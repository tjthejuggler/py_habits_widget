# py_habits_widget

A PyQt5 desktop widget for the **Tail Habit Tracker**, mirroring the Android app's `HabitGridScreen` layout.

## Layout

```
┌──────────────────────────────────────────────────────────┐
│  ◀  Today / date  ▶       [📊] [✏] [ℹ] [🔒] [⚙]       │  ← Top bar
├──────────────────────────────────────────────────────────┤
│  [general]  [screen2]  [screen3]                    │  ← Screen tabs
├─────────────────────────────────────────────────────┤
│                                                     │
│   8-column × 10-row grid of HabitButton cells       │  ← Main grid
│                                                     │
├─────────────────────────────────────────────────────┤
│  Info panel  /  Edit control bar  (conditional)     │  ← Bottom panel
└─────────────────────────────────────────────────────┘
```

## Running

```bash
source py_habits_widget/bin/activate
python py_widget.py
# or use the launch script:
bash start_py_widget.sh
```

## Key Files

| File | Purpose |
|------|---------|
| `py_widget.py` | Main app entry point, window assembly |
| `habit_button.py` | Individual habit cell widget (dynamic sizing) |
| `habit_view_model.py` | State management / ViewModel |
| `habit_models.py` | Data models (`Habit`, `HabitScreen`, `AppSettings`) |
| `habits_repository.py` | Reads/writes the habits SQLite database |
| `settings_repository.py` | Persists app settings to `~/.config/py_habits_widget/settings.json` |
| `habit_colors.py` | Color and icon mapping per habit |
| `habit_calculator.py` | Streak and stat calculations |
| `info_panel.py` | Bottom info panel (info mode) |
| `edit_control_bar.py` | Bottom edit control bar (edit mode) |
| `graphs_panel.py` | Bottom graphs panel (graph mode) |
| `dialogs.py` | All modal dialogs |

## Persistent Files

| Path | Contents |
|------|---------|
| `~/.config/py_habits_widget/settings.json` | Habit screens, icons, input modes, etc. |
| `~/.config/py_habits_widget/window_geometry.json` | Saved window size and position |

## Dynamic Resizing

*(Added 2026-03-29)*

The window is fully resizable. All grid cells, icons, and text scale proportionally as the window is resized:

- **`HabitButton`** and **`PlaceholderCell`** accept a `cell_size` parameter instead of using a fixed constant.
- Font size, icon size, corner radius, and text margins all scale relative to the cell size.
- `HabitGridWidget.resizeEvent` debounces resize events (80 ms) and recomputes `cell_size` from the window width using:
  ```
  cell_size = (window_width - 2×margin - 7×spacing) / 8
  ```
- Minimum cell size is **40 px** to keep the widget usable when shrunk.

## Window Geometry Persistence

*(Added 2026-03-29)*

Window size and position are saved to `~/.config/py_habits_widget/window_geometry.json` on close and restored on next launch. The position is clamped to the available screen area so the window is never off-screen.

## Read-Only Mode

*(Added 2026-04-01)*

A **read-only toggle** (🔒/🔓) in the top bar prevents the widget from writing to `~/habitsdb/habitsdb.txt`. This is useful when the file is synced from a phone via Syncthing and the desktop should only display data, not modify it.

- **🔒 (red, active)** — Read-only ON: no writes to `habitsdb.txt`. `ensure_days_exist()` still fills missing days in memory for display, but never saves to disk. `increment_habit()` and `set_habit_count()` are no-ops.
- **🔓 (default)** — Read-only OFF: normal read/write behavior (original behavior).

The setting is persisted in `~/.config/py_habits_widget/settings.json` as `read_only_mode` and remembered across restarts.

## PC Floating Bubble Widget

*(Added 2026-08-18; switched to Tail Bridge transport same day)*

`pc_bubble_widget.py` is a small frameless always-on-top circle with the tail
icon, draggable anywhere on screen, with one habit square per habit toggled
**"PC widget"** in the phone app's edit mode. Clicking a square starts that
habit's timer; clicking again stops it and queues an event (duration + the
real start time) for the phone. Lives in the system tray — no taskbar entry;
tray click or menu recalls the bubble next to the tray.

