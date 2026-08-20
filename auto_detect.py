"""
auto_detect — window-activity auto start/stop for habit timers.

Right-click a habit square → "Auto-detect window…" lists every OPEN
window type (deduplicated by app class — four VSCode windows show up
as a single "code" entry). Pick one and the habit's timer starts by
itself whenever you type or click in that app, and stops when you

  * cancel it manually (click the square — auto-start then stays off
    until you leave that window once, so it can't fight you), or
  * stop using the machine for `idle_seconds` (default 15 s), or
  * switch away / minimize the window (it is no longer the active
    window, so you're clearly not doing that habit right now).

Nothing is hardcoded: any habit can be paired with any window class,
the pairs live in ~/.config/pc_bubble_widget/auto_detect.json.

Backends (probed in this order, silent no-op when none fits):
  * KDE/Wayland: a tiny KWin script (loaded via DBus, same trick as
    the keep-above script) pushes window-activation and minimize
    events to a DBus service this module registers; window listing
    uses a one-shot KWin script the same way.
  * X11: wmctrl -lx for the window list, xdotool polling (2 s) for
    the active window's class.

"Typing or clicking" is detected by reading the evdev devices
(/dev/input/event*) in a background thread — works on Wayland where
global input hooks don't exist; requires the user to be in the
`input` group (checked at runtime; without it the idle-stop rule is
disabled and focus alone drives the timer).
"""

import fcntl
import json
import os
import select
import subprocess
import threading
import time

from PyQt5.QtCore import QObject, QTimer, Q_CLASSINFO, pyqtSlot
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QMenu

try:
    from PyQt5.QtDBus import (QDBusConnection, QDBusAbstractAdaptor,
                              QDBusMessage)
    HAVE_QTDBUS = True
except ImportError:          # pragma: no cover - unusual PyQt5 builds
    HAVE_QTDBUS = False

CONFIG_DIR = os.path.expanduser('~/.config/pc_bubble_widget')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'auto_detect.json')
IDLE_SECONDS_DEFAULT = 15

DBUS_SERVICE = 'org.pyhabits.AutoDetect'
DBUS_PATH = '/AutoDetect'
DBUS_IFACE = 'org.pyhabits.AutoDetect'

# window classes that are desktop plumbing, not "things I am doing"
NOISE_CLASSES = {
    'plasmashell', 'org.kde.plasmashell', 'kwin_wayland', 'kded6',
    'org.kde.kded6', 'xdg-desktop-portal-kde', 'xwaylandvideobridge',
    'org.kde.polkit-kde-authentication-agent-1',
}
OWN_CAPTION_PREFIX = 'Tail PC Widget'   # our bubble/flash/tip windows

# KWin watcher script: pushes the active window (class, caption,
# minimized) whenever activation/minimize state changes. Bump _V in the
# filename to force KWin to reload changed script content.
WATCH_V = 1
WATCH_SCRIPT_NAME = 'pyhabits_watch_v{}'.format(WATCH_V)
WATCH_JS = '''
function push(w) {
    if (!w) { callDBus("@S@", "@P@", "@I@", "ActiveWindow", "", "", true); return; }
    callDBus("@S@", "@P@", "@I@", "ActiveWindow",
             String(w.resourceClass), String(w.caption), w.minimized === true);
}
function hook(w) {
    if (!w) return;
    w.minimizedChanged.connect(function() { push(workspace.activeWindow); });
    w.activeChanged.connect(function() { push(workspace.activeWindow); });
}
workspace.windowActivated.connect(function(w) { push(w); });
workspace.windowAdded.connect(hook);
workspace.windowList().forEach(hook);
push(workspace.activeWindow);
'''

# One-shot KWin script: dumps every window's (class, caption) as JSON
# to our DBus service. Python unloads it once the answer arrives.
ENUM_SCRIPT_NAME = 'pyhabits_enum'
ENUM_JS = '''
var out = [];
workspace.windowList().forEach(function(w) {
    if (!w || w.specialWindow === true) return;
    out.push([String(w.resourceClass), String(w.caption)]);
});
callDBus("@S@", "@P@", "@I@", "WindowList", JSON.stringify(out));
'''


# ── keyboard/mouse activity (evdev; Wayland-safe, no root if in `input`) ──

EVIOCGBIT_EVTYPE = 0x80044520   # EVIOCGBIT(0, 4): supported-event-types bitmap
EV_KEY_BIT = 0x02               # keyboards, mice, touchpads all set this


