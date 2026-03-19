"""
Edit mode control bar shown below the grid when in edit mode.
Matches the Android EditModeControlBar composable in HabitGridScreen.kt.

Three states:
 1. Nothing selected → prompt + Add Screen / Del Screen buttons
 2. Placeholder selected → "Add Habit" button
 3. Habit selected → MOVE button + screen-jump buttons + SETTINGS section
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSpinBox, QScrollArea, QFrame
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Optional, List, Set, Dict

from habit_models import HabitScreen


class EditModeControlBar(QWidget):
    """
    Control bar shown below the grid in edit mode.
    Emits signals for all actions.
    """
    # Signals
    start_move = pyqtSignal()
    add_habit = pyqtSignal()
    move_to_screen = pyqtSignal(int)
    add_screen = pyqtSignal()
    delete_screen = pyqtSignal()
    toggle_max_one = pyqtSignal(str)
    toggle_custom_input = pyqtSignal(str)
    toggle_text_input = pyqtSignal(str)
    toggle_text_input_options = pyqtSignal(str)
    pick_text_input_file = pyqtSignal(str)
    toggle_dated_entry = pyqtSignal(str)
    pick_dated_entry_file = pyqtSignal(str)
    delete_habit = pyqtSignal(str)
    change_icon = pyqtSignal(str)
    set_count = pyqtSignal(str, int)
    set_divider = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1A1000;")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 6, 8, 6)
        self._layout.setSpacing(6)

        # State
        self._selected_index = -1
        self._selected_habit_name: Optional[str] = None
        self._selected_raw_count = 0
        self._is_placeholder = False
        self._move_pending = False
        self._habit_screens: List[HabitScreen] = []
        self._active_screen_index = 0
        self._max_one_habits: Set[str] = set()
        self._custom_input_habits: Set[str] = set()
        self._text_input_habits: Set[str] = set()
        self._text_input_options_habits: Set[str] = set()
        self._text_input_file_uris: Dict[str, str] = {}
        self._dated_entry_habits: Set[str] = set()
        self._dated_entry_file_uris: Dict[str, str] = {}
        self._habit_dividers: Dict[str, int] = {}

    def update_state(self, selected_index: int, selected_habit_name: Optional[str],
                     selected_raw_count: int, is_placeholder: bool, move_pending: bool,
                     habit_screens: List[HabitScreen], active_screen_index: int,
                     max_one_habits: Set[str], custom_input_habits: Set[str],
                     text_input_habits: Set[str], text_input_options_habits: Set[str],
                     text_input_file_uris: Dict[str, str],
                     dated_entry_habits: Set[str], dated_entry_file_uris: Dict[str, str],
                     habit_dividers: Dict[str, int]):
        """Update all state and rebuild the UI."""
        self._selected_index = selected_index
        self._selected_habit_name = selected_habit_name
        self._selected_raw_count = selected_raw_count
        self._is_placeholder = is_placeholder
        self._move_pending = move_pending
        self._habit_screens = habit_screens
        self._active_screen_index = active_screen_index
        self._max_one_habits = max_one_habits
        self._custom_input_habits = custom_input_habits
        self._text_input_habits = text_input_habits
        self._text_input_options_habits = text_input_options_habits
        self._text_input_file_uris = text_input_file_uris
        self._dated_entry_habits = dated_entry_habits
        self._dated_entry_file_uris = dated_entry_file_uris
        self._habit_dividers = habit_dividers
        self._rebuild()

    def _clear_layout(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def _rebuild(self):
        self._clear_layout()
        has_selection = self._selected_index >= 0

        if self._move_pending:
            self.setStyleSheet("background-color: #001A1A;")
            self._build_move_pending()
        else:
            self.setStyleSheet("background-color: #1A1000;")
            if not has_selection:
                self._build_no_selection()
            elif self._is_placeholder:
                self._build_placeholder_selected()
            else:
                self._build_habit_selected()

    def _build_move_pending(self):
        row = QHBoxLayout()
        label = QLabel(f'↕ Tap any cell to move "{self._selected_habit_name}" there')
        label.setStyleSheet("color: #44FFFF; font-size: 11px; font-weight: 600;")
        row.addWidget(label, 1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #3A3A00; color: #FFFF44; font-size: 11px; padding: 4px 10px; border-radius: 4px;")
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.start_move.emit)
        row.addWidget(cancel_btn)
        self._layout.addLayout(row)

    def _build_no_selection(self):
        row = QHBoxLayout()
        label = QLabel("✏ Tap a habit or placeholder to select")
        label.setStyleSheet("color: #888888; font-size: 11px;")
        row.addWidget(label, 1)

        if len(self._habit_screens) > 1:
            del_btn = QPushButton("Del Screen")
            del_btn.setStyleSheet("background-color: #3A0000; color: #FF8888; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
            del_btn.setFixedHeight(32)
            del_btn.clicked.connect(self.delete_screen.emit)
            row.addWidget(del_btn)

        add_btn = QPushButton("+ Add Screen")
        add_btn.setStyleSheet("background-color: #1A3A1A; color: #88FF88; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self.add_screen.emit)
        row.addWidget(add_btn)
        self._layout.addLayout(row)

    def _build_placeholder_selected(self):
        row = QHBoxLayout()
        label = QLabel(f"Placeholder [{self._selected_index}]")
        label.setStyleSheet("color: #888888; font-size: 11px; font-weight: 600;")
        row.addWidget(label, 1)

        add_btn = QPushButton("+ Add Habit")
        add_btn.setStyleSheet("background-color: #1A3A1A; color: #88FF88; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self.add_habit.emit)
        row.addWidget(add_btn)
        self._layout.addLayout(row)

    def _build_habit_selected(self):
        name = self._selected_habit_name
        if not name:
            return

        # Header row: name + count adjuster
        header_row = QHBoxLayout()
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #FFAA00; font-size: 11px; font-weight: 600;")
        header_row.addWidget(name_label, 1)

        # Count adjuster: [−] rawCount [+]
        today_label = QLabel("today:")
        today_label.setStyleSheet("color: #888888; font-size: 10px;")
        header_row.addWidget(today_label)

        minus_btn = QPushButton("−")
        minus_btn.setFixedSize(28, 28)
        minus_btn.setStyleSheet("background-color: #3A1A00; color: #FFAA00; font-size: 14px; border-radius: 4px;")
        minus_btn.setEnabled(self._selected_raw_count > 0)
        minus_btn.clicked.connect(lambda: self.set_count.emit(name, self._selected_raw_count - 1))
        header_row.addWidget(minus_btn)

        count_label = QLabel(str(self._selected_raw_count))
        count_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        count_label.setFixedWidth(28)
        count_label.setAlignment(Qt.AlignCenter)
        header_row.addWidget(count_label)

        plus_btn = QPushButton("+")
        plus_btn.setFixedSize(28, 28)
        plus_btn.setStyleSheet("background-color: #1A3A00; color: #88FF88; font-size: 14px; border-radius: 4px;")
        plus_btn.clicked.connect(lambda: self.set_count.emit(name, self._selected_raw_count + 1))
        header_row.addWidget(plus_btn)
        self._layout.addLayout(header_row)

        # Move + screen jump buttons
        action_row = QHBoxLayout()
        move_btn = QPushButton("↕ Move")
        move_btn.setStyleSheet("background-color: #004A4A; color: #44FFFF; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        move_btn.setFixedHeight(32)
        move_btn.clicked.connect(self.start_move.emit)
        action_row.addWidget(move_btn)

        # Screen jump buttons (other screens)
        if len(self._habit_screens) > 1:
            for idx, screen in enumerate(self._habit_screens):
                if idx != self._active_screen_index:
                    screen_btn = QPushButton(screen.name)
                    screen_btn.setStyleSheet("background-color: #003A5A; color: #88CCFF; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
                    screen_btn.setFixedHeight(32)
                    screen_btn.clicked.connect(lambda checked, i=idx: self.move_to_screen.emit(i))
                    action_row.addWidget(screen_btn)

        action_row.addStretch()
        self._layout.addLayout(action_row)

        # Delete + Change Icon
        actions_row2 = QHBoxLayout()
        del_btn = QPushButton("🗑 Delete")
        del_btn.setStyleSheet("background-color: #3A0000; color: #FF8888; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        del_btn.setFixedHeight(32)
        del_btn.clicked.connect(lambda: self.delete_habit.emit(name))
        actions_row2.addWidget(del_btn)

        icon_btn = QPushButton("🎨 Icon")
        icon_btn.setStyleSheet("background-color: #003A3A; color: #88FFFF; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        icon_btn.setFixedHeight(32)
        icon_btn.clicked.connect(lambda: self.change_icon.emit(name))
        actions_row2.addWidget(icon_btn)
        actions_row2.addStretch()
        self._layout.addLayout(actions_row2)

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #333300;")
        self._layout.addWidget(line)

        # SETTINGS header
        settings_label = QLabel("SETTINGS")
        settings_label.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self._layout.addWidget(settings_label)

        # Divider toggle
        current_divisor = self._habit_dividers.get(name, 1)
        is_divider = current_divisor > 1
        self._add_toggle_row(
            "Divider",
            f"Points = input ÷ {current_divisor} (rounded, min 1)" if is_divider else "Points = raw input",
            is_divider,
            lambda checked: self.set_divider.emit(name, 2 if checked else 1)
        )

        # 1 max toggle
        is_max_one = name in self._max_one_habits
        self._add_toggle_row(
            "1 max",
            "Capped at 1 per day (binary)" if is_max_one else "No daily cap",
            is_max_one,
            lambda checked: self.toggle_max_one.emit(name)
        )

        # Custom input toggle
        is_custom = name in self._custom_input_habits
        self._add_toggle_row(
            "Custom input",
            "Shows number picker on tap" if is_custom else "Simple +1 on tap",
            is_custom,
            lambda checked: self.toggle_custom_input.emit(name)
        )

        # Text input toggle
        is_text = name in self._text_input_habits
        self._add_toggle_row(
            "Text input",
            "Shows text entry on tap" if is_text else "No text entry",
            is_text,
            lambda checked: self.toggle_text_input.emit(name)
        )

        if is_text:
            # Options sub-toggle
            is_options = name in self._text_input_options_habits
            self._add_toggle_row(
                "  Options",
                "Shows past entries as choices" if is_options else "Free-text only",
                is_options,
                lambda checked: self.toggle_text_input_options.emit(name),
                indent=True
            )

            # File picker
            has_file = name in self._text_input_file_uris
            file_row = QHBoxLayout()
            file_label = QLabel("  Text log file")
            file_label.setStyleSheet("color: #AAAAAA; font-size: 12px;")
            file_row.addWidget(file_label)
            status = QLabel("✓ File selected" if has_file else "⚠ No file selected")
            status.setStyleSheet(f"color: {'#88FF88' if has_file else '#FF8844'}; font-size: 10px;")
            file_row.addWidget(status, 1)
            pick_btn = QPushButton("Change" if has_file else "Select")
            pick_btn.setStyleSheet("background-color: #003A5A; color: #88CCFF; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
            pick_btn.setFixedHeight(32)
            pick_btn.clicked.connect(lambda: self.pick_text_input_file.emit(name))
            file_row.addWidget(pick_btn)
            self._layout.addLayout(file_row)

        # Dated Entry toggle
        is_dated = name in self._dated_entry_habits
        self._add_toggle_row(
            "Dated Entry",
            "Auto-counts from linked file" if is_dated else "Manual count only",
            is_dated,
            lambda checked: self.toggle_dated_entry.emit(name)
        )

        if is_dated:
            has_dated_file = name in self._dated_entry_file_uris
            dated_row = QHBoxLayout()
            dated_label = QLabel("  Source file")
            dated_label.setStyleSheet("color: #AAAAAA; font-size: 12px;")
            dated_row.addWidget(dated_label)
            dated_status = QLabel("✓ File linked" if has_dated_file else "⚠ No file linked")
            dated_status.setStyleSheet(f"color: {'#FFCC44' if has_dated_file else '#FF8844'}; font-size: 10px;")
            dated_row.addWidget(dated_status, 1)
            dated_pick_btn = QPushButton("Change" if has_dated_file else "Link File")
            dated_pick_btn.setStyleSheet("background-color: #3A2A00; color: #FFCC44; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
            dated_pick_btn.setFixedHeight(32)
            dated_pick_btn.clicked.connect(lambda: self.pick_dated_entry_file.emit(name))
            dated_row.addWidget(dated_pick_btn)
            self._layout.addLayout(dated_row)

    def _add_toggle_row(self, label: str, description: str, checked: bool,
                        on_toggle, indent: bool = False):
        row = QHBoxLayout()
        text_col = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {'#AAAAAA' if indent else '#CCCCCC'}; font-size: 12px;")
        text_col.addWidget(lbl)
        desc = QLabel(description)
        desc.setStyleSheet(f"color: {'#666666' if indent else '#888888'}; font-size: 10px;")
        text_col.addWidget(desc)
        row.addLayout(text_col, 1)

        toggle = QCheckBox()
        toggle.setChecked(checked)
        toggle.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:checked {
                background-color: #88FF88;
                border: 2px solid #1A4A1A;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #333333;
                border: 2px solid #555555;
                border-radius: 4px;
            }
        """)
        toggle.toggled.connect(on_toggle)
        row.addWidget(toggle)
        self._layout.addLayout(row)