- **Run:** `./start_pc_bubble.sh` (uses the project venv)
- **Transport:** the local **Tail Bridge** (`http://127.0.0.1:8001`) — the
  same FastAPI server that serves the Garmin proxy data and the movie cache.
  Zero setup: the auth token is auto-resolved from the environment or the
  bridge's `.env` file, and the phone derives the bridge URL from its Garmin
  settings, exactly like the movie-bridge feature. Endpoints:
  - `GET/POST /api/v1/pc_widget/config` (phone → PC) — habit squares to show
  - `POST /api/v1/pc_widget/event` (PC → phone) — queue one event
    (the bridge assigns the ID — it is the single writer of its state)
  - `GET /api/v1/pc_widget/events` (PC) — events not yet acked
  - `POST /api/v1/pc_widget/acks` (phone → PC) — acks; the bridge prunes
- **Delivery:** at-least-once + acks = effectively-once. Events queued while
  the phone is offline deliver on its next poll (the phone polls the bridge
  every 45 s while its bubble service runs). Orange dot on a square =
  queued; green flash = phone confirmed. If the bridge is down the widget
  keeps its squares and badges and shows a write-failure flash.
- **Tooltips** (custom, per-widget — 2026-08-19): each habit square shows its
  *own* hover message — habit name, its count for today ("today: 23 min" /
  "today: 3 pts" — unit follows the habit's minutes-primary setting), and —
  while a dot is showing — what it's reporting ("waiting for the phone to
  sync" / "phone confirmed ✓"). Hovering the **center bubble only** shows the
  summary: today's total points plus the 7-day and 30-day daily averages.
  These are *not* Qt built-in tooltips: Qt's receiver tracking goes stale when
  squares glide under a stationary cursor (the container's text kept winning,
  so one message appeared for the whole widget). Instead the bubble's own
  Enter/Leave tracking drives a custom `BubbleToolTip` window (600 ms hover
  delay, hidden on leave/click/drag/menu). Numbers come from
  `pc_widget_stats.py`, which reads the Syncthing-synced
  `~/habitsdb/habitsdb.txt` (mtime-cached, so it re-reads only when the
  phone's copy syncs over).
- **Session semantics** mirror the phone's bubble timer: ≥1 min → +1 session
  AND +minutes on the habit's secondary value; <1 min → simple +1 tap.
  Timestamps are recorded at the event's own start time on the phone.
- **State** (bubble position + running timers) persists across restarts in
  `~/.config/pc_bubble_widget/state.json`.
- **Single instance** guard via a local socket (`pc-bubble-widget-singleton`).
- `pc_widget_sync.py` is the Qt-free HTTP IO module (stdlib urllib only,
  never raises on transport errors) — smoke-testable standalone with
  `pc_widget_smoke_test.py` (spins up an in-process fake bridge + offscreen
  Qt widget and checks the full config → tap → ack → prune round-trip).
- **KDE/Wayland notes** (fixed 2026-08-18): Qt/Wayland ignores absolute
  `move()` and doesn't implement `WindowStaysOnTopHint`, so —
  - dragging uses compositor-driven moves (`QWindow.startSystemMove()`);
    manual offset dragging remains the X11 fallback.
  - keep-above is enforced by a tiny KWin script the widget auto-loads via
    DBus at startup (`~/.config/pc_bubble_widget/keep_above_v3.js`, matches the
    window titles "Tail PC Widget" / "Tail PC Widget Flash" /
    "Tail PC Widget Tip"). It re-applies to windows added later in the
    session; silently no-ops on non-KDE.
  - "Recall bubble to tray" starts an interactive compositor move on
    Wayland (clients cannot position themselves) — one drag flings it back.

## PC Bubble Widget — Proximity Ring & Backdating

*(Added 2026-08-19)*

- **Ring layout:** idle squares tuck in deep **behind** the bubble while the
  mouse is away; **running timers always stay out at rest radius** (a 4 px
  sliver of a gap to the bubble) so they remain prominent. When the cursor
  moves over the widget the whole ring spreads out (radius sized so every
  square gets a non-overlapping clickable slot) and glides back when it
  leaves. Spread detection is Wayland-safe: Enter/Leave events on the
  container + squares drive it (120 ms debounce for container↔square
  transitions, and a pin keeps the ring out while a context menu is open).
  On X11 a 40 ms cursor poll additionally spreads the ring a square-width
  *before* the pointer enters the window — Wayland clients cannot query the
  global cursor (`QCursor.pos()` freezes outside our windows, which is why
  pure polling "only worked once"). Easing runs at ~60 Hz on a
  self-stopping QTimer.
- **Black-hole collapse** *(2026-08-19)*: the center circle is now its own
  child widget (`BubbleCore`) stacked **above** the squares, so tucked
  squares collapse *behind* it — and as they tuck, the side nearest the
  center is squeezed and faded strip-by-strip (a pinch warp rendered with
  `SmoothPixmapTransform`, applied to the whole square body — rounded rect,
  icon, dots — so the icons warp too). Strips stay axis-aligned, so the
  content never rotates — only the squeeze direction follows the ring. The
  squeeze/fade follows the animated ring radius, so the morph plays on every
  collapse/expand. `BubbleCore` is `WA_TransparentForMouseEvents`: clicks,
  drags and hover over the middle keep flowing to the container exactly as
  before.
- **Android-matched habit colours** *(2026-08-19)*: each square's
  background (and border rings) mirrors the phone app's habit-button style
  for that habit's **effective points** today — the exact `getHabitStyle`
  ladder of `ui/HabitColors.kt`: 0-5 solid muted backgrounds (red → orange
  → green → blue → pink → yellow), 6 glass, 7-12 glass + single vivid
  border cycling Red→Yellow, 13-48 glass + double vivid border (outer |
  black | inner, capped at 49). Mirrored Qt-free in `pc_widget_stats.py`
  (`habit_style`); effective points mirror the phone's
  `effectivePointsForDate` (see the next bullet).
- **Bigger tail icon** *(2026-08-19)*: the tail image in the center circle
  now spans the circle's inner diameter (its edge touches the inner edge of
  the circle) instead of floating smaller inside.
- **Effective points, not raw counts** *(2026-08-19)*: square colours and
  the tooltip's today/week/month numbers are now the points the phone
  itself shows — `HabitViewModel.effectivePointsForDate` mirrored in
  `pc_widget_stats.py`: minutes-primary habits score their
  `minutes:<habit>` slot through the divider (session count standing in on
  zero-minute days), other habits score raw/divider, inverted-binary
  habits score 1 when not done, `noPointsHabits`/`disabledHabits` score
  nothing, and auxiliary `minutes:`/`secondary_value*:` slots are never
  summed as habits (raw minutes had inflated the totals ~10×). Per-habit
  config comes from the bridge config's `divider` field (consumed as soon
  as the phone sends it), a user overrides file
  (`~/.config/pc_bubble_widget/point_overrides.json`), or the newest
  parseable tail backup's settings block (`~/habitsdb/Auto_backups/`
  daily, `Manual_backups/` — mid-sync files are skipped), defaulting to
  divider 30 for minutes-primary habits.