class InputActivityMonitor:
    """
    Daemon thread that watches all evdev devices that can produce key
    events and timestamps the last real input. Reading evdev does not
    steal events from other readers, so this is passive and safe.
    """

    def __init__(self):
        self.last_activity = time.monotonic()
        self.available = False
        self._stop_evt = threading.Event()
        self._thread = None

    def start(self):
        fds = self._open_key_devices()
        if not fds:
            return                      # not in `input` group — degrade
        self.available = True
        self._thread = threading.Thread(
            target=self._loop, args=(fds,), daemon=True,
            name='auto-detect-input')
        self._thread.start()

    def stop(self):
        self._stop_evt.set()            # thread closes its own fds

    def idle_seconds(self) -> float:
        return time.monotonic() - self.last_activity

    # ── internals ────────────────────────────────────────────────────────

    def _open_key_devices(self):
        fds = []
        try:
            names = sorted(os.listdir('/dev/input'))
        except OSError:
            return fds
        for name in names:
            if not name.startswith('event'):
                continue
            try:
                fd = os.open(os.path.join('/dev/input', name),
                             os.O_RDONLY | os.O_NONBLOCK)
                buf = bytearray(4)
                fcntl.ioctl(fd, EVIOCGBIT_EVTYPE, buf, True)
                if buf[0] & EV_KEY_BIT:
                    fds.append(fd)
                else:
                    os.close(fd)
            except OSError:
                continue
        return fds

    def _loop(self, fds):
        while not self._stop_evt.is_set() and fds:
            try:
                ready, _, _ = select.select(fds, [], [], 1.0)
            except (OSError, ValueError):
                break
            for fd in ready:
                try:
                    if os.read(fd, 8192):
                        self.last_activity = time.monotonic()
                except OSError:         # device vanished — drop it
                    try:
                        fds.remove(fd)
                        os.close(fd)
                    except (ValueError, OSError):
                        pass
        for fd in fds:
            try:
                os.close(fd)
            except OSError:
                pass


# ── KDE / KWin backend (Wayland and X11 sessions of KDE) ──────────────────

if HAVE_QTDBUS:

    class _AutoDetectAdaptor(QDBusAbstractAdaptor):
        """DBus surface KWin scripts call into."""

        Q_CLASSINFO("D-Bus Interface", DBUS_IFACE)

        def __init__(self, backend):
            super().__init__(backend)
            self._backend = backend

        @pyqtSlot(str)
        def WindowList(self, payload):
            self._backend._on_window_list(payload)

        @pyqtSlot(str, str, bool)
        def ActiveWindow(self, cls, caption, minimized):
            self._backend._on_active(cls, caption, minimized)


class _KWinBackend(QObject):
    """
    Talks to KWin over the session bus: a resident watcher script
    pushes active-window events; a one-shot script answers window
    enumeration. Both scripts live in CONFIG_DIR.
    """

    def __init__(self, controller):
        super().__init__(controller)
        self.active_class = None
        self.active_minimized = False
        self._bus = QDBusConnection.sessionBus()
        self._enum_cb = None
        self._enum_timer = QTimer(self)
        self._enum_timer.setSingleShot(True)
        self._enum_timer.timeout.connect(self._enum_timeout)
        _AutoDetectAdaptor(self)
        if not self._bus.registerService(DBUS_SERVICE):
            raise RuntimeError('DBus service name taken: ' + DBUS_SERVICE)
        if not self._bus.registerObject(DBUS_PATH, self):
            raise RuntimeError('DBus object path taken: ' + DBUS_PATH)

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self):
        watch_js = os.path.join(CONFIG_DIR,
                                'auto_detect_watch_v{}.js'.format(WATCH_V))
        with open(watch_js, 'w', encoding='utf-8') as f:
            f.write(_fill_js(WATCH_JS))
        self._scripting('unloadScript', WATCH_SCRIPT_NAME)
        self._scripting('loadScript', watch_js, WATCH_SCRIPT_NAME)
        self._scripting('start')

    def stop(self):
        self._scripting('unloadScript', WATCH_SCRIPT_NAME)
        self._scripting('unloadScript', ENUM_SCRIPT_NAME)
        self._bus.unregisterObject(DBUS_PATH)
        self._bus.unregisterService(DBUS_SERVICE)

    # ── window enumeration (async — arrives via DBus) ────────────────────

    def request_windows(self, callback):
        self._enum_cb = callback
        enum_js = os.path.join(CONFIG_DIR, 'auto_detect_enum.js')
        with open(enum_js, 'w', encoding='utf-8') as f:
            f.write(_fill_js(ENUM_JS))
        self._scripting('unloadScript', ENUM_SCRIPT_NAME)
        self._scripting('loadScript', enum_js, ENUM_SCRIPT_NAME)
        self._scripting('start')
        self._enum_timer.start(3000)    # KWin never answered → give up

    def _on_window_list(self, payload):
        if self._enum_cb is None:
            return
        self._enum_timer.stop()
        cb, self._enum_cb = self._enum_cb, None
        QTimer.singleShot(0, lambda: self._scripting(
            'unloadScript', ENUM_SCRIPT_NAME))   # not from inside the slot
        try:
            rows = json.loads(payload)
            cb([(str(c), str(t)) for c, t in rows])
        except (ValueError, TypeError):
            cb([])

    def _enum_timeout(self):
        if self._enum_cb is not None:
            cb, self._enum_cb = self._enum_cb, None
            self._scripting('unloadScript', ENUM_SCRIPT_NAME)
            cb([])

    # ── active window events ─────────────────────────────────────────────

    def _on_active(self, cls, caption, minimized):
        self.active_class = cls or None
        self.active_minimized = bool(minimized)

    # ── helpers ──────────────────────────────────────────────────────────

    def _scripting(self, member, *args):
        msg = QDBusMessage.createMethodCall(
            'org.kde.KWin', '/Scripting', 'org.kde.kwin.Scripting', member)
        msg.setArguments(list(args))
        try:
            self._bus.call(msg, 3000)
        except Exception:
            pass


