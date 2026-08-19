#!/usr/bin/env python3
"""
pc_bubble_widget — the PC floating bubble widget for Tail habits.

A small frameless always-on-top circle with the tail icon, draggable
anywhere on screen, with one habit square per habit toggled "PC widget"
in the phone app's edit mode. Clicking a square starts that habit's
timer; clicking again stops it and queues an event (duration + the real
start time) on the local Tail Bridge server — the phone pulls it from
there, applies it and acks. Zero setup: same bridge as Garmin/movies.

Idle squares tuck in around the bubble (overlapping) while the mouse is
away; running timers always stay out at rest radius, and an approaching
mouse spreads the whole ring so every square is easy to click.
Right-clicking a square offers a repeatable "Started 1 min earlier"
action that backdates the running timer.

Lives in the system tray (no taskbar entry). Tray click or menu item
recalls the bubble next to the tray so it can always be found.

Run with the project venv:
  ./py_habits_widget/bin/python pc_bubble_widget.py
"""

import json
import math
import os
import subprocess
import sys
import html
import time
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from PyQt5.QtGui import (QIcon, QPixmap, QPainter, QColor, QFont, QPen,
                         QFontMetrics, QCursor)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QAction, QToolTip,
)

from pc_widget_sync import (
    load_config, append_event, pending_events,
)
from pc_widget_stats import HabitStats, habit_style

try:
    from habit_colors import get_habit_icon_path
except ImportError:  # standalone fallback if habit_colors is unavailable
    def get_habit_icon_path(habit_name, custom_overrides=None):
        return None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TAIL_ICON = os.path.join(SCRIPT_DIR, 'icons', 'tail_icon.png')
STATE_FILE = os.path.expanduser('~/.config/pc_bubble_widget/state.json')
INSTANCE_KEY = 'pc-bubble-widget-singleton'


def show_tip_text(pos, text, target):
    """
    Tooltip display seam (the smoke test records calls through it).
    QToolTip popups are positioned by the platform itself — on Wayland
    clients may not place their own top-level windows (our hand-rolled
    tooltip kept appearing at its spawn point), but popup tooltips are
    anchored properly, right at the cursor.
    """
    QToolTip.showText(pos, text, target)


def hide_tip_text():
    QToolTip.hideText()

BUBBLE_D = 56          # bubble diameter (px)
SQUARE_D = 46          # habit square size (px)
REST_GAP = 4           # bubble↔square gap at rest — just a sliver
REST_R = BUBBLE_D // 2 + REST_GAP + SQUARE_D // 2   # running timers sit here
TUCK_R = BUBBLE_D // 2 + SQUARE_D // 2 - 26         # idle: mostly BEHIND the bubble
SPREAD_PAD = 10        # ring spacing per square when spread out for clicking
DRAG_THRESHOLD = 8     # px before a square press becomes a whole-widget drag
PINCH = 0.38           # black-hole: max squeeze of a tucked square's near edge
PINCH_FADE = 0.45      # black-hole: max transparency of that near edge

BG_COLOR = QColor(24, 24, 28, 225)
BORDER_IDLE = QColor(90, 90, 100)
BORDER_RUN = QColor(82, 196, 26)      # green ring while a timer runs
BORDER_SQ_RUN = QColor(82, 196, 26)
DOT_PENDING = QColor(255, 170, 0)     # orange dot: queued, not yet acked
DOT_ACKED = QColor(82, 196, 26)       # green dot: phone confirmed
TEXT_COLOR = QColor(235, 235, 235)