- **Wayland hover recovery + tooltips at the cursor** *(2026-08-19)*:
  after a compositor drag (`startSystemMove`) Qt can miss Leave events,
  which used to wedge the ring spread on forever; drags now reset the
  hover state, mouse tracking lets plain motion over the widget re-arm
  hover when no Enter ever fires, and a presence watchdog drops hover when
  the cursor reading has been frozen for 3 s outside the window. Tooltips
  switched from our own top-level window (whose `move()` KWin ignores —
  it kept appearing at the spawn point) to `QToolTip` popups, which the
  platform anchors right at the cursor; each square still gets its own
  message via our enter/leave targeting.
- **Dragging:** left-drag anywhere on the widget moves it — from the bubble
  directly, or from any square. Squares disambiguate click vs drag: under
  8 px of movement = a click (toggles the timer on release), 8 px or more =
  the whole widget follows the pointer (compositor-driven move on Wayland).
  This matters because the tucked idle squares cover the bubble at rest.
- **Right-click a habit square** → per-habit menu (every action carries an
  icon) with a repeatable **"Started 1 min earlier"** action: each click
  pulls the running timer's start another minute into the past (the label
  shows the resulting start clock time, and the menu stays open for repeated
  clicks). The backdated start is what gets synced to the phone, and it
  persists across restarts.
