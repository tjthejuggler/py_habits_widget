"""
All dialog windows matching the Android app's dialogs:
- IncrementDialog (custom amount input with quick-add buttons)
- TextInputDialog (text entry with optional past-entries list)
- AddScreenDialog / RenameScreenDialog / DeleteHabitConfirmDialog
- AddHabitDialog
- IconPickerDialog
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGridLayout, QScrollArea, QWidget, QListWidget,
    QListWidgetItem, QSizePolicy
)
from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon, QPalette, QIntValidator
from PyQt5.QtCore import Qt, QSize
from typing import List, Optional, Callable
import os

from habit_colors import ALL_ICON_NAMES, ICON_DIR, ICONS_BASE_DIR


# ── Shared dark dialog stylesheet ──────────────────────────────────────────────

DARK_DIALOG_STYLE = """
QDialog {
    background-color: #1E1E1E;
}
QLabel {
    color: #CCCCCC;
}
QLineEdit {
    background-color: #2A2A2A;
    color: white;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #FFAA00;
}
QPushButton {
    background-color: #3A3A3A;
    color: white;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #4A4A4A;
}
QPushButton:pressed {
    background-color: #2A2A2A;
}
QListWidget {
    background-color: #111111;
    color: #CCCCCC;
    border: 1px solid #333333;
    border-radius: 6px;
    font-size: 13px;
}
QListWidget::item {
    padding: 7px 12px;
}
QListWidget::item:hover {
    background-color: #2A2A2A;
}
QListWidget::item:selected {
    background-color: #3A3A00;
    color: #FFAA00;
}
"""


# ── IncrementDialog ────────────────────────────────────────────────────────────

QUICK_AMOUNTS = [1, 5, 10, 30, 50]


class IncrementDialog(QDialog):
    """
    Dialog for entering a custom increment amount for widget-style habits.
    Shows quick-add buttons (+1, +5, +10, +30, +50) and a text field.
    Matches Android IncrementDialog.kt.
    """
    def __init__(self, habit_name: str, current_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(habit_name)
        self.setStyleSheet(DARK_DIALOG_STYLE)
        self.setMinimumWidth(300)
        self.result_amount = 0

        layout = QVBoxLayout(self)

        # Title
        title = QLabel(habit_name)
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #FFD700;")
        layout.addWidget(title)

        # Current count
        count_label = QLabel(f"Today: {current_count}")
        count_label.setStyleSheet("color: #CCCCCC; font-size: 13px;")
        layout.addWidget(count_label)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Amount")
        self.input_field.setValidator(QIntValidator(1, 99999))
        layout.addWidget(self.input_field)

        # Quick add label
        quick_label = QLabel("Quick add:")
        quick_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(quick_label)

        # Quick add buttons
        quick_row = QHBoxLayout()
        for amount in QUICK_AMOUNTS:
            btn = QPushButton(f"+{amount}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2A2A2A;
                    color: #88CCFF;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #3A3A3A; }
            """)
            btn.clicked.connect(lambda checked, a=amount: self.input_field.setText(str(a)))
            quick_row.addWidget(btn)
        layout.addLayout(quick_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("color: #888888;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet("background-color: #5A3A00; color: #FFAA00;")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _on_ok(self):
        text = self.input_field.text().strip()
        if text and text.isdigit() and int(text) > 0:
            self.result_amount = int(text)
            self.accept()

    @staticmethod
    def get_amount(habit_name: str, current_count: int, parent=None) -> Optional[int]:
        """Show the dialog and return the amount, or None if cancelled."""
        dlg = IncrementDialog(habit_name, current_count, parent)
        if dlg.exec_() == QDialog.Accepted:
            return dlg.result_amount
        return None


# ── TextInputDialog ────────────────────────────────────────────────────────────

class TextInputDialog(QDialog):
    """
    Dialog shown when the user taps a habit that has "text input" enabled.
    Matches Android TextInputDialog.kt.
    """
    def __init__(self, habit_name: str, show_options: bool = False,
                 options: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(habit_name)
        self.setStyleSheet(DARK_DIALOG_STYLE)
        self.setMinimumWidth(350)
        self.result_text = ""

        layout = QVBoxLayout(self)

        # Title
        title = QLabel(habit_name)
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #FFD700;")
        layout.addWidget(title)

        # Text input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Entry")
        layout.addWidget(self.input_field)

        # Past options list
        if show_options and options:
            opts_label = QLabel("Past entries")
            opts_label.setStyleSheet("color: #888888; font-size: 11px; font-weight: bold;")
            layout.addWidget(opts_label)

            self.options_list = QListWidget()
            self.options_list.setMaximumHeight(200)
            for opt in options:
                self.options_list.addItem(opt)
            self.options_list.itemClicked.connect(
                lambda item: self.input_field.setText(item.text())
            )
            layout.addWidget(self.options_list)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("color: #888888;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet("background-color: #5A3A00; color: #FFAA00;")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _on_ok(self):
        text = self.input_field.text().strip()
        if text:
            self.result_text = text
            self.accept()

    @staticmethod
    def get_text(habit_name: str, show_options: bool = False,
                 options: Optional[List[str]] = None, parent=None) -> Optional[str]:
        dlg = TextInputDialog(habit_name, show_options, options, parent)
        if dlg.exec_() == QDialog.Accepted:
            return dlg.result_text
        return None


# ── AddScreenDialog ────────────────────────────────────────────────────────────

class AddScreenDialog(QDialog):
    """Dialog to add a new screen. Matches Android AddScreenDialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Screen")
        self.setStyleSheet(DARK_DIALOG_STYLE)
        self.setMinimumWidth(300)
        self.result_name = ""

        layout = QVBoxLayout(self)
        title = QLabel("New Screen")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #FFAA00;")
        layout.addWidget(title)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Screen name")
        layout.addWidget(self.name_field)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("color: #888888;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        add_btn = QPushButton("Add")
        add_btn.setStyleSheet("background-color: #5A3A00; color: #FFAA00;")
        add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

    def _on_add(self):
        name = self.name_field.text().strip()
        if name:
            self.result_name = name
            self.accept()

    @staticmethod
    def get_name(parent=None) -> Optional[str]:
        dlg = AddScreenDialog(parent)
        if dlg.exec_() == QDialog.Accepted:
            return dlg.result_name
        return None


# ── RenameScreenDialog ─────────────────────────────────────────────────────────

class RenameScreenDialog(QDialog):
    """Dialog to rename a screen. Matches Android RenameScreenDialog."""
    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename Screen")
        self.setStyleSheet(DARK_DIALOG_STYLE)
        self.setMinimumWidth(300)
        self.result_name = ""

        layout = QVBoxLayout(self)
        title = QLabel("Rename Screen")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #FFAA00;")
        layout.addWidget(title)

        self.name_field = QLineEdit(current_name)
        layout.addWidget(self.name_field)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("color: #888888;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.setStyleSheet("background-color: #5A3A00; color: #FFAA00;")
        rename_btn.clicked.connect(self._on_rename)
        btn_row.addWidget(rename_btn)
        layout.addLayout(btn_row)

    def _on_rename(self):
        name = self.name_field.text().strip()
        if name:
            self.result_name = name
            self.accept()

    @staticmethod
    def get_name(current_name: str, parent=None) -> Optional[str]:
        dlg = RenameScreenDialog(current_name, parent)
        if dlg.exec_() == QDialog.Accepted:
            return dlg.result_name
        return None


# ── AddHabitDialog ─────────────────────────────────────────────────────────────

class AddHabitDialog(QDialog):
    """Dialog to add a new habit. Matches Android AddHabitDialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Habit")
        self.setStyleSheet(DARK_DIALOG_STYLE)
        self.setMinimumWidth(300)
        self.result_name = ""

        layout = QVBoxLayout(self)
        title = QLabel("Add Habit")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #88FF88;")
        layout.addWidget(title)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Habit name")
        self.name_field.setStyleSheet("""
            QLineEdit:focus { border-color: #88FF88; }
        """)
        layout.addWidget(self.name_field)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("color: #888888;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        add_btn = QPushButton("Add")
        add_btn.setStyleSheet("background-color: #1A3A1A; color: #88FF88;")
        add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

    def _on_add(self):
        name = self.name_field.text().strip()
        if name:
            self.result_name = name
            self.accept()

    @staticmethod
    def get_name(parent=None) -> Optional[str]:
        dlg = AddHabitDialog(parent)
        if dlg.exec_() == QDialog.Accepted:
            return dlg.result_name
        return None


# ── DeleteHabitConfirmDialog ───────────────────────────────────────────────────

class DeleteHabitConfirmDialog(QDialog):
    """Confirmation dialog for deleting a habit. Matches Android DeleteHabitConfirmDialog."""
    def __init__(self, habit_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete Habit")
        self.setStyleSheet(DARK_DIALOG_STYLE)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        title = QLabel("Delete Habit")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #FF8888;")
        layout.addWidget(title)

        msg = QLabel(f'Remove "{habit_name}" from the grid?\n\n'
                     f'The habit data in your JSON files will NOT be deleted.')
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #CCCCCC; font-size: 13px;")
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("color: #888888;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("background-color: #3A0000; color: #FF8888;")
        delete_btn.clicked.connect(self.accept)
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def confirm(habit_name: str, parent=None) -> bool:
        dlg = DeleteHabitConfirmDialog(habit_name, parent)
        return dlg.exec_() == QDialog.Accepted


# ── IconPickerDialog ───────────────────────────────────────────────────────────

class IconPickerDialog(QDialog):
    """
    Dialog to pick an icon for a habit. Shows a scrollable grid of all available icons.
    Matches Android IconPickerDialog.
    """
    def __init__(self, habit_name: str, current_icon_name: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Choose Icon — {habit_name}")
        self.setStyleSheet(DARK_DIALOG_STYLE)
        self.setMinimumSize(500, 500)
        self.result_icon_name: Optional[str] = None
        self._accepted = False

        layout = QVBoxLayout(self)

        title = QLabel(f"Choose Icon — {habit_name}")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color: #88FFFF;")
        layout.addWidget(title)

        # "No icon" option
        no_icon_btn = QPushButton("✕  No icon (use default)")
        no_icon_btn.setStyleSheet("""
            QPushButton {
                background-color: %s;
                color: %s;
                text-align: left;
                padding: 6px 8px;
                border-radius: 6px;
            }
        """ % ("#003A3A" if current_icon_name is None else "transparent",
               "#88FFFF" if current_icon_name is None else "#888888"))
        no_icon_btn.clicked.connect(self._select_none)
        layout.addWidget(no_icon_btn)

        # Scrollable grid of icons
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1E1E1E; }")

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(4)

        cols = 8
        for i, icon_name in enumerate(ALL_ICON_NAMES):
            row = i // cols
            col = i % cols
            btn = QPushButton()
            btn.setFixedSize(50, 50)
            is_selected = icon_name == current_icon_name

            # Try to load icon
            icon_path = self._find_icon(icon_name)
            if icon_path:
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(32, 32))

            btn.setStyleSheet("""
                QPushButton {
                    background-color: %s;
                    border: %s;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #3A3A3A; }
            """ % ("#003A3A" if is_selected else "#2A2A2A",
                   "1px solid #88FFFF" if is_selected else "none"))
            btn.setToolTip(icon_name)
            btn.clicked.connect(lambda checked, n=icon_name: self._select_icon(n))
            grid_layout.addWidget(btn, row, col)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

        # Cancel button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("color: #888888;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _find_icon(self, icon_name: str) -> Optional[str]:
        """Find the icon file path."""
        path = os.path.join(ICON_DIR, icon_name + '.png')
        if os.path.exists(path):
            return path
        # Try other directories
        if os.path.isdir(ICONS_BASE_DIR):
            for subdir in os.listdir(ICONS_BASE_DIR):
                alt = os.path.join(ICONS_BASE_DIR, subdir, icon_name + '.png')
                if os.path.exists(alt):
                    return alt
        return None

    def _select_icon(self, icon_name: str):
        self.result_icon_name = icon_name
        self._accepted = True
        self.accept()

    def _select_none(self):
        self.result_icon_name = None
        self._accepted = True
        self.accept()

    @staticmethod
    def pick_icon(habit_name: str, current_icon_name: Optional[str] = None,
                  parent=None) -> Optional[str]:
        """
        Show the dialog and return the selected icon name.
        Returns the icon name string, None for "no icon", or raises if cancelled.
        Use the second return value to distinguish cancel from "no icon".
        """
        dlg = IconPickerDialog(habit_name, current_icon_name, parent)
        if dlg.exec_() == QDialog.Accepted and dlg._accepted:
            return dlg.result_icon_name
        return current_icon_name  # cancelled — keep current
