#!/usr/bin/env python3
"""
pc_settings_dialog — settings screen for the PC bubble widget.

Opened from the bubble's right-click menu ("Settings…"):

 * Habit picker — every habit in the Android habit app (the phone
   pushes the full catalog alongside the widget config as
   "all_habits"). Checking a habit queues a toggle request on the
   Tail Bridge; the phone's event poller applies it to its "PC
   widget" toggles — exactly as if the switch had been flipped in
   the app — and pushes the updated widget config back, which the
   bubble picks up on its 20 s config poll.
 * Auto-detect timings — the idle threshold after which a mapped
   window's countdown starts, and that countdown's duration (the
   two values deducted from a session whose countdown runs out).

The dialog keeps polling the config while open (paused briefly after
one of our own toggle requests, so the checklist doesn't visually
revert before the phone has applied it), so toggles made on the phone
show up live.
"""

import html
import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout,
)

import pc_widget_sync


class PcSettingsDialog(QDialog):
    """Bubble settings: PC-widget habit picker + auto-detect timings."""

    def __init__(self, bubble, auto_controller, parent=None):
        super().__init__(parent)
        self.bubble = bubble
        self.auto = auto_controller
        self.setWindowTitle('Tail PC Widget — Settings')
        self.setModal(True)
        self.setMinimumWidth(380)

        self._loading = False      # suppress itemChanged while rebuilding
        self._cfg_hold = 0.0       # monotonic time until which reload is paused

        root = QVBoxLayout(self)

        root.addWidget(QLabel('Habits on the PC widget'))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('Search habits…')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        root.addWidget(self.search_edit)
        hint = QLabel(
            'Checked habits appear as squares on the bubble. Toggling '
            'flips the same "PC widget" switch in the Android app '
            '(synced through the bridge; the phone picks it up within '
            'a few seconds).')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #9a9aa2;')
        root.addWidget(hint)
        self.habit_list = QListWidget()
        self.habit_list.setToolTip('Checked = shown as a square on the PC widget')
        self.habit_list.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.habit_list, 1)

        # the selected habits as little highlight tags — the at-a-glance
        # summary of what's on the widget (checked ones stay in the list
        # above too, so searching/unchecking works in one place)
        root.addWidget(QLabel('Selected for the PC widget:'))
        self.chips_label = QLabel('')
        self.chips_label.setWordWrap(True)
        self.chips_label.setTextFormat(Qt.RichText)
        root.addWidget(self.chips_label)

        self.sync_label = QLabel('')
        self.sync_label.setStyleSheet('color: #9a9aa2;')
        self.sync_label.setWordWrap(True)
        root.addWidget(self.sync_label)

        refresh = QPushButton('Refresh from phone')
        refresh.clicked.connect(self.reload_habits)
        root.addWidget(refresh)

        root.addSpacing(8)
        form = QFormLayout()
        self.idle_spin = QSpinBox()
        self.idle_spin.setRange(1, 300)
        self.idle_spin.setSuffix(' s')
        self.idle_spin.setValue(auto_controller.idle_seconds())
        self.idle_spin.setToolTip(
            'No input / interaction for this long in a mapped window\n'
            '→ the countdown starts on that habit\'s square')
        self.countdown_spin = QSpinBox()
        self.countdown_spin.setRange(5, 600)
        self.countdown_spin.setSuffix(' s')
        self.countdown_spin.setValue(auto_controller.countdown_seconds())
        self.countdown_spin.setToolTip(
            'Length of the countdown before the timer auto-stops.\n'
            'idle + countdown are subtracted from the session when it fires.')
        form.addRow('Idle before countdown', self.idle_spin)
        form.addRow('Countdown duration', self.countdown_spin)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.reload_habits()

        # live refresh: the phone pushes a new config a few seconds after
        # applying one of our toggle requests (and may toggle on its own)
        self._cfg_timer = QTimer(self)
        self._cfg_timer.setInterval(3_000)
        self._cfg_timer.timeout.connect(self.reload_habits)
        self._cfg_timer.start()

    # ── habit picker ────────────────────────────────────────────────────

    def reload_habits(self):
        """(Re)builds the checklist from the phone-pushed config."""
        if time.monotonic() < self._cfg_hold:
            return                      # our own toggle is still in flight
        cfg = pc_widget_sync.load_config_full()
        if cfg is None:
            self.sync_label.setText('bridge unreachable — showing last known state')
            if self.habit_list.count():
                return
            habits, all_names = [], []
        else:
            habits = [h.get('name') for h in (cfg.get('habits') or [])
                      if isinstance(h, dict) and isinstance(h.get('name'), str)]
            all_names = [n for n in (cfg.get('all_habits') or [])
                         if isinstance(n, str) and n]
            if not all_names:
                # older phone app: catalog not pushed yet — offer what we know
                all_names = list(habits)
                self.sync_label.setText(
                    'phone app update needed for the full habit list')
            else:
                self.sync_label.setText('')
        enabled = set(habits)
        names = sorted(dict.fromkeys(all_names + [h for h in habits
                                                  if h not in all_names]),
                       key=str.casefold)          # alphabetical
        self._loading = True
        self.habit_list.clear()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name in enabled else Qt.Unchecked)
            self.habit_list.addItem(item)
        self._loading = False
        self._apply_filter(self.search_edit.text())
        self._render_chips()

    def _apply_filter(self, text):
        """Search box: hides list rows that don't match (check states stay)."""
        needle = (text or '').strip().casefold()
        for i in range(self.habit_list.count()):
            item = self.habit_list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().casefold())

    def _render_chips(self):
        """The selected habits as little highlight tags below the list."""
        selected = sorted(
            (self.habit_list.item(i).text()
             for i in range(self.habit_list.count())
             if self.habit_list.item(i).checkState() == Qt.Checked),
            key=str.casefold)
        if not selected:
            self.chips_label.setText(
                '<span style="color:#9a9aa2; font-style:italic">'
                'none yet — check habits above</span>')
            return
        self.chips_label.setText(' '.join(
            '<span style="background-color:#2f4a1e; color:#a8e6a0;">'
            '&nbsp;{}&nbsp;</span>'.format(html.escape(n))
            for n in selected))

    def _on_item_changed(self, item):
        if self._loading:
            return
        self._render_chips()
        name = item.text()
        enabled = item.checkState() == Qt.Checked
        # hold the checklist steady until the phone has round-tripped
        # the request (otherwise the 3 s reload would revert the box
        # before the new config lands)
        self._cfg_hold = time.monotonic() + 20
        event_id = pc_widget_sync.append_toggle_event(name, enabled)
        if event_id:
            self.sync_label.setText(
                "'{}' {} — the phone will sync and the square {} shortly".format(
                    name, 'ON' if enabled else 'OFF',
                    'appears' if enabled else 'disappears'))
        else:
            self.sync_label.setText(
                'FAILED to queue the toggle for \'{}\' (bridge reachable?)'.format(
                    name))

    # ── closing ─────────────────────────────────────────────────────────

    def hideEvent(self, e):
        self._cfg_timer.stop()
        # persist the timings no matter how the dialog was closed
        self.auto.set_idle_seconds(self.idle_spin.value())
        self.auto.set_countdown_seconds(self.countdown_spin.value())
        self.bubble._poll_config()
        super().hideEvent(e)