# ── plain X11 backend (wmctrl + xdotool; non-KDE or KWin DBus refused) ────

class _X11Backend(QObject):
    """
    Polls the active window's class with xdotool every 2 s; enumerates
    windows with wmctrl -lx. Minimized windows are never the active
    window on X11, so "not active" already covers the minimize rule.
    """

    POLL_MS = 2000

    def __init__(self, controller):
        super().__init__(controller)
        self.active_class = None
        self.active_minimized = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    def start(self):
        self._timer.start(self.POLL_MS)
        self._poll()

    def stop(self):
        self._timer.stop()

    def request_windows(self, callback):
        rows = []
        out = _run(['wmctrl', '-lx'])
        if out is not None:
            for line in out.splitlines():
                parts = line.split(None, 3)
                if len(parts) < 4:
                    continue
                wm_class = parts[2]
                cls = wm_class.rsplit('.', 1)[-1]
                if cls:
                    rows.append((cls, parts[3]))
        QTimer.singleShot(0, lambda: callback(rows))

    def _poll(self):
        cls = _run(['xdotool', 'getactivewindow', 'getwindowclassname'])
        self.active_class = cls.strip() or None if cls is not None else None


# ── controller: mappings, persistence, the start/stop state machine ───────

class AutoDetectController(QObject):
    """
    Owns the habit → window-class mappings and decides every second
    whether each mapped habit's timer should run:

      run  ⇔  target window is the ACTIVE window (not minimized)
               AND the user typed/clicked within `idle_seconds`.

    Timers the controller started itself it also stops itself; timers
    the user started manually are never auto-stopped. A manual stop
    suppresses auto-start until the target window loses focus once.
    """

    TICK_MS = 1000

    def __init__(self, is_running, on_start, on_stop, on_info,
                 habits_provider=None):
        """
        Callbacks (all called on the Qt main thread):
          is_running(habit) -> bool     is a timer running for habit?
          on_start(habit)                start it now (auto)
          on_stop(habit)                 stop it now (auto)
          on_info(message)               transient status text
          habits_provider() -> set       habit names that have squares
        """
        super().__init__()
        self._is_running = is_running
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_info = on_info
        self._habits = habits_provider or (lambda: set())
        self._mappings = {}          # habit -> window class
        self._idle_seconds = IDLE_SECONDS_DEFAULT
        self._auto_started = set()   # habits whose timer WE started
        self._suppress = set()       # manual stop → no restart until unfocus
        self._backend = None
        self._input = InputActivityMonitor()
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._load_config()

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self):
        self._input.start()
        self._backend = self._make_backend()
        if self._backend is not None:
            self._backend.start()
        if self._mappings and not self._input.available:
            self._on_info('auto-detect: no input devices — '
                          'idle stop disabled')
        self._tick_timer.start(self.TICK_MS)

    def stop(self):
        self._tick_timer.stop()
        self._input.stop()
        if self._backend is not None:
            self._backend.stop()
            self._backend = None

    def _make_backend(self):
        if HAVE_QTDBUS:
            bus = QDBusConnection.sessionBus()
            if bus.isConnected() and _service_registered(bus, 'org.kde.KWin'):
                try:
                    return _KWinBackend(self)
                except Exception:
                    pass
        if _run(['wmctrl', '-m']) is not None and \
                _run(['xdotool', 'version']) is not None:
            return _X11Backend(self)
        return None

    # ── mappings / persistence ───────────────────────────────────────────

    def mapping_for(self, habit):
        return self._mappings.get(habit)

    def set_mapping(self, habit, window_class):
        self._mappings[habit] = window_class
        self._suppress.discard(habit)
        self._save_config()

    def clear_mapping(self, habit):
        if self._mappings.pop(habit, None) is not None:
            # a timer we auto-started keeps running, but becomes manual
            self._auto_started.discard(habit)
            self._save_config()

    def _load_config(self):
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            self._mappings = {str(h): str(c)
                              for h, c in (data.get('mappings') or {}).items()}
            idle = data.get('idle_seconds')
            if isinstance(idle, (int, float)) and idle > 0:
                self._idle_seconds = int(idle)
        except (OSError, ValueError):
            pass

    def _save_config(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE + '.tmp', 'w') as f:
                json.dump({'idle_seconds': self._idle_seconds,
                           'mappings': self._mappings}, f, indent=1)
            os.replace(CONFIG_FILE + '.tmp', CONFIG_FILE)
        except OSError:
            pass

    # ── window enumeration for the picker ────────────────────────────────

    def request_windows(self, callback):
        """
        callback([(class, count, sample_caption), ...]) — open window
        types, deduplicated, noise filtered, alphabetically sorted.
        """
        def with_rows(rows):
            callback(self._dedup(rows))
        if self._backend is None:
            callback([])
        else:
            self._backend.request_windows(with_rows)

    @staticmethod
    def _dedup(rows):
        merged = {}                   # casefolded class -> [n, display, sample]
        for cls, caption in rows:
            if (not cls or cls.casefold() in NOISE_CLASSES
                    or caption.startswith(OWN_CAPTION_PREFIX)):
                continue
            key = cls.casefold()
            entry = merged.setdefault(key, [0, cls, ''])
            entry[0] += 1
            if not entry[2] and caption:
                entry[2] = caption
        return sorted((disp, n, sample)
                      for n, disp, sample in merged.values())

    # ── interaction with the widget ──────────────────────────────────────

    def note_manual_toggle(self, habit, started):
        """
        The user clicked the square. A manual STOP of a mapped habit
        suppresses auto-start until the target window loses focus —
        otherwise typing on would instantly re-start what was cancelled.
        """
        if not started:
            self._auto_started.discard(habit)
            if habit in self._mappings:
                self._suppress.add(habit)

    # ── the state machine ────────────────────────────────────────────────

    def _tick(self):
        if not self._mappings or self._backend is None:
            return
        cls = (self._backend.active_class or '').casefold()
        focused_ok = bool(cls) and not self._backend.active_minimized
        user_active = (self._input.idle_seconds() <= self._idle_seconds
                       if self._input.available else True)
        known = self._habits()
        for habit, mapped in list(self._mappings.items()):
            if habit not in known:
                continue
            focused = focused_ok and cls == mapped.casefold()
            if not focused:
                self._suppress.discard(habit)   # left the window: re-arm
            if habit in self._auto_started:
                if not focused or not user_active:
                    self._auto_started.discard(habit)
                    self._on_stop(habit)
            elif (focused and user_active and habit not in self._suppress
                    and not self._is_running(habit)):
                self._auto_started.add(habit)
                self._on_start(habit)