- **Tray-only presence:** the KWin startup script now also sets
  `skipTaskbar` on the widget's windows (KDE/Wayland), and the app plus its
  windows carry the tail icon, so any DE that insists on a taskbar entry at
  least shows the right icon.
- Running timers are restored as "running" squares after a restart
  (previously the persisted timer kept counting but its square painted as
  idle).

## PC Bubble Widget — Window Auto-Detect Timers

*(Added 2026-08-20)*

Right-click a habit square → **"🎯 Auto-detect window…"** pops up every
open window type (deduplicated by app class — four VSCode windows list as
one `code` entry, hover shows a sample title). Pick one and that habit's
timer runs itself whenever you actually use that app:

- **Auto-start** only when you actually interact with the paired window:
  it must be the active (focused, not minimized) window AND a real key
  or button press must land INSIDE it after it became active. Merely
  bringing it to the front — alt-tab, taskbar click, clicking the icon
  to cycle its windows, maximize — never starts the timer: mouse
  movement, button releases and the press that raised the window don't
  count; your first real click/keystroke in it does.
- **Auto-stop (debounced)** when you switch away or minimize the window,
  or after 15 s of no keyboard/mouse input at all — but the timer keeps
  running through a three-minute **grace period** first. Get back to the
  window within those three minutes and the SAME session simply continues (same
  start, one increment on the phone). Only when the grace period lapses is the
  session finalized — retroactively stamped as finished at the moment
  the window activity actually stopped, so brief window switches can't
  chop one session into a clutter of tiny ones. Manual stops bypass the
  grace and apply immediately.
- **Manual always wins**: clicking the square stops the timer and
  suppresses auto-start until you leave that window once (so it can't
  fight you); timers you started by hand are never auto-stopped.
- Nothing is hardcoded — any habit ↔ any window class, several habits
  can be paired at once, and pairs persist in
  `~/.config/pc_bubble_widget/auto_detect.json` (idle timeout lives
  there too, `idle_seconds`).

How it works on this KDE/Wayland machine (`auto_detect.py`):

- A resident KWin script (loaded over DBus like the keep-above one)
  pushes active-window/minimize events to a `org.pyhabits.AutoDetect`
  DBus service the widget registers; a one-shot KWin script answers the
  window listing. On plain X11 it falls back to `wmctrl -lx` +
  `xdotool` polling instead.
- "Typing or clicking" is detected by passively reading the evdev
  devices (`/dev/input/event*`, filtered to key-capable ones) in a
  daemon thread — the reason the user must be in the `input` group.
  Without that permission the idle-stop rule is disabled and focus
  alone drives the timer (a flash warns once).
- Desktop plumbing (plasmashell, xwaylandvideobridge, …) and the
  widget's own windows are filtered out of the picker.
- Both backends timestamp every active-window change by window
  IDENTITY (`_FocusTracker`: class + caption on KWin, window id on
  X11), so cycling between same-class windows still re-arms the rule.
  Auto-start requires a key/button PRESS strictly after that moment —
  the evdev stream is parsed so movement, releases and autorepeat
  never satisfy it.
- Grace-period stops live entirely in the widget layer (`auto_detect.py`
  is untouched): a timer in its grace minute reports as "not running"
  to the controller, so re-focusing the window re-fires auto-start and
  cancels the pending stop. Pending stops persist in `state.json` — an
  expired one finalizes retroactively right after a restart, and
  quitting the widget flushes any pending grace stops so no session is
  lost.

## PC Bubble Widget — Fast Sync, Visible Indicators, White Icons

*(Added 2026-08-20)*

- **Near-instant phone sync** *(2026-08-20)*: stopping a timer used to
  wait on two stacked delays — the phone's bubble service polled the
  bridge every 45 s, and the widget only noticed acks every 30 s. The
  bridge now has a long-poll endpoint
  (`GET /api/v1/pc_widget/events/wait?timeout=N`) that holds the
  request open until an event is queued, the phone's bubble service
  uses it in a wait→drain→repeat loop (falling back to the 45 s poll
  on bridges without it), and the widget polls acks every 2 s while
  anything is queued (30 s when idle). Net effect: a stopped timer
  lands on the phone and clears its orange dot in ~1–3 s.
