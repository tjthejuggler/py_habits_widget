"""
py_widget.py — Main application assembly for the Habit Tracker desktop widget.
Matches the Android Tail app's HabitGridScreen.kt layout:

  ┌─────────────────────────────────────────────────────┐
  │  ◀  Today / date  ▶          [📊] [✏] [ℹ] [⚙]     │  ← Top bar
  ├─────────────────────────────────────────────────────┤
  │  [general]  [screen2]  [screen3]                    │  ← Screen tabs
  ├─────────────────────────────────────────────────────┤
  │                                                     │
  │   8-column × 10-row grid of HabitButton cells       │  ← Main grid
  │                                                     │
  ├─────────────────────────────────────────────────────┤
  │  Info panel  /  Edit control bar  (conditional)     │  ← Bottom panel
  └─────────────────────────────────────────────────────┘
"""
import sys
import os
from datetime import date

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
    QFileDialog, QMessageBox
)
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtCore import Qt, QTimer, QSize

from habit_models import Habit, HabitScreen
from habit_view_model import HabitViewModel, TOTAL_GRID_CELLS
from habit_button import HabitButton, PlaceholderCell, CELL_SIZE
from habit_colors import get_habit_icon_name
from info_panel import HabitInfoPanel
from edit_control_bar import EditModeControlBar
from graphs_panel import GraphsPanel
from dialogs import (
    IncrementDialog, TextInputDialog, AddScreenDialog,
    RenameScreenDialog, AddHabitDialog, DeleteHabitConfirmDialog,
    IconPickerDialog
)

GRID_COLUMNS = 8
DISPLAY_DATE_FMT = "%b %d, %Y"


# ── Dark palette ───────────────────────────────────────────────────────────────

def apply_dark_theme(app: QApplication):
    """Apply a dark theme matching the Android app's Material3 dark surface."""
    palette = QPalette()
    surface = QColor(0x12, 0x12, 0x12)
    on_surface = QColor(0xE0, 0xE0, 0xE0)
    palette.setColor(QPalette.Window, surface)
    palette.setColor(QPalette.WindowText, on_surface)
    palette.setColor(QPalette.Base, QColor(0x1E, 0x1E, 0x1E))
    palette.setColor(QPalette.AlternateBase, QColor(0x2A, 0x2A, 0x2A))
    palette.setColor(QPalette.ToolTipBase, QColor(0x2A, 0x2A, 0x2A))
    palette.setColor(QPalette.ToolTipText, on_surface)
    palette.setColor(QPalette.Text, on_surface)
    palette.setColor(QPalette.Button, QColor(0x2A, 0x2A, 0x2A))
    palette.setColor(QPalette.ButtonText, on_surface)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(0x88, 0xCC, 0xFF))
    palette.setColor(QPalette.Highlight, QColor(0x5A, 0x3A, 0x00))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)
    app.setStyleSheet("""
        QToolTip {
            background-color: #2A2A2A;
            color: #E0E0E0;
            border: 1px solid #555555;
            padding: 4px;
        }
        QScrollBar:vertical {
            background: #1A1A1A;
            width: 8px;
        }
        QScrollBar::handle:vertical {
            background: #444444;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """)


# ── Main Widget ────────────────────────────────────────────────────────────────