# ── picker popup ───────────────────────────────────────────────────────────

def open_window_picker(controller, habit_name, on_chosen, pos=None):
    """
    Lists the currently open window types (deduplicated) in a popup
    menu at the cursor; picking one calls on_chosen(window_class).
    Enumeration is async (KWin answers over DBus), so the menu opens
    a moment after the click — the event loop must be free for that.
    """
    def deliver(windows):
        menu = QMenu()
        menu.setToolTipsVisible(True)
        head = menu.addAction('Auto-detect for {}'.format(habit_name))
        head.setEnabled(False)
        menu.addSeparator()
        current = (controller.mapping_for(habit_name) or '').casefold()
        if not windows:
            na = menu.addAction('(no windows could be listed)')
            na.setEnabled(False)
        else:
            for cls, count, sample in windows:
                label = cls + (' — {} windows'.format(count)
                               if count > 1 else '')
                if cls.casefold() == current:
                    label = '✓ ' + label
                act = menu.addAction(label)
                if sample:
                    act.setToolTip(sample[:100])
                act.triggered.connect(
                    lambda _=False, c=cls: on_chosen(c))
        menu.addSeparator()
        menu.addAction('Cancel')
        menu.exec_(pos if pos is not None else QCursor.pos())

    controller.request_windows(deliver)


# ── small helpers ──────────────────────────────────────────────────────────

def _fill_js(template):
    return (template
            .replace('@S@', DBUS_SERVICE)
            .replace('@P@', DBUS_PATH)
            .replace('@I@', DBUS_IFACE))


def _run(cmd):
    """subprocess.run that returns stdout, or None on any failure."""
    try:
        r = subprocess.run(cmd, check=False, capture_output=True, timeout=5)
        return r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _service_registered(bus, name):
    msg = QDBusMessage.createMethodCall(
        'org.freedesktop.DBus', '/', 'org.freedesktop.DBus', 'NameHasOwner')
    msg.setArguments([name])
    reply = bus.call(msg, 2000)
    args = reply.arguments()
    return bool(args and args[0])