- **Instant ack pickup on the PC** *(2026-08-20)*: the fast ack poll
  above only armed *after* the next idle tick — up to 30 s after the
  timer stopped — so the orange "waiting for the phone to sync" dot
  lingered long after the phone had actually confirmed (the long-poll
  delivers its ack ~1 s after the stop). `stop_timer()` now arms the
  fast poll (`ACK_POLL_FAST_MS`, 1 s) the moment the event is queued,
  and `_poll_acks()` re-arms with `start()` instead of `setInterval()`
  so each interval's countdown begins immediately rather than riding
  the remains of the previous schedule. The dot now clears ~1–2 s
  after the phone acks, instead of up to ~30 s later. (Phone-side: the
  Tail app's 2-minute widget-watchdog heartbeat now also drains the
  queue on every fire, so events land within ~2 min even when neither
  the bubble service nor the app is running — ~9 min worst case in
  deep Doze. FCM push remains the only true instant-everywhere option,
  and would need a Firebase project set up.)
- **Indicator squares never collapse** *(2026-08-20)*: any square with
  something to say — a running timer, an orange queued-events dot, or
  the green just-acked flash — now stays out at rest radius instead of
  tucking behind the bubble; only fully idle squares still collapse.
- **White habit icons** *(2026-08-20)*: square icons are recoloured to
  solid white (alpha mask kept), matching the Android app's look.

## PC Bubble Widget — Reliable Hover Tooltips, Correct Minutes

*(Added 2026-08-20)*

- **Hover always targets the right square** *(2026-08-20)*: hovering a
  habit square often showed the center bubble's summary instead. Two
  Qt event races were to blame: the container's Enter can be delivered
  *after* the square's (stealing the tooltip target), and a square
  gliding under a *stationary* cursor while the ring spreads never
  receives an Enter at all. The tooltip target is now resolved
  geometrically at display time (`_square_at_cursor`): whichever
  square's rect contains the cursor wins; positions inside the center
  circle belong to the bubble (tucked squares hide behind it), and the
  old enter/leave tracking only fills in when no square is under the
  cursor.
- **Minutes-primary tooltips show real minutes** *(2026-08-20)*: the
  per-square "today" line printed the habit's raw slot count — the
  session *tally* — labelled as minutes ("3 min" when the phone showed
  22 minutes across 3 sessions). Minutes-primary habits now headline
  the `minutes:<habit>` slot via `HabitStats.habit_minutes_today()`,
  with the session count as detail: "today: 24 min (4 sessions)".
  Count-based habits keep their "today: N pts" line.

## PC Bubble Widget — Stop-and-Edit + Menu Icons

*(Added 2026-08-20)*

- **"Stop and edit times…"** *(2026-08-20)*: new right-click action on a
  habit square (enabled only while its timer runs). It opens a small modal
  dialog pre-filled with the session's real start time and "now" as the
  end, both editable (`QDateTimeEdit` with calendar popups; the end can
  never be dragged before the start — it bumps along automatically).
  **OK** stops the timer and queues the event with the corrected times
  (minutes are recomputed from them, so a fixed start or end fixes the
  synced duration too); **Cancel** changes nothing and the timer keeps
  running. Implemented as a `start` override on
  `BubbleWidget.stop_timer()`, mirroring the existing `end` override the
  auto-detect grace finalization uses.
- **Icons on every right-click menu item** *(2026-08-20)*: the square menu
  (header = the habit's own icon, backdate = seek-back arrows, stop-and-
  edit = pencil, cancel = trashcan, auto-detect = magnifier/binoculars,
  stop-auto-detect = ✕) and the bubble menu (home / arrow-down / power)
  now show icons. Each prefers the system icon theme (Breeze on KDE) and
  falls back to the bundled `icons/transparentglasshd/` set, so nothing
  goes icon-less on themeless setups. The old emoji prefixes were dropped
  in favour of the real icons.
