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
action that backdates the running timer, plus "Stop and edit times"
which finalizes the session with user-corrected start/end times.
Every right-click menu action carries an icon (system icon theme,
with the bundled transparent-glass set as fallback).

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

from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QRectF, QDateTime
from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from PyQt5.QtGui import (QIcon, QPixmap, QPainter, QColor, QFont, QPen,
                         QFontMetrics, QCursor)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QAction, QToolTip,
    QDialog, QDateTimeEdit, QFormLayout, QDialogButtonBox, QLabel,
)

from pc_widget_sync import (
    load_config, append_event, pending_events,
)
from pc_widget_stats import HabitStats, habit_style
from auto_detect import AutoDetectController, open_window_picker
from pc_settings_dialog import PcSettingsDialog

try:
    from habit_colors import get_habit_icon_path
except ImportError:  # standalone fallback if habit_colors is unavailable
    def get_habit_icon_path(habit_name, custom_overrides=None):
        return None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TAIL_ICON = os.path.join(SCRIPT_DIR, 'icons', 'tail_icon.png')
STATE_FILE = os.path.expanduser('~/.config/pc_bubble_widget/state.json')
INSTANCE_KEY = 'pc-bubble-widget-singleton'
ICON_SET_DIR = os.path.join(SCRIPT_DIR, 'icons', 'transparentglasshd')


def menu_icon(png_name, *theme_names):
    """
    Icon for a right-click menu action. Prefers the system icon theme
    (Breeze on KDE — scales crisply and matches the desktop), falling
    back to the bundled transparent-glass icon set so every action
    still gets an icon on themeless setups.
    """
    for theme_name in theme_names:
        icon = QIcon.fromTheme(theme_name)
        if not icon.isNull():
            return icon
    path = os.path.join(ICON_SET_DIR, png_name)
    return QIcon(path) if os.path.exists(path) else QIcon()


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
RUN_GROW = 1.30        # running squares grow 30% — room for ✕ + countdown
SQUARE_D_RUN = int(round(SQUARE_D * RUN_GROW))   # 46 → 60 while running
# running squares carry corner chips (✕ / countdown / ←) that stick a
# little past the body — the widget grows a transparent margin for them
BADGE_OVERHANG = 6     # transparent margin around a running square's body
SQUARE_D_RUN_W = SQUARE_D_RUN + 2 * BADGE_OVERHANG  # widget side, running
BADGE_D = 20           # ✕ / ← chip side (px)
COUNTDOWN_W, COUNTDOWN_H = 26, 20   # countdown chip box
BADGE_STICK = 5        # how far chips stick out past the body corner
BADGE_RADIUS = 6       # chip corner rounding (matches the square body)
RUN_GAP = 10           # extra bubble↔square distance while its timer runs
REST_GAP = 4           # bubble↔square gap at rest — just a sliver
REST_R = BUBBLE_D // 2 + REST_GAP + SQUARE_D // 2   # base rest ring; running squares sit RUN_GAP further out
TUCK_R = BUBBLE_D // 2 + SQUARE_D // 2 - 26         # idle: mostly BEHIND the bubble
SPREAD_PAD = 10        # ring spacing per square when spread out for clicking
CORE_PAD = 14          # margin around the circle for its all-timers chips
CORE_D = BUBBLE_D + 2 * CORE_PAD   # center-circle widget side
CORE_BADGE_D = 22      # the circle's ✕ / ← chips (act on ALL timers)
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
CANCEL_RED = QColor(232, 72, 72)       # ✕ strokes + countdown border
OVERLAY_BG = QColor(12, 12, 14, 235)   # countdown box / ✕ button fill

# Ack-poll cadence: 1 s while events are queued (the phone long-polls the
# bridge, so its ack usually lands ~1 s after the timer stops), 30 s when
# the queue is empty. stop_timer() arms the fast cadence the moment an
# event is queued — waiting for the next idle tick to switch is what made
# the orange "waiting for the phone to sync" dot linger ~30 s after the
# phone had already confirmed.
ACK_POLL_FAST_MS = 1_000
ACK_POLL_IDLE_MS = 30_000

# Auto-detected stops run a VISIBLE countdown on the square: when a
# mapped window loses focus (or the user goes idle for idle_seconds —
# see auto_detect.json), a red-bordered countdown box appears on the
# habit square. Activity in that window again before it reaches zero
# → the SAME session simply continues. Reaching zero → the session is
# finalized retroactively with `idle + countdown` seconds (35 s with
# the 5 s / 30 s defaults) subtracted from its end — the idle gap and
# the countdown itself never happened.