class HabitGridWidget(QWidget):
    """
    Main application widget matching the Android HabitGridScreen composable.
    Assembles: top bar, screen tabs, habit grid, info panel, edit control bar.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tail — Habit Tracker")
        # Window size: 8 cells × CELL_SIZE + spacing + margins ≈ 440px wide
        # Height: top bar + tabs + 10 rows × CELL_SIZE + spacing ≈ 600px
        grid_w = CELL_SIZE * 8 + 4 * 9 + 8  # 8 cells + 9 gaps of 4px + 8px margins
        grid_h = CELL_SIZE * 10 + 4 * 11 + 8
        self.setMinimumSize(grid_w, grid_h + 80)  # +80 for top bar + tab row

        # ── ViewModel ──────────────────────────────────────────────────────
        self.vm = HabitViewModel()
        self.vm.set_on_state_changed(self._on_state_changed)

        # ── Grid cell widgets ──────────────────────────────────────────────
        self._grid_cells = []  # list of (HabitButton | PlaceholderCell | QWidget)

        # ── Build UI ───────────────────────────────────────────────────────
        self._build_ui()
        self._refresh_all()

        # ── Auto-refresh timer (every 60 seconds) ─────────────────────────
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._refresh_timer.start(60_000)

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        """Build the complete UI hierarchy."""
        self.setStyleSheet("background-color: #121212;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Top bar
        self._top_bar = self._build_top_bar()
        root.addWidget(self._top_bar)

        # 2. Screen tab row
        self._tab_row_container = QWidget()
        self._tab_row_container.setStyleSheet("background-color: #111111;")
        self._tab_row_layout = QHBoxLayout(self._tab_row_container)
        self._tab_row_layout.setContentsMargins(4, 2, 4, 2)
        self._tab_row_layout.setSpacing(4)
        self._tab_row_layout.addStretch()
        root.addWidget(self._tab_row_container)

        # 3. Scrollable grid area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #121212; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background-color: #121212;")
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        self._grid_layout.setSpacing(3)  # Android uses 2.dp padding per cell ≈ 4dp gap

        scroll.setWidget(self._grid_widget)
        root.addWidget(scroll, 1)  # stretch factor 1 — grid takes remaining space

        # 4. Info panel (hidden by default)
        self._info_panel = HabitInfoPanel()
        self._info_panel.hide()
        root.addWidget(self._info_panel)

        # 5. Graphs panel (hidden by default, shown when graph mode is active)
        self._graphs_panel = GraphsPanel(self.vm)
        self._graphs_panel.hide()
        self._graphs_panel.setMaximumHeight(320)
        root.addWidget(self._graphs_panel)

        # 6. Edit control bar (hidden by default)
        self._edit_bar = EditModeControlBar()
        self._edit_bar.hide()
        self._connect_edit_bar_signals()

        # Wrap edit bar in a scroll area for long settings lists
        self._edit_bar_scroll = QScrollArea()
        self._edit_bar_scroll.setWidgetResizable(True)
        self._edit_bar_scroll.setWidget(self._edit_bar)
        self._edit_bar_scroll.setMaximumHeight(300)
        self._edit_bar_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._edit_bar_scroll.hide()
        root.addWidget(self._edit_bar_scroll)

    def _build_top_bar(self) -> QWidget:
        """Build the top app bar matching Android's TopAppBar."""
        bar = QWidget()
        bar.setStyleSheet("background-color: #1E1E1E;")
        bar.setFixedHeight(48)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(2)

        # Back arrow
        self._btn_prev_day = QPushButton("◀")
        self._btn_prev_day.setFixedSize(36, 36)
        self._btn_prev_day.setStyleSheet(self._icon_btn_style())
        self._btn_prev_day.clicked.connect(lambda: self.vm.navigate_day(-1))
        layout.addWidget(self._btn_prev_day)

        # Date label
        self._date_label = QLabel("Today")
        self._date_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self._date_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._date_label)

        # Forward arrow
        self._btn_next_day = QPushButton("▶")
        self._btn_next_day.setFixedSize(36, 36)
        self._btn_next_day.setStyleSheet(self._icon_btn_style())
        self._btn_next_day.clicked.connect(lambda: self.vm.navigate_day(+1))
        layout.addWidget(self._btn_next_day)

        layout.addStretch()

        # Graph mode toggle (📊) — matches Android's BarChart icon button
        self._btn_graph = QPushButton("📊")
        self._btn_graph.setFixedSize(36, 36)
        self._btn_graph.setToolTip("Graph mode")
        self._btn_graph.setStyleSheet(self._icon_btn_style())
        self._btn_graph.clicked.connect(self.vm.toggle_graph_mode)
        layout.addWidget(self._btn_graph)

        # Edit mode toggle
        self._btn_edit = QPushButton("✏")
        self._btn_edit.setFixedSize(36, 36)
        self._btn_edit.setToolTip("Edit mode")
        self._btn_edit.setStyleSheet(self._icon_btn_style())
        self._btn_edit.clicked.connect(self.vm.toggle_edit_mode)
        layout.addWidget(self._btn_edit)

        # Info mode toggle
        self._btn_info = QPushButton("ℹ")
        self._btn_info.setFixedSize(36, 36)
        self._btn_info.setToolTip("Info mode")
        self._btn_info.setStyleSheet(self._icon_btn_style())
        self._btn_info.clicked.connect(self.vm.toggle_info_mode)
        layout.addWidget(self._btn_info)

        # Settings button
        self._btn_settings = QPushButton("⚙")
        self._btn_settings.setFixedSize(36, 36)
        self._btn_settings.setToolTip("Settings")
        self._btn_settings.setStyleSheet(self._icon_btn_style())
        self._btn_settings.clicked.connect(self._on_settings_clicked)
        layout.addWidget(self._btn_settings)

        return bar

    @staticmethod
    def _icon_btn_style(active: bool = False, active_color: str = "#FFAA00",
                        active_bg: str = "#4A2A00") -> str:
        """Returns stylesheet for a top-bar icon button."""
        if active:
            return f"""
                QPushButton {{
                    background-color: {active_bg};
                    color: {active_color};
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                }}
                QPushButton:hover {{ background-color: #5A3A00; }}
            """
        return """
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #333333; }
            QPushButton:disabled { color: #555555; }
        """

    def _connect_edit_bar_signals(self):
        """Connect all EditModeControlBar signals to handlers."""
        self._edit_bar.start_move.connect(self.vm.start_move_mode)
        self._edit_bar.add_habit.connect(self._on_add_habit_requested)
        self._edit_bar.move_to_screen.connect(self.vm.move_habit_to_screen)
        self._edit_bar.add_screen.connect(self._on_add_screen)
        self._edit_bar.delete_screen.connect(self._on_delete_screen)
        self._edit_bar.toggle_max_one.connect(self.vm.toggle_max_one)
        self._edit_bar.toggle_custom_input.connect(self.vm.toggle_custom_input)
        self._edit_bar.toggle_text_input.connect(self.vm.toggle_text_input)
        self._edit_bar.toggle_text_input_options.connect(self.vm.toggle_text_input_options)
        self._edit_bar.pick_text_input_file.connect(self._on_pick_text_input_file)
        self._edit_bar.toggle_dated_entry.connect(self.vm.toggle_dated_entry)
        self._edit_bar.pick_dated_entry_file.connect(self._on_pick_dated_entry_file)
        self._edit_bar.delete_habit.connect(self._on_delete_habit)
        self._edit_bar.change_icon.connect(self._on_change_icon)
        self._edit_bar.set_count.connect(self.vm.set_habit_count)
        self._edit_bar.set_divider.connect(self.vm.set_habit_divider)

    # ── State refresh ──────────────────────────────────────────────────────────

    def _on_state_changed(self):
        """Called by the ViewModel whenever state changes."""
        self._refresh_all()

    def _auto_refresh(self):
        """Periodic refresh to catch external database changes."""
        self.vm.refresh()

    def _refresh_all(self):
        """Rebuild all UI elements from current ViewModel state."""
        self._refresh_top_bar()
        self._refresh_tab_row()
        self._refresh_grid()
        self._refresh_bottom_panels()

    def _refresh_top_bar(self):
        """Update the top bar date label and button states."""
        is_today = self.vm.is_today
        if is_today:
            self._date_label.setText("Today")
            self._date_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        else:
            self._date_label.setText(self.vm.selected_date.strftime(DISPLAY_DATE_FMT))
            self._date_label.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: bold;")

        self._btn_next_day.setEnabled(not is_today)

        # Graph button highlight — light blue when active, matching Android's Color(0xFF4FC3F7)
        if self.vm.graph_mode:
            self._btn_graph.setStyleSheet(self._icon_btn_style(
                active=True, active_color="#4FC3F7", active_bg="#0A2A4A"))
        else:
            self._btn_graph.setStyleSheet(self._icon_btn_style())

        # Edit button highlight
        if self.vm.edit_mode:
            self._btn_edit.setStyleSheet(self._icon_btn_style(
                active=True, active_color="#FFAA00", active_bg="#4A2A00"))
        else:
            self._btn_edit.setStyleSheet(self._icon_btn_style())

        # Info button highlight
        if self.vm.info_mode:
            self._btn_info.setStyleSheet(self._icon_btn_style(
                active=True, active_color="#88CCFF", active_bg="#1A4A7A"))
        else:
            self._btn_info.setStyleSheet(self._icon_btn_style())

    def _refresh_tab_row(self):
        """Rebuild the screen tab row."""
        # Clear existing tabs
        while self._tab_row_layout.count():
            item = self._tab_row_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        screens = self.vm.habit_screens
        if len(screens) <= 1:
            self._tab_row_container.hide()
            return

        self._tab_row_container.show()
        for idx, screen in enumerate(screens):
            is_active = idx == self.vm.active_screen_index
            label = f"✎ {screen.name}" if (self.vm.edit_mode and is_active) else screen.name

            btn = QPushButton(label)
            btn.setFixedHeight(32)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #555555;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 0 10px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #666666; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #888888;
                        border: none;
                        border-radius: 4px;
                        padding: 0 10px;
                        font-size: 12px;
                    }
                    QPushButton:hover { background-color: #333333; }
                """)

            # In edit mode, clicking active tab opens rename dialog
            if self.vm.edit_mode and is_active:
                btn.clicked.connect(lambda checked, i=idx: self._on_rename_screen(i))
            else:
                btn.clicked.connect(lambda checked, i=idx: self.vm.switch_screen(i))

            self._tab_row_layout.addWidget(btn)

        self._tab_row_layout.addStretch()

    def _refresh_grid(self):
        """Rebuild the 8-column grid of habit buttons and placeholders."""
        # Remove all existing grid widgets
        for cell in self._grid_cells:
            cell.setParent(None)
            cell.deleteLater()
        self._grid_cells.clear()

        habits = self.vm.habits
        is_move_pending = self.vm.move_pending_source_index >= 0

        # Build cells list: habits + placeholders to fill TOTAL_GRID_CELLS
        total_cells = max(TOTAL_GRID_CELLS, len(habits))

        for idx in range(total_cells):
            row = idx // GRID_COLUMNS
            col = idx % GRID_COLUMNS

            habit = habits[idx] if idx < len(habits) else None
            # Empty-name habits are embedded placeholders
            if habit is not None and not habit.name:
                habit = None

            if habit is not None:
                cell = self._create_habit_cell(habit, idx, is_move_pending)
            elif self.vm.edit_mode:
                cell = self._create_placeholder_cell(idx, is_move_pending)
            else:
                # Invisible spacer in normal mode
                cell = QWidget()
                cell.setFixedSize(CELL_SIZE, CELL_SIZE)
                cell.setStyleSheet("background-color: transparent;")

            self._grid_layout.addWidget(cell, row, col)
            self._grid_cells.append(cell)

    def _create_habit_cell(self, habit: Habit, index: int, is_move_pending: bool) -> HabitButton:
        """Create a HabitButton for a real habit."""
        btn = HabitButton(habit)
        btn.set_custom_icon_overrides(self.vm.settings.habit_icons)

        is_edit_selected = self.vm.edit_mode and index == self.vm.selected_edit_index
        is_info_selected = (self.vm.info_mode and self.vm.selected_info_habit is not None
                            and self.vm.selected_info_habit.name == habit.name)
        is_move_source = self.vm.edit_mode and index == self.vm.move_pending_source_index
        is_graph_selected = self.vm.graph_mode and habit.name in self.vm.graph_selected_habits

        btn.set_modes(
            info_mode=self.vm.info_mode,
            edit_mode=self.vm.edit_mode,
            graph_mode=self.vm.graph_mode,
            is_selected=is_edit_selected or is_info_selected,
            is_graph_selected=is_graph_selected,
            is_move_pending_source=is_move_source,
            is_move_pending_target=is_move_pending and not is_move_source and self.vm.edit_mode
        )

        # Click handler
        btn.clicked.connect(lambda h=habit, i=index: self._on_habit_clicked(h, i))
        # Double-click (long press equivalent)
        btn.long_clicked.connect(lambda h=habit: self._on_habit_long_clicked(h))

        return btn

    def _create_placeholder_cell(self, index: int, is_move_pending: bool) -> PlaceholderCell:
        """Create a PlaceholderCell for an empty grid position in edit mode."""
        cell = PlaceholderCell()
        cell.set_state(
            is_selected=index == self.vm.selected_edit_index,
            is_move_pending_target=is_move_pending
        )
        cell.clicked.connect(lambda i=index: self.vm.select_edit_habit(i))
        return cell

    def _refresh_bottom_panels(self):
        """Show/hide info panel, graphs panel, and edit control bar based on mode."""
        # Info panel
        if self.vm.info_mode:
            self._info_panel.show()
            self._info_panel.update_habit(self.vm.selected_info_habit)
        else:
            self._info_panel.hide()

        # Graphs panel — shown when graph mode is active
        if self.vm.graph_mode:
            self._graphs_panel.show()
            self._graphs_panel.refresh()
        else:
            self._graphs_panel.hide()

        # Edit control bar
        if self.vm.edit_mode:
            self._edit_bar_scroll.show()
            self._edit_bar.show()

            # Determine selection state
            selected_idx = self.vm.selected_edit_index
            habits = self.vm.habits
            selected_habit = None
            selected_name = None
            selected_raw_count = 0
            is_placeholder = False

            if selected_idx >= 0:
                if selected_idx < len(habits):
                    selected_habit = habits[selected_idx]
                    selected_name = selected_habit.name if selected_habit.name else None
                    selected_raw_count = selected_habit.raw_today_count if selected_name else 0
                    is_placeholder = not selected_name
                else:
                    is_placeholder = True

            self._edit_bar.update_state(
                selected_index=selected_idx,
                selected_habit_name=selected_name,
                selected_raw_count=selected_raw_count,
                is_placeholder=is_placeholder,
                move_pending=self.vm.move_pending_source_index >= 0,
                habit_screens=self.vm.habit_screens,
                active_screen_index=self.vm.active_screen_index,
                max_one_habits=self.vm.settings.max_one_habits,
                custom_input_habits=self.vm.settings.custom_input_habits,
                text_input_habits=self.vm.settings.text_input_habits,
                text_input_options_habits=self.vm.settings.text_input_options_habits,
                text_input_file_uris=self.vm.settings.text_input_file_uris,
                dated_entry_habits=self.vm.settings.dated_entry_habits,
                dated_entry_file_uris=self.vm.settings.dated_entry_file_uris,
                habit_dividers=self.vm.settings.habit_dividers
            )
        else:
            self._edit_bar.hide()
            self._edit_bar_scroll.hide()

    # ── Click handlers ─────────────────────────────────────────────────────────

    def _on_habit_clicked(self, habit: Habit, index: int):
        """Handle a habit button click — behavior depends on current mode."""
        if self.vm.graph_mode:
            # In graph mode, clicking a habit toggles its selection for graphing
            self.vm.toggle_graph_habit_selection(habit.name)
        elif self.vm.edit_mode:
            self.vm.select_edit_habit(index)
        elif self.vm.info_mode:
            self.vm.select_info_habit(habit)
        elif habit.name in self.vm.settings.text_input_habits:
            self._show_text_input_dialog(habit)
        elif habit.use_custom_input:
            self._show_increment_dialog(habit)
        else:
            self.vm.increment_habit(habit.name, 1)

    def _on_habit_long_clicked(self, habit: Habit):
        """Handle double-click (long press equivalent) — toggle custom input."""
        if not self.vm.info_mode and not self.vm.edit_mode and not self.vm.graph_mode:
            self.vm.toggle_custom_input(habit.name)

    def _show_increment_dialog(self, habit: Habit):
        """Show the custom increment dialog."""
        amount = IncrementDialog.get_amount(habit.name, habit.today_count, self)
        if amount is not None:
            self.vm.increment_habit(habit.name, amount)

    def _show_text_input_dialog(self, habit: Habit):
        """Show the text input dialog."""
        show_opts = habit.name in self.vm.settings.text_input_options_habits
        options = []
        if show_opts:
            # Load past entries from the text input file
            file_path = self.vm.settings.text_input_file_uris.get(habit.name)
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        options = [line.strip() for line in f.readlines() if line.strip()]
                    # Deduplicate and reverse (most recent first)
                    seen = set()
                    unique = []
                    for opt in reversed(options):
                        if opt not in seen:
                            seen.add(opt)
                            unique.append(opt)
                    options = unique
                except Exception:
                    pass

        text = TextInputDialog.get_text(habit.name, show_opts, options, self)
        if text is not None:
            # Save text entry to file
            file_path = self.vm.settings.text_input_file_uris.get(habit.name)
            if file_path:
                try:
                    with open(file_path, 'a') as f:
                        f.write(text + '\n')
                except Exception:
                    pass
            # Increment the habit
            self.vm.increment_habit(habit.name, 1)

    # ── Edit mode action handlers ──────────────────────────────────────────────

    def _on_add_habit_requested(self):
        """Show the add habit dialog."""
        name = AddHabitDialog.get_name(self)
        if name:
            self.vm.add_habit(name, self.vm.selected_edit_index)

    def _on_add_screen(self):
        """Show the add screen dialog."""
        name = AddScreenDialog.get_name(self)
        if name:
            self.vm.add_screen(name)

    def _on_delete_screen(self):
        """Delete the current screen (with confirmation if it has habits)."""
        screen_idx = self.vm.active_screen_index
        if screen_idx < 0 or screen_idx >= len(self.vm.habit_screens):
            return
        screen = self.vm.habit_screens[screen_idx]
        habit_count = len([h for h in screen.habit_names if h])
        if habit_count > 0:
            reply = QMessageBox.question(
                self, "Delete Screen",
                f'Delete screen "{screen.name}"?\n\n'
                f'{habit_count} habits will be moved to the first screen.',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        self.vm.delete_screen(screen_idx)

    def _on_rename_screen(self, screen_index: int):
        """Show the rename screen dialog."""
        if screen_index < 0 or screen_index >= len(self.vm.habit_screens):
            return
        current_name = self.vm.habit_screens[screen_index].name
        new_name = RenameScreenDialog.get_name(current_name, self)
        if new_name:
            self.vm.rename_screen(screen_index, new_name)

    def _on_delete_habit(self, habit_name: str):
        """Show delete habit confirmation dialog."""
        if DeleteHabitConfirmDialog.confirm(habit_name, self):
            # Find the index of this habit
            for i, h in enumerate(self.vm.habits):
                if h.name == habit_name:
                    self.vm.delete_habit(i)
                    break

    def _on_change_icon(self, habit_name: str):
        """Show the icon picker dialog."""
        current_icon = self.vm.settings.habit_icons.get(habit_name)
        if current_icon is None:
            current_icon = get_habit_icon_name(habit_name)
        new_icon = IconPickerDialog.pick_icon(habit_name, current_icon, self)
        if new_icon != current_icon:
            self.vm.set_habit_icon(habit_name, new_icon)

    def _on_pick_text_input_file(self, habit_name: str):
        """Open a file dialog to select a text input log file."""
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select text log file for {habit_name}",
            os.path.expanduser("~"),
            "All Files (*)"
        )
        if path:
            self.vm.set_text_input_file_uri(habit_name, path)

    def _on_pick_dated_entry_file(self, habit_name: str):
        """Open a file dialog to select a dated entry source file."""
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select dated entry file for {habit_name}",
            os.path.expanduser("~"),
            "Text Files (*.txt *.md);;All Files (*)"
        )
        if path:
            self.vm.set_dated_entry_file_uri(habit_name, path)

    def _on_settings_clicked(self):
        """Show a simple settings info message (desktop doesn't need file pickers like Android)."""
        from habit_view_model import HABITSDB_PATH, SCREENS_RELAY_FILE
        QMessageBox.information(
            self, "Settings",
            f"Database file:\n{HABITSDB_PATH}\n\n"
            f"Screens relay file:\n{SCREENS_RELAY_FILE}\n\n"
            f"Settings file:\n~/.config/py_habits_widget/settings.json"
        )


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Tail Habit Tracker")
    apply_dark_theme(app)

    widget = HabitGridWidget()
    widget.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