- **"Cancel timer (discard)"** *(2026-08-20)*: right-click action that
  throws a running session away **entirely** — `BubbleWidget.cancel_timer()`
  pops the timer without queueing anything on the bridge, so no event is
  recorded and nothing is ever sent to the phone; the square simply goes
  back to idle (a transient "timer discarded" flash confirms it). A pending
  auto-detect grace stop is dropped too, and the manual-cancel is noted to
  the auto-detect controller (same rule as a manual stop) so a still-
  focused mapped window can't instantly re-start what was discarded.

## PC Bubble Widget — Auto-Detect Self-Healing

*(Added 2026-08-20)*

- **Auto-detect no longer dies after days of uptime** *(2026-08-20)*:
  the evdev input monitor opened `/dev/input` exactly once at startup,
  but keyboards and mice are re-enumerated with NEW event nodes on
  every bluetooth reconnect, dock replug and suspend/resume cycle.
  After a few days the widget was blind to the keyboard actually in
  use — `idle_seconds()` grew without bound, `user_active` was
  permanently false, and auto-start never fired (focusing VSCode no
  longer started "Programming sessions"; anything auto-running was
  auto-stopped instead). Diagnosed live: the 5-day-old process held
  fds only for `event1–20`, while the keyboard in use was `event27`.
  The monitor thread now rescans `/dev/input` every 30 s (and every
  second while it holds no devices at all), adopts new nodes, drops
  vanished ones, and rebuilds its fd set instead of exiting when a
  device disappears underneath it.
- **KWin watcher script is now self-healing** *(2026-08-20)*: a KWin
  restart (crash, Plasma update, `--replace`) silently unloads the
  auto-detect watcher script, and a loaded script can also be stopped
  without being unloaded — either way active-window events stopped
  forever while `isScriptLoaded` still said `true`. A
  `QDBusServiceWatcher` now reinstalls the script the moment
  `org.kde.KWin` reappears on the session bus, and a 60 s watchdog
  polls `isScriptLoaded` and reinstalls the script if it went
  missing. Reinstalling re-pushes the current active window, so the
  backend state re-syncs itself.
- Smoke tests: section **[9]** drives the real monitor thread with a
  pipe-backed fake evdev device and proves activity tracking survives
  a device being replaced under it (the exact long-uptime failure).

*(Added 2026-08-21)*

- **Visible idle countdown replaces the invisible 3-minute grace**
  *(2026-08-21)*: when a mapped window loses focus or input stops for
  `idle_seconds` (now default 5 s, configurable), the habit square
  shows a black box with a red border counting down from
  `countdown_seconds` (default 30 s, configurable). Activity again
  before zero → the same session continues untouched. At zero the
  session is finalized retroactively with `idle + countdown` seconds
  (35 s by default) subtracted from its end — the idle gap and the
  countdown itself never happened. Both durations live in
  `~/.config/pc_bubble_widget/auto_detect.json` and are editable in
  the new settings screen.
- **✕ cancel button on running squares** *(2026-08-21)*: top-right
  small square with a red ✕ — same as the right-click "Cancel timer
  (discard)". The sync dot moves left of it while a timer runs.
- **Running squares are 30% larger** *(2026-08-21)*: 46 → 60 px while
  their timer runs (room for the ✕ and the countdown box); the ring
  spread radius, window size and proximity zone account for the
  larger squares.
- **Center-circle left-click stops every running timer** *(2026-08-21)*:
  with ≥1 timer active, clicking the middle bubble stops and queues
  them all exactly as if each square had been clicked (mapped habits
  get the manual-stop auto-restart suppression); with none running it
  still starts a widget drag.
- **Settings screen** *(2026-08-21)*: the bubble's right-click menu
  gains "Settings…" — a habit picker listing the phone's FULL habit
  catalog (`all_habits`, pushed alongside the widget config) where
  checking a habit queues a `toggle_pc_widget_habit` event on the
  bridge; the phone's event poller applies it to its "PC widget"
  toggles (idempotent — the event carries the ABSOLUTE desired
  state) and pushes the updated config back, so the square appears or
  disappears on the widget's next config poll. The dialog also edits
  the idle threshold and countdown duration, and live-refreshes from
  the phone while open.
- Smoke tests: section **[2b]** rewritten for the countdown (arm /
  cancel / expiry with the 35 s deduction / manual stop mid-countdown
  / state.json persistence incl. deadline + deduct).