def fmt_elapsed(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return '{}:{:02d}:{:02d}'.format(h, m, s) if h else '{:02d}:{:02d}'.format(m, s)


def square_d(running: bool) -> int:
    """
    Habit square WIDGET side — the body grows 30% while running, plus
    the transparent margin its corner chips stick out into.
    """
    return SQUARE_D_RUN_W if running else SQUARE_D


def _tint_pixmap_white(pm: QPixmap) -> QPixmap:
    """
    Recolours an icon to solid white (Android-app style): keep the
    alpha mask, replace every colour with white.
    """
    if pm.isNull():
        return pm
    tinted = QPixmap(pm.size())
    tinted.fill(Qt.transparent)
    p = QPainter(tinted)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(tinted.rect(), QColor(255, 255, 255))
    p.end()
    return tinted


def _badge_box(p: QPainter, rect: QRect, border: QColor):
    """Chip base: rounded dark box with a 1 px coloured border."""
    p.setPen(QPen(border, 1))
    p.setBrush(OVERLAY_BG)
    p.drawRoundedRect(QRectF(rect), BADGE_RADIUS, BADGE_RADIUS)
    p.setBrush(Qt.NoBrush)


def draw_x_badge(p: QPainter, rect: QRect):
    """✕ chip — discards the timer (red, like the menu's cancel)."""
    _badge_box(p, rect, CANCEL_RED)
    pen = QPen(CANCEL_RED, 2)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    m = 6
    p.drawLine(rect.left() + m, rect.top() + m,
               rect.right() - m, rect.bottom() - m)
    p.drawLine(rect.left() + m, rect.bottom() - m,
               rect.right() - m, rect.top() + m)


def draw_back_badge(p: QPainter, rect: QRect):
    """← chip — pulls the timer's start 1 minute further back."""
    _badge_box(p, rect, QColor(130, 130, 140))
    pen = QPen(TEXT_COLOR, 2)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    cy = rect.center().y()
    m, head = 5, 4
    p.drawLine(rect.right() - m, cy, rect.left() + m, cy)
    p.drawLine(rect.left() + m, cy, rect.left() + m + head, cy - head)
    p.drawLine(rect.left() + m, cy, rect.left() + m + head, cy + head)


def draw_countdown_badge(p: QPainter, rect: QRect, seconds_left):
    """Countdown chip — dark box, red border, the two big digits."""
    _badge_box(p, rect, CANCEL_RED)
    p.setPen(TEXT_COLOR)
    p.setFont(QFont('Sans', 9, QFont.Bold))
    p.drawText(rect, Qt.AlignCenter,
               '{:02d}'.format(max(0, int(seconds_left)) % 100))


class HabitSquare(QWidget):
    """One habit square: click to start/stop its timer."""

    def __init__(self, habit: dict, parent=None):
        super().__init__(parent)
        self.habit_name = habit['name']
        self.icon_name = habit.get('icon')
        self.minutes_primary = habit.get('minutes_primary', False)
        self.running = False
        self.countdown_left = None   # seconds shown in the idle-countdown box
        self.pending = 0          # queued-but-unacked events for this habit
        self.acked_flash_until = 0.0
        self._angle = 0.0         # ring position in radians (set by the bubble)
        self._radius = float(TUCK_R)  # current ring radius (animated)
        self._press_pos = None    # global press pos while click-vs-drag is pending
        self._x_rect = None       # hit rect of the ✕ chip (set while rendering)
        self._back_rect = None    # hit rect of the ← chip (set while rendering)
        self.setFixedSize(SQUARE_D, SQUARE_D)
        self.setMouseTracking(True)   # hover self-heal needs no-button moves
        self.setCursor(Qt.PointingHandCursor)
        self._icon_src = self._load_icon()   # tinted, unscaled
        self._icon_cache = {}     # (box_w, box_h) → scaled icon (2 sizes max)

    def _apply_size(self):
        """Running squares are 30% larger — room for the ✕ and countdown."""
        d = square_d(self.running)
        if self.width() != d or self.height() != d:
            self.setFixedSize(d, d)

    def _load_icon(self):
        overrides = {self.habit_name: self.icon_name} if self.icon_name else None
        path = get_habit_icon_path(self.habit_name, overrides)
        if path and os.path.exists(path):
            pm = QPixmap(path)
            if not pm.isNull():
                # cap the source so the cache stays tiny; scaling to
                # the body happens per size in _icon_for()
                if pm.width() > 128 or pm.height() > 128:
                    pm = pm.scaled(128, 128,
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
                return _tint_pixmap_white(pm)
        return QPixmap()

    def _icon_for(self, body_d: int):
        """
        The white icon scaled to nearly fill the body — only a slim
        margin, a little more at the bottom while running so the
        elapsed label fits underneath.
        """
        if self._icon_src is None or self._icon_src.isNull():
            return None
        box_w = body_d - 10
        box_h = body_d - (22 if self.running else 14)
        pm = self._icon_cache.get((box_w, box_h))
        if pm is None:
            pm = self._icon_src.scaled(
                box_w, box_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._icon_cache[(box_w, box_h)] = pm
        return pm

    def tooltip_lines(self):
        """
        This square's hover message: habit name, its count for today,
        and — while a dot is showing — what the dot is reporting
        (orange = queued events the phone hasn't picked up yet,
        green = the phone just confirmed).
        """
        win = self.window()
        win.stats.refresh()
        if self.minutes_primary:
            # the raw slot counts SESSIONS — headline the minutes the
            # phone writes to minutes:<habit>, session tally as the
            # detail (mirrors the Android habit screen's
            # "22 minutes, 3 timestamps")
            minutes = win.stats.habit_minutes_today(self.habit_name)
            sessions = win.stats.habit_today(self.habit_name)
            today = ('today: {} min ({} session{})'.format(
                minutes, sessions, '' if sessions == 1 else 's')
                if sessions else 'today: {} min'.format(minutes))
        else:
            today = 'today: {} pts'.format(
                win.stats.habit_today(self.habit_name))
        lines = [self.habit_name, today]
        if time.time() < self.acked_flash_until:
            lines.append('phone confirmed ✓')
        elif self.pending > 0:
            lines.append('{} events waiting for the phone to sync'.format(
                self.pending) if self.pending != 1
                else 'waiting for the phone to sync')
        return lines

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.running:
                win = self.window()
                if (self._x_rect is not None
                        and self._x_rect.contains(e.pos())):
                    # the ✕ chip: discard the timer outright — same as
                    # the right-click menu's "Cancel timer (discard)"
                    win._hide_tooltip()  # type: ignore[attr-defined]
                    win.cancel_timer(self.habit_name)  # type: ignore[attr-defined]
                    return
                if (self._back_rect is not None
                        and self._back_rect.contains(e.pos())):
                    # the ← chip: pull the start 1 min back — same as
                    # the right-click menu's backdate option
                    win._hide_tooltip()  # type: ignore[attr-defined]
                    win.backdate_timer(self.habit_name, 1)  # type: ignore[attr-defined]
                    return
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
        habit's phone-matched tier colour, icon, dots, timer, and while
        running the ✕ / ← chips + idle-countdown box sticking slightly
        out past the body's corners — so the black-hole warp can distort
        all of it.
        """
        d = self.width()            # running squares are the larger widgets
        pm = QPixmap(d, d)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        bg_hex, border_hex, outer_hex, inner_hex = self._today_style()
        bg = QColor(bg_hex)
        bg.setAlpha(235)   # let the dark widget bleed through just slightly
        on_glass = QColor(bg_hex).lightness() > 128   # glass bg → dark text
        fg = QColor(20, 20, 24) if on_glass else TEXT_COLOR

        # the body: inset by the chip margin while running so the corner
        # chips can stick out beyond it
        bx = BADGE_OVERHANG if self.running else 1
        bd = d - 2 * bx
        r = 12.0
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(bx, bx, bd, bd, r, r)
        p.setBrush(Qt.NoBrush)
        if self.running:
            p.setPen(QPen(BORDER_SQ_RUN, 2))
            p.drawRoundedRect(bx, bx, bd, bd, r, r)
        elif inner_hex:
            # phone phase 4: double vivid border with a thin black gap
            p.setPen(QPen(QColor(outer_hex), 1))
            p.drawRoundedRect(QRectF(bx - 0.5, bx - 0.5, bd + 1, bd + 1), r, r)
            p.setPen(QPen(Qt.black, 1))
            p.drawRoundedRect(QRectF(bx + 1.5, bx + 1.5, bd - 3, bd - 3),
                              r - 2, r - 2)
            p.setPen(QPen(QColor(inner_hex), 1))
            p.drawRoundedRect(QRectF(bx + 3.5, bx + 3.5, bd - 7, bd - 7),
                              r - 4, r - 4)
        else:
            p.setPen(QPen(QColor(border_hex) if border_hex else BORDER_IDLE,
                          2 if border_hex else 1))
            p.drawRoundedRect(bx, bx, bd, bd, r, r)

        icon = self._icon_for(bd)
        if icon is not None:
            p.drawPixmap(bx + bd // 2 - icon.width() // 2,
                         bx + bd // 2 - icon.height() // 2
                         - (4 if self.running else 3),
                         icon)
        else:
            p.setPen(fg)
            p.setFont(QFont('Sans', 14 + (4 if self.running else 0),
                            QFont.Bold))
            initial = self.habit_name[:1].upper()
            p.drawText(QRect(bx, bx, bd, bd).adjusted(0, -4, 0, -4),
                       Qt.AlignCenter, initial)

        if self.running:
            secs = self.window().elapsed_for(self.habit_name)  # type: ignore[attr-defined]
            p.setPen(fg)
            p.setFont(QFont('Sans', 7, QFont.Bold))
            p.drawText(QRect(bx, bx + bd - 16, bd, 14),
                       Qt.AlignCenter, fmt_elapsed(secs))

        # idle countdown: rounded chip, red border, two digits — stuck
        # slightly out past the body's top-left corner
        if self.countdown_left is not None:
            draw_countdown_badge(
                p, QRect(bx - BADGE_STICK, bx - BADGE_STICK,
                         COUNTDOWN_W, COUNTDOWN_H),
                self.countdown_left)

        # ✕ (top-right) discards the timer; ← (bottom-left) pulls its
        # start 1 min back — both running-only, sticking out likewise
        self._x_rect = None
        self._back_rect = None
        if self.running:
            xr = QRect(bx + bd - BADGE_D + BADGE_STICK, bx - BADGE_STICK,
                       BADGE_D, BADGE_D)
            self._x_rect = xr
            draw_x_badge(p, xr)
            br = QRect(bx - BADGE_STICK, bx + bd - BADGE_D + BADGE_STICK,
                       BADGE_D, BADGE_D)
            self._back_rect = br
            draw_back_badge(p, br)

        # sync dot: inside the body's top-right, clear of the ✕ chip
        dot_x = (bx + bd - 26) if self.running else (d - 12)
        dot_y = (bx + 4) if self.running else 5
        if self.pending > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(DOT_PENDING)
            p.drawEllipse(dot_x, dot_y, 8, 8)
        elif time.time() < self.acked_flash_until:
            p.setPen(Qt.NoPen)
            p.setBrush(DOT_ACKED)
            p.drawEllipse(dot_x, dot_y, 8, 8)
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
        d = self.width()
        n = 16
        w = d / n
        for i in range(n):
            c = (i + 0.5) * w           # strip centre along the axis
            outward = ux if vertical else uy
            f = (c / d) if outward > 0 else 1 - (c / d)
            s = 1.0 - PINCH * t * (1.0 - f)
            p.setOpacity(1.0 - PINCH_FADE * t * (1.0 - f))
            if vertical:
                p.drawPixmap(
                    QRectF(c - w / 2, d * (1 - s) / 2,
                           w, d * s),
                    pm, QRectF(c - w / 2, 0, w, d))
            else:
                p.drawPixmap(
                    QRectF(d * (1 - s) / 2, c - w / 2,
                           d * s, w),
                    pm, QRectF(0, c - w / 2, d, w))
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
        # habit -> {stopped_at, deadline, deduct}: the visible idle
        # countdown state (deadline drives the box, deduct the retroactive
        # end-time correction when it fires)
        self.pending_auto_stops = {}
        self._grace_timers = {}           # habit -> single-shot countdown QTimer
        self.auto_note_toggle = None      # set by PcBubbleApp (auto-detect)
        self._drag_offset = None          # type: QPoint | None
        self._config_sig = None          # (name, icon, minutes_primary) tuple
        self._spread_r = REST_R           # spread ring radius (per habit count)
        self._near = False                # mouse inside the approach zone?
        self.window_d = 2 * (REST_R + RUN_GAP + SQUARE_D_RUN_W // 2) + 8
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
        self.ack_timer.start(ACK_POLL_IDLE_MS)
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
        # its own non-overlapping clickable slot (sized for RUNNING
        # squares — they are the big ones); the window grows to match
        self._spread_r = (max(REST_R, int(math.ceil(
            n * (SQUARE_D_RUN_W + SPREAD_PAD) / (2 * math.pi)))) if n else REST_R)
        new_d = 2 * (self._spread_r + RUN_GAP + SQUARE_D_RUN_W // 2) + 8
        if new_d != self.window_d:
            self.window_d = new_d
            self.setFixedSize(new_d, new_d)
        for i, habit in enumerate(habits):
            sq = HabitSquare(habit, self)
            sq._angle = math.radians(90 - i * 360.0 / n) if n else 0.0
            sq.running = habit['name'] in self.timers  # restore persisted timers
            sq._apply_size()           # running squares start out 30% larger
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
        mouse is away; squares with ANY indicator — a running timer, a
        queued-events dot or the green just-acked flash — always stay
        out at rest radius so they stay prominent, and an approaching
        mouse spreads the whole ring out so every square is easy to click.
        """
        if self._near:
            base = float(self._spread_r)
        else:
            has_indicator = (sq.running or sq.pending > 0
                             or time.time() < sq.acked_flash_until)
            base = float(REST_R if has_indicator else TUCK_R)
        # a running square also keeps a little extra distance from the
        # circle — its chips stick out, and it stays clear of the core's
        return base + RUN_GAP if sq.running else base

    def _place_square(self, sq: HabitSquare):
        c = self._center()
        x = c.x() + sq._radius * math.cos(sq._angle)
        y = c.y() - sq._radius * math.sin(sq._angle)
        half = sq.width() // 2            # running squares are larger
        sq.move(int(round(x)) - half,
                int(round(y)) - half)

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
        enter_r = self._spread_r + SQUARE_D_RUN
        exit_r = enter_r + 14  # hysteresis: no flicker at the boundary
        self._set_near(d <= (exit_r if self._near else enter_r))

    # ── interaction ─────────────────────────────────────────────────────

    def on_square_clicked(self, sq: HabitSquare):
        self._hide_tooltip()
        name = sq.habit_name
        if name not in self.timers:
            self.start_timer(name)
        else:
            self.stop_timer(name)
        if self.auto_note_toggle is not None:
            self.auto_note_toggle(name, name in self.timers)

    def start_timer(self, habit_name: str) -> bool:
        """Starts a habit's timer (manual click or auto-detect)."""
        if habit_name in self.timers:
            return False
        self.timers[habit_name] = datetime.now()
        for sq in self.squares:
            if sq.habit_name == habit_name:
                sq.running = True
                sq._apply_size()          # 30% larger while running
                self._place_square(sq)
        self._raise_running()
        self._kick_anim()
        for sq in self.squares:
            if sq.habit_name == habit_name:
                sq.update()
        self.update()
        self.core.update()   # the circle's border/chips react at once
        self._save_state()
        return True

    def stop_timer(self, habit_name: str, end=None, start=None):
        """
        Stops a habit's timer, queues the event on the bridge and
        flashes the confirmation. No-op when no timer is running.
        `end` overrides the finish time — auto-detect finalizes
        retroactively at the moment window activity stopped, after
        its grace period lapsed. `start` overrides the session start
        (right-click "Stop and edit": the timer began at the wrong
        time); minutes are recomputed from the corrected times.
        """
        self._cancel_pending_stop(habit_name)
        begun = self.timers.pop(habit_name, None)
        if begun is None:
            return
        if start is not None:
            begun = start
        for sq in self.squares:
            if sq.habit_name == habit_name:
                sq.running = False
                sq._apply_size()          # back to the idle size
                self._place_square(sq)
        self._kick_anim()
        finish = end or datetime.now()
        elapsed = (finish - begun).total_seconds()
        minutes = int(elapsed // 60)
        kind = 'session' if minutes > 0 else 'tap'
        event_id = append_event(habit_name, kind=kind, start=begun,
                                minutes=minutes, end=finish)
        if event_id:
            self.pending_by_habit[habit_name] = \
                self.pending_by_habit.get(habit_name, 0) + 1
            # Arm the fast ack poll NOW. The phone long-polls the bridge
            # and typically acks within ~1 s; on the idle cadence the
            # widget wouldn't look again for up to 30 s, leaving the
            # orange "waiting for the phone to sync" dot up long after
            # the phone had actually applied the event. start() also
            # restarts the countdown from zero.
            self.ack_timer.start(ACK_POLL_FAST_MS)
        self._apply_pending_badges()
        for sq in self.squares:
            if sq.habit_name == habit_name:
                sq.update()
        self.update()
        self.core.update()   # the circle's border/chips react at once
        self._save_state()
        self.window().show_flash(
            habit_name, minutes if kind == 'session' else 0,
            event_id is not None)

    def cancel_timer(self, habit_name: str, flash: bool = True):
        """
        Discards a running timer outright: nothing is queued on the
        bridge, nothing reaches the phone, no event is recorded —
        the session is forgotten as if it never ran.
        """
        self._cancel_pending_stop(habit_name)
        if self.timers.pop(habit_name, None) is None:
            return
        for sq in self.squares:
            if sq.habit_name == habit_name:
                sq.running = False
                sq._apply_size()          # back to the idle size
                self._place_square(sq)
        self._kick_anim()
        for sq in self.squares:
            if sq.habit_name == habit_name:
                sq.update()
        self.update()
        self.core.update()   # the circle's border/chips react at once
        self._save_state()
        if flash:
            FlashLabel('{} ✖ timer discarded'.format(habit_name), self)
        if self.auto_note_toggle is not None:
            # a mapped habit must not be instantly auto-restarted by
            # the still-focused window — same rule as a manual stop
            self.auto_note_toggle(habit_name, False)

    def stop_all_timers(self):
        """
        Center-circle left-click with timers running: stop (and queue to
        the phone) every active timer — exactly as if each square had
        been clicked in turn.
        """
        self._hide_tooltip()
        for name in list(self.timers):
            self.stop_timer(name)
            if self.auto_note_toggle is not None:
                # a mapped habit must not be instantly auto-restarted by
                # the still-focused window — same rule as manual stops
                self.auto_note_toggle(name, False)

    def cancel_all_timers(self):
        """
        The core circle's ✕ (shown while 2+ timers run): discard every
        active timer — as if each square's ✕ chip had been clicked at once.
        """
        self._hide_tooltip()
        for name in list(self.timers):
            self.cancel_timer(name, flash=False)
        FlashLabel('✖ all timers discarded', self)

    def backdate_all_timers(self, minutes: int = 1):
        """
        The core circle's ← (shown while 2+ timers run): pull every
        running start `minutes` further back — as if each square's ←
        chip had been clicked at once.
        """
        self._hide_tooltip()
        for name in list(self.timers):
            self.backdate_timer(name, minutes)

    # ── auto-stop countdown (visible debounce) ──────────────────────────

    def request_auto_stop(self, habit_name: str, countdown_s: int = 30,
                          deduct_s: int = 35):
        """
        Auto-detect says activity stopped (window lost focus or the user
        went idle). Don't stop outright — run the VISIBLE countdown on
        the square: activity in the mapped window again before it
        reaches zero continues this same session; at zero the session
        is finalized retroactively with `deduct_s` seconds (the idle
        gap + the countdown itself) subtracted from its end.
        """
        if habit_name not in self.timers:
            return
        now = datetime.now()
        self.pending_auto_stops[habit_name] = {
            'stopped_at': now,
            'deadline': now + timedelta(seconds=max(1, int(countdown_s))),
            'deduct': max(0, int(deduct_s)),
        }
        self._arm_grace(habit_name, countdown_s)
        self._update_countdown_displays()
        self._save_state()

    def cancel_pending_stop(self, habit_name: str):
        """Activity resumed → the countdown dies, the session keeps running."""
        self._cancel_pending_stop(habit_name)
        self._save_state()

    def finalize_pending_stops(self):
        """Flush every pending countdown stop now (retroactively) — shutdown."""
        for habit_name in list(self.pending_auto_stops):
            self._finalize_auto_stop(habit_name)

    def _arm_grace(self, habit_name: str, seconds: float):
        timer = self._grace_timers.get(habit_name)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(
                lambda h=habit_name: self._finalize_auto_stop(h))
            self._grace_timers[habit_name] = timer
        timer.start(max(0, int(seconds * 1000)))

    def _finalize_auto_stop(self, habit_name: str):
        info = self.pending_auto_stops.pop(habit_name, None)
        self._drop_grace_timer(habit_name)
        self._set_countdown_display(habit_name, None)
        if info is None or habit_name not in self.timers:
            return
        # the idle gap + the countdown itself never happened: finalize
        # retroactively with that time subtracted from the session's end
        self.stop_timer(
            habit_name,
            end=datetime.now() - timedelta(seconds=info['deduct']))

    def _cancel_pending_stop(self, habit_name: str):
        self.pending_auto_stops.pop(habit_name, None)
        self._drop_grace_timer(habit_name)
        self._set_countdown_display(habit_name, None)

    def _set_countdown_display(self, habit_name: str, seconds_left):
        for sq in self.squares:
            if sq.habit_name == habit_name:
                sq.countdown_left = seconds_left
                sq.update()

    def _update_countdown_displays(self):
        """1 Hz: refresh every square's visible countdown number."""
        for habit_name, info in self.pending_auto_stops.items():
            left = max(0, int(math.ceil(
                (info['deadline'] - datetime.now()).total_seconds())))
            for sq in self.squares:
                if sq.habit_name == habit_name and sq.countdown_left != left:
                    sq.countdown_left = left
                    sq.update()

    def _drop_grace_timer(self, habit_name: str):
        timer = self._grace_timers.pop(habit_name, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

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
        # fast follow-up while anything is queued (the phone long-polls,
        # so acks land within ~a second); relax when the queue is empty.
        # start() rather than setInterval(): the new interval's countdown
        # must begin now, not ride the remains of the previous schedule.
        self.ack_timer.start(
            ACK_POLL_FAST_MS if self.pending_by_habit else ACK_POLL_IDLE_MS)

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

    def _square_at_cursor(self):
        """
        The habit square geometrically under the cursor, if any — the
        display-time truth for tooltip targeting. Qt's Enter events
        can't be trusted here: the container's Enter may be delivered
        AFTER a square's (stealing _tip_target), and a square gliding
        under a stationary cursor while the ring spreads never receives
        one at all. Tucked squares hide behind the center circle (which
        is raised above them), so positions inside the core circle
        belong to the center bubble, never to them.
        """
        pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(pos):
            return None
        c = self._center()
        if math.hypot(pos.x() - c.x(), pos.y() - c.y()) <= BUBBLE_D / 2:
            return None          # the center circle (or a tucked square)
        for sq in self.squares:
            if sq.geometry().contains(pos):
                return sq
        return None

    def _show_tooltip(self):
        target = self._square_at_cursor()
        if target is None:
            # no square under the cursor: the container's own message
            # when it (or the mouse-transparent core over it) is hovered
            target = self if self in self._hover_set else self._tip_target
            if target is None or target not in self._hover_set:
                return
        # (a geometrically-resolved square skips the hover_set guard —
        #  the cursor being inside its rect is stronger evidence than
        #  Enter tracking, which is exactly what fails in the races above)
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
        self._update_countdown_displays()
        self.core.update()   # the running-border colour lives on the core now
        self._save_state_throttled()

    def _place_core(self):
        """
        Keeps the center circle glued to the widget's middle (the window
        resizes when the habit count changes).
        """
        c = self._center()
        self.core.move(c.x() - CORE_D // 2, c.y() - CORE_D // 2)

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
            c = self._center()
            if len(self.timers) > 1:
                # the core's all-timers chips (painted on the circle,
                # hit-tested here — the core itself is mouse-transparent)
                xr, br = self.core.badge_rects()
                core_pos = self.core.pos()
                if xr is not None and xr.translated(core_pos).contains(e.pos()):
                    self.cancel_all_timers()   # ✕ on every timer at once
                    return
                if br is not None and br.translated(core_pos).contains(e.pos()):
                    self.backdate_all_timers()  # ← on every timer at once
                    return
            if (self.timers and math.hypot(e.pos().x() - c.x(),
                                           e.pos().y() - c.y())
                    <= BUBBLE_D / 2):
                # left-click on the center circle with timers running:
                # stop (and queue) every active timer in one go
                self.stop_all_timers()
                return
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
                'pending_stops': {
                    h: {'stopped_at': i['stopped_at'].isoformat(
                            timespec='seconds'),
                        'deadline': i['deadline'].isoformat(
                            timespec='seconds'),
                        'deduct': i['deduct']}
                    for h, i in self.pending_auto_stops.items()},
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
            for h, raw in (data.get('pending_stops') or {}).items():
                if h not in self.timers:
                    continue
                if isinstance(raw, str):   # old grace-era format
                    raw = {'stopped_at': raw}
                if not isinstance(raw, dict):
                    continue
                try:
                    stopped_at = datetime.fromisoformat(raw['stopped_at'])
                except (KeyError, ValueError):
                    continue
                try:
                    deadline = datetime.fromisoformat(raw['deadline'])
                except (KeyError, ValueError):
                    deadline = stopped_at + timedelta(seconds=30)
                deduct = raw.get('deduct')
                self.pending_auto_stops[h] = {
                    'stopped_at': stopped_at,
                    'deadline': deadline,
                    'deduct': deduct if isinstance(deduct, int)
                    and deduct >= 0 else 35,
                }
                remaining_s = (deadline - datetime.now()).total_seconds()
                # expired while we were down → 0 s: finalize as soon as
                # the event loop runs, never inline (init is still building
                # and e.g. ack_timer doesn't exist yet)
                self._arm_grace(h, remaining_s)
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
    container painted the circle itself. While 2+ timers run it also
    carries ✕ / ← chips on its rim — the same actions as the
    squares' chips, applied to ALL running timers at once (the
    container hit-tests them; it sees the clicks).
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(CORE_D, CORE_D)   # circle + chip margin
        pm = QPixmap(TAIL_ICON)
        if not pm.isNull():
            # fill the circle: the icon's edge reaches the circle's inner
            # edge (the source image is square, so it spans the diameter)
            self.tail_pm = pm.scaled(BUBBLE_D - 4, BUBBLE_D - 4,
                                     Qt.KeepAspectRatio,
                                     Qt.SmoothTransformation)
        else:
            self.tail_pm = QPixmap()

    def badge_rects(self):
        """
        The ✕ (upper-right rim) and ← (lower-left rim) chip rects in
        core coordinates — or (None, None) unless 2+ timers run.
        """
        if len(self.window().timers) < 2:
            return None, None
        k = int((BUBBLE_D / 2 - 4) * 0.7071)   # chips sit on the rim
        c = CORE_D // 2
        half = CORE_BADGE_D // 2
        return (QRect(c + k - half, c - k - half, CORE_BADGE_D, CORE_BADGE_D),
                QRect(c - k - half, c + k - half, CORE_BADGE_D, CORE_BADGE_D))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPoint(CORE_D // 2, CORE_D // 2)
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
        xr, br = self.badge_rects()
        if xr is not None:
            draw_x_badge(p, xr)
            draw_back_badge(p, br)
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


class StopEditDialog(QDialog):
    """
    "Stop and edit" popup: corrects a session's start/end times before
    the stop is finalized and queued to the bridge. OK stops the timer
    with the edited times; Cancel leaves the timer running untouched.
    """

    def __init__(self, habit_name: str, start: datetime, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Stop timer — {}'.format(habit_name))
        self.setModal(True)
        layout = QFormLayout(self)
        self.start_edit = QDateTimeEdit(QDateTime(start), self)
        self.end_edit = QDateTimeEdit(QDateTime(datetime.now()), self)
        for editor in (self.start_edit, self.end_edit):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat('yyyy-MM-dd HH:mm')
        # a session can never end before it began — bump the end
        # along whenever the start moves past it
        self.end_edit.setMinimumDateTime(self.start_edit.dateTime())
        self.start_edit.dateTimeChanged.connect(
            self.end_edit.setMinimumDateTime)
        layout.addRow('Started', self.start_edit)
        layout.addRow('Ended', self.end_edit)
        hint = QLabel('OK stops the timer and records the corrected '
                      'times — Cancel keeps it running.')
        hint.setWordWrap(True)
        layout.addRow(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok |
                                   QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def start_time(self) -> datetime:
        return self.start_edit.dateTime().toPyDateTime()

    def end_time(self) -> datetime:
        return self.end_edit.dateTime().toPyDateTime()


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

        # window-activity auto start/stop for mapped habits
        self.auto = AutoDetectController(
            # a timer inside its countdown counts as NOT running, so
            # the controller re-fires on_start when the window regains
            # focus — which cancels the pending stop and continues the
            # same session instead of letting the countdown expire under it
            is_running=lambda h: (h in self.bubble.timers
                                  and h not in self.bubble.pending_auto_stops),
            on_start=self._auto_started,
            on_stop=self._auto_stopped,
            on_info=lambda msg: FlashLabel(msg, self.bubble),
            habits_provider=lambda: {sq.habit_name
                                     for sq in self.bubble.squares},
        )
        self.bubble.auto_note_toggle = self.auto.note_manual_toggle
        self.auto.start()

    def _auto_started(self, habit: str):
        # activity resumed before the countdown ran out → cancel the
        # pending stop; the timer never actually stopped, so this is
        # the SAME session
        self.bubble.cancel_pending_stop(habit)
        if self.bubble.start_timer(habit):
            cls = self.auto.mapping_for(habit)
            FlashLabel('{} ▶ auto ({})'.format(habit, cls or 'window'),
                       self.bubble)

    def _auto_stopped(self, habit: str):
        # visible countdown on the square; at zero the session is
        # finalized retroactively with idle + countdown seconds
        # subtracted from its end (the gap never happened)
        countdown = self.auto.countdown_seconds()
        self.bubble.request_auto_stop(
            habit, countdown_s=countdown,
            deduct_s=self.auto.idle_seconds() + countdown)

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if not self.bubble.isVisible():
                self.bubble.show()
            self.bubble.recall_to_tray()

    def toggle_bubble(self):
        self.bubble.setVisible(not self.bubble.isVisible())

    def open_bubble_menu(self, global_pos):
        menu = QMenu()
        act = menu.addAction('Recall to tray',
                             lambda: self.bubble.recall_to_tray())
        act.setIcon(menu_icon('home5.png', 'go-home'))
        act = menu.addAction('Hide bubble', self.toggle_bubble)
        act.setIcon(menu_icon('last_arrow_down.png', 'arrow-down'))
        menu.addSeparator()
        act = menu.addAction('Settings…', self.open_settings)
        act.setIcon(menu_icon('gears1_sc44.png', 'preferences-system',
                              'configure'))
        act = menu.addAction('Quit', self.quit)
        act.setIcon(menu_icon('power_button4.png', 'application-exit'))
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
        habit_icon = get_habit_icon_path(sq.habit_name)
        head.setIcon(QIcon(habit_icon) if habit_icon
                     else menu_icon('clock1.png', 'chronometer'))
        head.setEnabled(False)
        menu.addSeparator()
        act = menu.addAction('Started 1 min earlier' if running
                             else 'No timer running')
        act.setIcon(menu_icon('a_media23_arrows_seek_back.png',
                              'media-seek-backward', 'edit-undo'))
        act.setEnabled(running)

        def backdate_one_more():
            if bubble.backdate_timer(sq.habit_name, 1):
                start = bubble.timers.get(sq.habit_name)
                act.setText('1 more min earlier (started {})'.format(
                    start.strftime('%H:%M') if start else '?'))

        act.setProperty('keep_open', True)
        act.triggered.connect(backdate_one_more)

        # stop now, but with corrected times — fixes a timer that
        # started (or should end) at the wrong moment
        act = menu.addAction('Stop and edit times…')
        act.setIcon(menu_icon('pencil1.png', 'document-edit'))
        act.setEnabled(running)
        act.triggered.connect(
            lambda: self.stop_and_edit(sq.habit_name))

        # throw the running session away entirely — nothing is
        # queued or synced, the timer is simply forgotten
        act = menu.addAction('Cancel timer (discard)')
        act.setIcon(menu_icon('trashcan3.png', 'edit-delete',
                              'edit-clear'))
        act.setEnabled(running)
        act.triggered.connect(
            lambda: bubble.cancel_timer(sq.habit_name))

        # window auto-detect: pair this habit with an open window type
        menu.addSeparator()
        mapping = self.auto.mapping_for(sq.habit_name)
        if mapping:
            cur = menu.addAction('Auto-detect: {}'.format(mapping))
            cur.setIcon(menu_icon('binocular.png', 'crosshairs'))
            cur.setEnabled(False)
            off = menu.addAction('Stop auto-detecting')
            off.setIcon(menu_icon('x_solid.png', 'window-close'))
            off.triggered.connect(
                lambda: self._clear_auto_mapping(sq.habit_name))
        else:
            pick = menu.addAction('Auto-detect window…')
            pick.setIcon(menu_icon('magnifying_glass_ps.png', 'edit-find'))
            pick.triggered.connect(lambda: open_window_picker(
                self.auto, sq.habit_name,
                lambda cls: self._set_auto_mapping(sq.habit_name, cls)))

        bubble._pin_spread = True   # keep the ring spread under the menu
        menu.exec_(global_pos)
        bubble._pin_spread = False
        bubble._check_proximity()

    def stop_and_edit(self, habit_name: str):
        """
        Right-click "Stop and edit times": opens the correction popup
        pre-filled with the running session's times. OK finalizes the
        stop with whatever the user corrected; Cancel changes nothing
        and the timer keeps running.
        """
        start = self.bubble.timers.get(habit_name)
        if start is None:
            return
        dialog = StopEditDialog(habit_name, start, self.bubble)
        if dialog.exec_() == QDialog.Accepted:
            self.bubble.stop_timer(habit_name, start=dialog.start_time(),
                                   end=dialog.end_time())

    def _set_auto_mapping(self, habit: str, window_class: str):
        self.auto.set_mapping(habit, window_class)
        FlashLabel('{} ↔ {} auto-detect ON'.format(habit, window_class),
                   self.bubble)

    def _clear_auto_mapping(self, habit: str):
        self.auto.clear_mapping(habit)
        FlashLabel('{} auto-detect OFF'.format(habit), self.bubble)

    def open_settings(self):
        """Bubble menu "Settings…": habit picker + auto-detect timings."""
        dialog = PcSettingsDialog(self.bubble, self.auto, self.bubble)
        dialog.exec_()
        self.bubble._poll_config()

    def show_flash(self, habit: str, minutes: int, queued: bool):
        if minutes > 0:
            text = '{} {}m → phone {}'.format(
                habit, minutes, '✓' if queued else '(write FAILED)')
        else:
            text = '{} +1 → phone {}'.format(
                habit, '✓' if queued else '(write FAILED)')
        FlashLabel(text, self.bubble)

    def quit(self):
        self.auto.stop()
        # flush pending countdown stops now (retroactively) so quitting
        # the widget can't silently swallow a session mid-countdown
        self.bubble.finalize_pending_stops()
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