def fmt_elapsed(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return '{}:{:02d}:{:02d}'.format(h, m, s) if h else '{:02d}:{:02d}'.format(m, s)


class HabitSquare(QWidget):
    """One habit square: click to start/stop its timer."""

    def __init__(self, habit: dict, parent=None):
        super().__init__(parent)
        self.habit_name = habit['name']
        self.icon_name = habit.get('icon')
        self.minutes_primary = habit.get('minutes_primary', False)
        self.running = False
        self.pending = 0          # queued-but-unacked events for this habit
        self.acked_flash_until = 0.0
        self._angle = 0.0         # ring position in radians (set by the bubble)
        self._radius = float(TUCK_R)  # current ring radius (animated)
        self._press_pos = None    # global press pos while click-vs-drag is pending
        self.setFixedSize(SQUARE_D, SQUARE_D)
        self.setMouseTracking(True)   # hover self-heal needs no-button moves
        self.setCursor(Qt.PointingHandCursor)
        self._icon_pm = self._load_icon()

    def _load_icon(self):
        overrides = {self.habit_name: self.icon_name} if self.icon_name else None
        path = get_habit_icon_path(self.habit_name, overrides)
        if path and os.path.exists(path):
            pm = QPixmap(path)
            if not pm.isNull():
                return pm.scaled(
                    SQUARE_D - 18, SQUARE_D - 26,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QPixmap()

    def tooltip_lines(self):
        """
        This square's hover message: habit name, its count for today,
        and — while a dot is showing — what the dot is reporting
        (orange = queued events the phone hasn't picked up yet,
        green = the phone just confirmed).
        """
        win = self.window()
        win.stats.refresh()
        unit = 'min' if self.minutes_primary else 'pts'
        lines = [self.habit_name,
                 'today: {} {}'.format(win.stats.habit_today(self.habit_name),
                                       unit)]
        if time.time() < self.acked_flash_until:
            lines.append('phone confirmed ✓')
        elif self.pending > 0:
            lines.append('{} events waiting for the phone to sync'.format(
                self.pending) if self.pending != 1
                else 'waiting for the phone to sync')
        return lines

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # click-vs-drag: don't toggle yet — a drag may take over
            self._press_pos = e.globalPos()
        elif e.button() == Qt.RightButton:
            win = self.window()
            win._hide_tooltip()  # type: ignore[attr-defined]
            win.open_square_menu(self, e.globalPos())  # type: ignore[attr-defined]

    def mouseMoveEvent(self, e):
        win = self.window()
        if win._drag_offset is not None:      # manual drag in progress
            win.move(e.globalPos() - win._drag_offset)
            win._save_state_throttled()
            return
        if (self._press_pos is not None and
                (e.globalPos() - self._press_pos).manhattanLength()
                > DRAG_THRESHOLD):
            self._press_pos = None            # consumed — a drag, not a click
            win.begin_widget_drag()  # type: ignore[attr-defined]
            return
        if not e.buttons() and self not in win._hover_set:
            # Wayland self-heal: after a compositor drag Qt may believe
            # the pointer never left, so no Enter ever fires — motion
            # over the square is proof enough of presence.
            win._hover_entered(self)
            win.request_tooltip(self)

    def mouseReleaseEvent(self, e):
        win = self.window()
        if win._drag_offset is not None:      # manual drag ends here too
            win._drag_offset = None
            win._save_state()
            return
        if e.button() == Qt.LeftButton and self._press_pos is not None:
            self._press_pos = None
            win.on_square_clicked(self)  # type: ignore[attr-defined]

    def enterEvent(self, _):
        win = self.window()
        win._hover_entered(self)  # type: ignore[attr-defined]
        win.request_tooltip(self)  # type: ignore[attr-defined]

    def leaveEvent(self, _):
        self.window()._hover_left(self)  # type: ignore[attr-defined]

    # ── habit style (Android-matched) ───────────────────────────────────

    def _today_style(self):
        """
        This square's colours for its EFFECTIVE points today (raw count,
        or minutes/divider for minutes-primary habits — what the phone
        shows) through the same ladder the phone's habit buttons use
        (pc_widget_stats.habit_style, mirroring HabitColors.kt
        getHabitStyle).
        """
        win = self.window()
        win.stats.refresh()
        return habit_style(win.stats.habit_effective(self.habit_name))

    # ── black-hole collapse ─────────────────────────────────────────────

    def _tuck_progress(self) -> float:
        """0 at rest/spread … 1 fully tucked — drives the pinch warp."""
        span = REST_R - TUCK_R
        if span <= 0:
            return 0.0
        return max(0.0, min(1.0, (REST_R - self._radius) / span))

    def _render_body(self) -> QPixmap:
        """
        The square's normal look rendered offscreen — rounded rect in the
        habit's phone-matched tier colour, icon, dots, timer — so the
        black-hole warp can distort all of it.
        """
        pm = QPixmap(SQUARE_D, SQUARE_D)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        bg_hex, border_hex, outer_hex, inner_hex = self._today_style()
        bg = QColor(bg_hex)
        bg.setAlpha(235)   # let the dark widget bleed through just slightly
        on_glass = QColor(bg_hex).lightness() > 128   # glass bg → dark text
        fg = QColor(20, 20, 24) if on_glass else TEXT_COLOR
        r = 12.0
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(1, 1, SQUARE_D - 2, SQUARE_D - 2, r, r)
        p.setBrush(Qt.NoBrush)
        if self.running:
            p.setPen(QPen(BORDER_SQ_RUN, 2))
            p.drawRoundedRect(1, 1, SQUARE_D - 2, SQUARE_D - 2, r, r)
        elif inner_hex:
            # phone phase 4: double vivid border with a thin black gap
            p.setPen(QPen(QColor(outer_hex), 1))
            p.drawRoundedRect(QRectF(0.5, 0.5, SQUARE_D - 1, SQUARE_D - 1), r, r)
            p.setPen(QPen(Qt.black, 1))
            p.drawRoundedRect(QRectF(2.5, 2.5, SQUARE_D - 5, SQUARE_D - 5), r - 2, r - 2)
            p.setPen(QPen(QColor(inner_hex), 1))
            p.drawRoundedRect(QRectF(4.5, 4.5, SQUARE_D - 9, SQUARE_D - 9), r - 4, r - 4)
        else:
            p.setPen(QPen(QColor(border_hex) if border_hex else BORDER_IDLE,
                          2 if border_hex else 1))
            p.drawRoundedRect(1, 1, SQUARE_D - 2, SQUARE_D - 2, r, r)

        cx = SQUARE_D // 2
        if not self._icon_pm.isNull():
            p.drawPixmap(cx - self._icon_pm.width() // 2,
                         cx - self._icon_pm.height() // 2 - 4, self._icon_pm)
        else:
            p.setPen(fg)
            f = QFont('Sans', 13, QFont.Bold)
            p.setFont(f)
            initial = self.habit_name[:1].upper()
            p.drawText(pm.rect().adjusted(0, -4, 0, -4), Qt.AlignCenter, initial)

        if self.running:
            secs = self.window().elapsed_for(self.habit_name)  # type: ignore[attr-defined]
            p.setPen(fg)
            p.setFont(QFont('Sans', 7, QFont.Bold))
            p.drawText(pm.rect().adjusted(0, SQUARE_D - 16, 0, -2),
                       Qt.AlignCenter, fmt_elapsed(secs))

        if self.pending > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(DOT_PENDING)
            p.drawEllipse(SQUARE_D - 12, 4, 8, 8)
        elif time.time() < self.acked_flash_until:
            p.setPen(Qt.NoPen)
            p.setBrush(DOT_ACKED)
            p.drawEllipse(SQUARE_D - 12, 4, 8, 8)
        p.end()
        return pm

    def paintEvent(self, _):
        pm = self._render_body()
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        t = self._tuck_progress()
        if t <= 0.02:
            p.drawPixmap(0, 0, pm)
            p.end()
            return
        # black-hole collapse: thin strips perpendicular to the radial
        # axis, each squeezed toward the radial axis line and faded near
        # the center. Strips stay axis-aligned (orientation picked by the
        # dominant radial component) so the content — icon included —
        # never rotates; only the squeeze direction follows the ring.
        ux, uy = math.cos(self._angle), -math.sin(self._angle)
        vertical = abs(ux) >= abs(uy)   # radial mostly horizontal → columns
        n = 16
        w = SQUARE_D / n
        for i in range(n):
            c = (i + 0.5) * w           # strip centre along the axis
            outward = ux if vertical else uy
            f = (c / SQUARE_D) if outward > 0 else 1 - (c / SQUARE_D)
            s = 1.0 - PINCH * t * (1.0 - f)
            p.setOpacity(1.0 - PINCH_FADE * t * (1.0 - f))
            if vertical:
                p.drawPixmap(
                    QRectF(c - w / 2, SQUARE_D * (1 - s) / 2,
                           w, SQUARE_D * s),
                    pm, QRectF(c - w / 2, 0, w, SQUARE_D))
            else:
                p.drawPixmap(
                    QRectF(SQUARE_D * (1 - s) / 2, c - w / 2,
                           SQUARE_D * s, w),
                    pm, QRectF(0, c - w / 2, SQUARE_D, w))
        p.setOpacity(1.0)
        p.end()


class BubbleWidget(QWidget):
    """Frameless container: tail bubble in the middle, habit squares around."""

    def __init__(self):
        super().__init__(None,
                         Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                         Qt.Tool | Qt.X11BypassWindowManagerHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(TAIL_ICON))  # tail icon if a DE shows a taskbar entry
        self.setWindowTitle('Tail PC Widget')

        self.squares = []                 # type: list
        self.timers = {}                  # habit name -> datetime (start)
        self.pending_by_habit = {}        # habit name -> queued count
        self._drag_offset = None          # type: QPoint | None
        self._config_sig = None          # (name, icon, minutes_primary) tuple
        self._spread_r = REST_R           # spread ring radius (per habit count)
        self._near = False                # mouse inside the approach zone?
        self.window_d = 2 * (REST_R + SQUARE_D // 2) + 8
        self.setFixedSize(self.window_d, self.window_d)
        # the center circle as a child widget: painted ABOVE the squares
        # so tucked ones collapse behind it (black-hole). Transparent for
        # mouse events — clicks/drags/hover pass through to the container
        # exactly as when the container painted the circle itself.
        self.core = BubbleCore(self)

        # today/week/month numbers for the tooltips, from the
        # Syncthing-synced habitsdb (mtime-cached, re-read on mtime change)
        self.stats = HabitStats()

        # ~60 Hz layout easing: squares glide between tucked/rest/spread radii
        # (created early — rebuild_squares kicks the animation)
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)
        self.anim_timer.timeout.connect(self._anim_step)

        # proximity: Enter/Leave events (Wayland-safe) drive the spread;
        # cursor polling only augments it on X11. Wayland clients cannot
        # query the global cursor — QCursor.pos() freezes at the last
        # in-window position once the pointer leaves our windows, so pure
        # polling would spread the ring once and never contract it again.
        self._hover_set = set()      # widgets currently under the pointer
        self._pin_spread = False     # context menu open → keep the ring out
        self._can_poll_cursor = QApplication.platformName() == 'xcb'
        self._leave_timer = QTimer(self)  # debounce Leave→Enter (child↔parent)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.setInterval(120)
        self._leave_timer.timeout.connect(lambda: self._set_near(False))

        # Wayland presence watchdog: QCursor.pos() only updates while the
        # pointer is over one of our windows. A reading frozen for a while
        # that no longer lies inside the window means a Leave went missing
        # (typically after a compositor drag grabbed the pointer) — the
        # stale hover is dropped so the ring can contract again.
        self.setMouseTracking(True)     # no-button moves feed the self-heal
        self._last_cursor = QCursor.pos()
        self._cursor_still_since = time.monotonic()

        # custom per-widget tooltips: QToolTip popups (platform-placed,
        # Wayland-safe) driven by our own enter/leave tracking so each
        # square reliably gets its own message even while the ring
        # animates under a stationary cursor
        self._tip_target = None
        self._tip_timer = QTimer(self)
        self._tip_timer.setSingleShot(True)
        self._tip_timer.setInterval(600)
        self._tip_timer.timeout.connect(self._show_tooltip)

        self.hover_timer = QTimer(self)
        self.hover_timer.setInterval(40)
        self.hover_timer.timeout.connect(self._check_proximity)
        self.hover_timer.start()

        self._load_state()
        self._apply_config(load_config())

        # 1 Hz tick: elapsed labels + running ring
        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self._on_tick)
        self.tick_timer.start(1000)

        # config poll (phone may toggle habits at any time)
        self.cfg_timer = QTimer(self)
        self.cfg_timer.timeout.connect(self._poll_config)
        self.cfg_timer.start(20_000)

        # ack poll (phone confirms applied events)
        self.ack_timer = QTimer(self)
        self.ack_timer.timeout.connect(self._poll_acks)
        self.ack_timer.start(30_000)
        self._poll_acks()

    # ── geometry helpers ────────────────────────────────────────────────

    def _center(self) -> QPoint:
        return QPoint(self.window_d // 2, self.window_d // 2)

    # ── squares / config ────────────────────────────────────────────────

    def rebuild_squares(self, habits):
        self._hide_tooltip()
        for sq in self.squares:
            self._hover_set.discard(sq)
            sq.deleteLater()
        self.squares = []
        n = len(habits)
        # spread radius: enough ring circumference for every square to get
        # its own non-overlapping clickable slot; the window grows to match
        self._spread_r = (max(REST_R, int(math.ceil(
            n * (SQUARE_D + SPREAD_PAD) / (2 * math.pi)))) if n else REST_R)
        new_d = 2 * (self._spread_r + SQUARE_D // 2) + 8
        if new_d != self.window_d:
            self.window_d = new_d
            self.setFixedSize(new_d, new_d)
        for i, habit in enumerate(habits):
            sq = HabitSquare(habit, self)
            sq._angle = math.radians(90 - i * 360.0 / n) if n else 0.0
            sq.running = habit['name'] in self.timers  # restore persisted timers
            sq._radius = self._target_radius(sq)
            self._place_square(sq)
            sq.show()
            self.squares.append(sq)
        self._raise_running()
        # drop timers for habits that lost their square
        gone = set(self.timers) - {h['name'] for h in habits}
        for name in gone:
            del self.timers[name]
        self._apply_pending_badges()
        self._place_core()
        self._kick_anim()  # glide out if the mouse is already near
        self.update()

    def _apply_config(self, habits):
        """Rebuilds the squares when the phone-pushed config actually
        changed. habits=None (bridge unreachable) keeps the current set."""
        if habits is None:
            return
        # effective-points inputs first: a divider change alone must not
        # rebuild the squares, but must recompute the point colours
        self.stats.set_point_config(habits)
        sig = tuple((h['name'], h['icon'], h['minutes_primary']) for h in habits)
        if sig == self._config_sig:
            return
        self._config_sig = sig
        self.rebuild_squares(habits)

    def _poll_config(self):
        self._apply_config(load_config())

    # ── ring layout: tuck / rest / spread ───────────────────────────────

    def _target_radius(self, sq: HabitSquare) -> float:
        """
        Idle squares tuck in close to the bubble (overlapping) while the
        mouse is away; running timers always stay out at rest radius so
        they stay prominent, and an approaching mouse spreads the whole
        ring out so every square is easy to click.
        """
        if self._near:
            return float(self._spread_r)
        return float(REST_R if sq.running else TUCK_R)

    def _place_square(self, sq: HabitSquare):
        c = self._center()
        x = c.x() + sq._radius * math.cos(sq._angle)
        y = c.y() - sq._radius * math.sin(sq._angle)
        sq.move(int(round(x)) - SQUARE_D // 2,
                int(round(y)) - SQUARE_D // 2)

    def _apply_layout_now(self):
        """Snaps every square onto its target radius (no animation)."""
        for sq in self.squares:
            sq._radius = self._target_radius(sq)
            self._place_square(sq)
        self._raise_running()

    def _raise_running(self):
        """
        Running squares stack above tucked idle ones — and the center
        circle stays on top of everything so idle squares collapse
        behind it.
        """
        for sq in self.squares:
            if sq.running:
                sq.raise_()
        self.core.raise_()

    def _kick_anim(self):
        if not self.anim_timer.isActive():
            self.anim_timer.start()

    def _anim_step(self):
        """Exponential ease toward each square's target radius (~60 Hz)."""
        moving = False
        for sq in self.squares:
            target = self._target_radius(sq)
            if abs(sq._radius - target) > 0.5:
                sq._radius += (target - sq._radius) * 0.28
                moving = True
            else:
                sq._radius = target
            self._place_square(sq)
            sq.update()   # repaint even when the rounded position is unchanged
        if moving:
            self._raise_running()
        else:
            self.anim_timer.stop()

    def _hover_entered(self, w):
        """Pointer entered the container or a square → spread immediately."""
        self._hover_set.add(w)
        if self._leave_timer.isActive():
            self._leave_timer.stop()
        self._set_near(True)

    def _hover_left(self, w):
        """
        Pointer left one of our widgets. Qt fires Leave on the container
        when the cursor moves onto a child square (and vice versa), so the
        contraction is debounced: only when nothing is hovered anymore does
        a short timer pull the ring back in (cancelled by any new Enter).
        """
        if self._tip_target is w:
            self._hide_tooltip()
        self._hover_set.discard(w)
        if self._hover_set or self._pin_spread:
            return
        if not self._can_poll_cursor:
            self._leave_timer.start()
        # X11: the cursor poll below owns the exit decision (hysteresis)

    def _set_near(self, near: bool):
        if near != self._near:
            self._near = near
            self._kick_anim()

    def _check_proximity(self):
        """
        Keeps the ring spread while the pointer is anywhere over the widget
        (or a context menu is open). On X11 the global cursor is queryable,
        so the ring also spreads a square-width BEFORE the pointer enters
        the window; on Wayland Enter/Leave events are the only trigger.
        """
        if not self.isVisible():
            self._hover_set.clear()
            self._hide_tooltip()
            self._set_near(False)
            return
        pos = QCursor.pos()
        if pos != self._last_cursor:
            self._last_cursor = pos
            self._cursor_still_since = time.monotonic()
        elif (self._hover_set and not self._pin_spread
                and time.monotonic() - self._cursor_still_since > 3.0
                and not self.rect().contains(self.mapFromGlobal(pos))):
            self._hover_set.clear()      # stale hover (lost Leave) — drop it
            self._hide_tooltip()
            self._set_near(False)
        if self._pin_spread or self._hover_set:
            self._set_near(True)
            return
        if not self._can_poll_cursor:
            return
        c = self.mapToGlobal(self._center())
        pos = QCursor.pos()
        d = math.hypot(pos.x() - c.x(), pos.y() - c.y())
        enter_r = self._spread_r + SQUARE_D
        exit_r = enter_r + 14  # hysteresis: no flicker at the boundary
        self._set_near(d <= (exit_r if self._near else enter_r))

    # ── interaction ─────────────────────────────────────────────────────

    def on_square_clicked(self, sq: HabitSquare):
        self._hide_tooltip()
        name = sq.habit_name
        if name not in self.timers:
            self.timers[name] = datetime.now()
            sq.running = True
            self._raise_running()
            self._kick_anim()
            sq.update()
            self.update()
            self._save_state()
            return
        start = self.timers.pop(name)
        sq.running = False
        self._kick_anim()
        elapsed = (datetime.now() - start).total_seconds()
        minutes = int(elapsed // 60)
        kind = 'session' if minutes > 0 else 'tap'
        event_id = append_event(name, kind=kind, start=start, minutes=minutes)
        if event_id:
            self.pending_by_habit[name] = self.pending_by_habit.get(name, 0) + 1
        self._apply_pending_badges()
        sq.update()
        self.update()
        self._save_state()
        self.window().show_flash(
            name, minutes if kind == 'session' else 0, event_id is not None)

    def elapsed_for(self, habit_name: str) -> int:
        start = self.timers.get(habit_name)
        return int((datetime.now() - start).total_seconds()) if start else 0

    def any_running(self) -> bool:
        return bool(self.timers)

    def backdate_timer(self, habit_name: str, minutes: int = 1) -> bool:
        """
        Pulls a running timer's start `minutes` further into the past
        (right-click menu: "as if I had started it a minute ago").
        Returns False when no timer is running for that habit.
        """
        start = self.timers.get(habit_name)
        if start is None:
            return False
        self.timers[habit_name] = start - timedelta(minutes=minutes)
        for sq in self.squares:
            if sq.habit_name == habit_name:
                sq.update()
        self._save_state()
        return True

    # ── acks / delivery state ───────────────────────────────────────────

    def _poll_acks(self):
        events = pending_events()
        if events is None:
            return  # bridge unreachable — keep current badges
        by_habit = {}
        for e in events:
            h = e.get('habit')
            if isinstance(h, str):
                by_habit[h] = by_habit.get(h, 0) + 1
        was_pending = self.pending_by_habit
        self.pending_by_habit = by_habit
        # flash a green dot on squares whose events were just acked
        now = time.time()
        for sq in self.squares:
            if was_pending.get(sq.habit_name, 0) > by_habit.get(sq.habit_name, 0):
                sq.acked_flash_until = now + 5.0
            sq.pending = by_habit.get(sq.habit_name, 0)
            sq.update()
        self._apply_pending_badges()

    def _apply_pending_badges(self):
        for sq in self.squares:
            sq.pending = self.pending_by_habit.get(sq.habit_name, 0)
            sq.update()

    # ── ticking / painting ──────────────────────────────────────────────

    # ── custom tooltips ─────────────────────────────────────────────────

    def tooltip_lines(self):
        """Center-bubble message: today's points + week/month averages."""
        self.stats.refresh()
        return ['Tail'] + self.stats.summary_lines()

    def request_tooltip(self, w):
        """Cursor entered the container or a square: show its message shortly."""
        self._tip_target = w
        self._tip_timer.start()

    def _hide_tooltip(self):
        self._tip_timer.stop()
        self._tip_target = None
        hide_tip_text()

    def _show_tooltip(self):
        target = self._tip_target
        if target is None or target not in self._hover_set:
            return
        lines = target.tooltip_lines()
        if lines:
            esc = [html.escape(l) for l in lines]
            text = '<b>{}</b>'.format(esc[0])
            if len(esc) > 1:
                text += '<br>' + '<br>'.join(esc[1:])
            show_tip_text(QCursor.pos(), text, target)

    def _on_tick(self):
        for sq in self.squares:
            if sq.running:
                sq.update()
        self.core.update()   # the running-border colour lives on the core now
        self._save_state_throttled()

    def _place_core(self):
        """
        Keeps the center circle glued to the widget's middle (the window
        resizes when the habit count changes).
        """
        c = self._center()
        self.core.move(c.x() - BUBBLE_D // 2, c.y() - BUBBLE_D // 2)

    # ── dragging ────────────────────────────────────────────────────────

    def enterEvent(self, _):
        self._hover_entered(self)
        self.request_tooltip(self)

    def leaveEvent(self, _):
        self._hover_left(self)

    def begin_widget_drag(self):
        """
        Left-drag from the bubble OR any square moves the whole widget.
        Wayland: ask the compositor to run the move itself (Qt/Wayland
        ignores move() — clients cannot position their own windows; the
        still-held button provides the serial, so this is also legal when
        called from a move event, e.g. a drag that began on a square).
        X11 / fallback: manual offset dragging.
        """
        self._hide_tooltip()
        # the compositor grab eats our Leave events — reset the hover
        # state so the ring can't stay wedged spread after the drag
        # ends (motion over the window re-arms it via the self-heal)
        self._hover_set.clear()
        self._leave_timer.stop()
        wh = self.windowHandle()
        if wh is not None and wh.startSystemMove():
            self._drag_offset = None
            return
        self._drag_offset = QCursor.pos() - self.frameGeometry().topLeft()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.begin_widget_drag()
        elif e.button() == Qt.RightButton:
            self._hide_tooltip()
            self.window().open_bubble_menu(self.mapToGlobal(e.pos()))  # type: ignore[attr-defined]

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_offset)
            self._save_state_throttled()
            return
        if not e.buttons() and self not in self._hover_set:
            # Wayland self-heal (see HabitSquare.mouseMoveEvent)
            self._hover_entered(self)
            self.request_tooltip(self)

    def mouseReleaseEvent(self, _):
        self._drag_offset = None
        self._save_state()

    # ── host hooks (overridden by PcBubbleApp) ──────────────────────────

    def show_flash(self, habit: str, minutes: int, queued: bool):
        """Confirmation flash; replaced by the app host. No-op standalone."""

    def open_bubble_menu(self, global_pos):
        """Bubble right-click menu; replaced by the app host. No-op standalone."""

    def open_square_menu(self, sq: HabitSquare, global_pos):
        """Per-habit right-click menu; replaced by the app host. No-op standalone."""

    # ── state persistence ───────────────────────────────────────────────

    _last_save = 0.0

    def _save_state_throttled(self):
        if time.time() - self._last_save > 2.0:
            self._save_state()

    def _save_state(self):
        self._last_save = time.time()
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            data = {
                'pos': [self.x(), self.y()],
                'timers': {h: s.isoformat(timespec='seconds')
                           for h, s in self.timers.items()},
            }
            with open(STATE_FILE + '.tmp', 'w') as f:
                json.dump(data, f)
            os.replace(STATE_FILE + '.tmp', STATE_FILE)
        except OSError:
            pass

    def _load_state(self):
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            pos = data.get('pos')
            if isinstance(pos, list) and len(pos) == 2:
                self.move(*pos)
                self._clamp_to_screen()
            for h, iso in (data.get('timers') or {}).items():
                try:
                    self.timers[h] = datetime.fromisoformat(iso)
                except ValueError:
                    pass
        except (OSError, ValueError):
            self.recall_to_tray(save=False)

    def _clamp_to_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = min(max(screen.left(), self.x()),
                screen.right() - self.window_d + 1)
        y = min(max(screen.top(), self.y()),
                screen.bottom() - self.window_d + 1)
        self.move(x, y)

    def recall_to_tray(self, save=True):
        """
        Moves the bubble next to the system tray (bottom-right corner).
        On Wayland clients cannot position themselves — show + raise and
        start a compositor move so one drag flings it back wherever you
        want it (the tray click provides the input serial).
        """
        self.show()
        self.raise_()
        wh = self.windowHandle()
        if wh is not None and wh.startSystemMove():
            return
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.window_d + 1,
                  screen.bottom() - self.window_d + 1)
        if save:
            self._save_state()


class BubbleCore(QWidget):
    """
    The center circle + tail icon, as a child widget stacked ABOVE the
    habit squares — collapsed squares slide behind it (black-hole
    collapse). It is transparent for mouse events, so clicking, dragging
    and hovering the middle behave exactly as they did when the
    container painted the circle itself.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(BUBBLE_D, BUBBLE_D)
        pm = QPixmap(TAIL_ICON)
        if not pm.isNull():
            # fill the circle: the icon's edge reaches the circle's inner
            # edge (the source image is square, so it spans the diameter)
            self.tail_pm = pm.scaled(BUBBLE_D - 4, BUBBLE_D - 4,
                                     Qt.KeepAspectRatio,
                                     Qt.SmoothTransformation)
        else:
            self.tail_pm = QPixmap()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPoint(BUBBLE_D // 2, BUBBLE_D // 2)
        p.setPen(Qt.NoPen)
        p.setBrush(BG_COLOR)
        p.drawEllipse(c, BUBBLE_D // 2, BUBBLE_D // 2)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(BORDER_RUN if self.window().any_running()
                      else BORDER_IDLE, 2))
        p.drawEllipse(c, BUBBLE_D // 2, BUBBLE_D // 2)
        if not self.tail_pm.isNull():
            p.drawPixmap(c.x() - self.tail_pm.width() // 2,
                         c.y() - self.tail_pm.height() // 2, self.tail_pm)
        else:
            p.setPen(TEXT_COLOR)
            p.setFont(QFont('Sans', 12, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter, 'tail')
        p.end()


class FlashLabel(QWidget):
    """Transient confirmation label shown near the bubble."""

    def __init__(self, text: str, anchor: 'BubbleWidget'):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowTitle('Tail PC Widget Flash')  # matched by keep_above.js
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowIcon(QIcon(TAIL_ICON))
        f = QFont('Sans', 9, QFont.Bold)
        w = QFontMetrics(f).horizontalAdvance(text) + 20
        self.setFixedSize(w, 26)
        self._text, self._font = text, f
        geo = anchor.frameGeometry()
        self.move(geo.center().x() - w // 2, geo.top() - 32)
        self.show()
        QTimer.singleShot(2600, self.close)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 20, 24, 235))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        p.setPen(DOT_ACKED if self._text.endswith('✓') else TEXT_COLOR)
        p.setFont(self._font)
        p.drawText(self.rect(), Qt.AlignCenter, self._text)
        p.end()


class KeepOpenMenu(QMenu):
    """
    QMenu that stays open when an action flagged `keep_open` is clicked,
    so the backdate item can be pressed repeatedly without reopening.
    """

    def mouseReleaseEvent(self, e):
        act = self.actionAt(e.pos())
        if act is not None and act.property('keep_open'):
            if act.isEnabled():
                act.trigger()
            e.accept()
            return
        super().mouseReleaseEvent(e)


class PcBubbleApp:
    """Wires the bubble, tray icon, menus and the single-instance guard."""

    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.bubble = BubbleWidget()
        self.bubble.show()

        self.tray = QSystemTrayIcon(QIcon(TAIL_ICON), qapp)
        self.tray.setToolTip('Tail PC Widget')
        menu = QMenu()
        act_recall = QAction('Recall bubble to tray', menu)
        act_recall.triggered.connect(lambda: self.bubble.recall_to_tray())
        act_toggle = QAction('Hide / show bubble', menu)
        act_toggle.triggered.connect(self.toggle_bubble)
        act_quit = QAction('Quit', menu)
        act_quit.triggered.connect(self.quit)
        menu.addAction(act_recall)
        menu.addAction(act_toggle)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

        # expose helpers the bubble calls into
        self.bubble.open_bubble_menu = self.open_bubble_menu
        self.bubble.open_square_menu = self.open_square_menu
        self.bubble.show_flash = self.show_flash

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if not self.bubble.isVisible():
                self.bubble.show()
            self.bubble.recall_to_tray()

    def toggle_bubble(self):
        self.bubble.setVisible(not self.bubble.isVisible())

    def open_bubble_menu(self, global_pos):
        menu = QMenu()
        menu.addAction('Recall to tray',
                       lambda: self.bubble.recall_to_tray())
        menu.addAction('Hide bubble', self.toggle_bubble)
        menu.addSeparator()
        menu.addAction('Quit', self.quit)
        self.bubble._pin_spread = True   # keep the ring spread under the menu
        menu.exec_(global_pos)
        self.bubble._pin_spread = False
        self.bubble._check_proximity()

    def open_square_menu(self, sq, global_pos):
        """
        Per-habit right-click menu. The backdate action keeps the menu
        open, so clicking it again pushes the start another minute back.
        """
        bubble = self.bubble
        menu = KeepOpenMenu()
        running = sq.habit_name in bubble.timers
        head = menu.addAction('{} — {}'.format(
            sq.habit_name,
            'running {}'.format(fmt_elapsed(bubble.elapsed_for(sq.habit_name)))
            if running else 'timer idle'))
        head.setEnabled(False)
        menu.addSeparator()
        act = menu.addAction('⏪ Started 1 min earlier' if running
                             else 'No timer running')
        act.setEnabled(running)

        def backdate_one_more():
            if bubble.backdate_timer(sq.habit_name, 1):
                start = bubble.timers.get(sq.habit_name)
                act.setText('⏪ 1 more min earlier (started {})'.format(
                    start.strftime('%H:%M') if start else '?'))

        act.setProperty('keep_open', True)
        act.triggered.connect(backdate_one_more)
        bubble._pin_spread = True   # keep the ring spread under the menu
        menu.exec_(global_pos)
        bubble._pin_spread = False
        bubble._check_proximity()

    def show_flash(self, habit: str, minutes: int, queued: bool):
        if minutes > 0:
            text = '{} {}m → phone {}'.format(
                habit, minutes, '✓' if queued else '(write FAILED)')
        else:
            text = '{} +1 → phone {}'.format(
                habit, '✓' if queued else '(write FAILED)')
        FlashLabel(text, self.bubble)

    def quit(self):
        self.bubble._save_state()
        self.tray.hide()
        self.qapp.quit()


KEEP_ABOVE_JS = """\
function tailPcKeepAbove(w) {
    var c = String(w.caption);
    if (c === "Tail PC Widget" || c === "Tail PC Widget Flash"
            || c === "Tail PC Widget Tip") {
        w.keepAbove = true;
        w.skipTaskbar = true;   // tray-only: no taskbar entry on KDE/Wayland
    }
}
workspace.windowAdded.connect(tailPcKeepAbove);
workspace.windowList().forEach(tailPcKeepAbove);
"""


def _enforce_keep_above() -> bool:
    """
    KDE/Wayland: clients cannot request keep-above (Qt's
    WindowStaysOnTopHint is X11-only), so load a tiny KWin script via
    DBus that sets keepAbove on our windows — now and for any window
    added later this session (flash labels). Silently no-ops on non-KDE
    or on any failure.
    """
    try:
        js_dir = os.path.expanduser('~/.config/pc_bubble_widget')
        # v3: also keeps the custom tooltip window above; fresh filename so
        # KWin reloads the content
        js_path = os.path.join(js_dir, 'keep_above_v3.js')
        os.makedirs(js_dir, exist_ok=True)
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(KEEP_ABOVE_JS)
        for cmd in (
            ['qdbus6', 'org.kde.KWin', '/Scripting',
             'org.kde.kwin.Scripting.loadScript', js_path],
            ['qdbus', 'org.kde.KWin', '/Scripting',
             'org.kde.kwin.Scripting.loadScript', js_path],
        ):
            try:
                subprocess.run(cmd, check=False, capture_output=True, timeout=5)
                break
            except (OSError, subprocess.TimeoutExpired):
                continue
        for cmd in (
            ['qdbus6', 'org.kde.KWin', '/Scripting',
             'org.kde.kwin.Scripting.start'],
            ['qdbus', 'org.kde.KWin', '/Scripting',
             'org.kde.kwin.Scripting.start'],
        ):
            try:
                subprocess.run(cmd, check=False, capture_output=True, timeout=5)
                break
            except (OSError, subprocess.TimeoutExpired):
                continue
        return True
    except Exception:
        return False


def _already_running() -> bool:
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE_KEY)
    running = sock.waitForConnected(150)
    if running:
        sock.disconnectFromServer()
    return running


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('Tail PC Widget')
    app.setWindowIcon(QIcon(TAIL_ICON))  # tail icon wherever the DE shows one
    if _already_running():
        return 0
    server = QLocalServer()  # kept alive for the app's lifetime
    QLocalServer.removeServer(INSTANCE_KEY)
    server.listen(INSTANCE_KEY)
    _ = PcBubbleApp(app)
    # KDE/Wayland: force keep-above via a KWin script (the bubble window
    # must already exist here; flash labels are covered by windowAdded).
    # No-op on other desktops. Qt's WindowStaysOnTopHint is X11-only.
    _enforce_keep_above()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
