"""
Main controller / state management for the habit tracker.
Matches the Android app's HabitViewModel.kt.
Owns habits list + settings state, delegates I/O to repositories.
"""
import json
import os
import uuid
from datetime import date, timedelta
from typing import List, Optional, Set, Dict, Callable

from habit_models import (
    Habit, HabitScreen, AppSettings, HabitsDatabase, HABIT_ORDER, apply_divider
)
from habit_calculator import date_string, parse_date, build_habit
import habits_repository as repo
import settings_repository as settings_repo

# ── Paths ──────────────────────────────────────────────────────────────────────

with open(os.path.expanduser('~/Projects/py_habits_widget/obsidian_dir.txt'), 'r') as f:
    OBSIDIAN_DIR = f.read().strip()

HABITSDB_PATH = OBSIDIAN_DIR + 'habitsdb.txt'
SCREENS_RELAY_FILE = os.path.expanduser('~/noteVault/tail/screens_layout.json')

TOTAL_GRID_CELLS = 80


class HabitViewModel:
    """
    Main state manager matching the Android HabitViewModel.
    """

    def __init__(self):
        self.habits: List[Habit] = []
        self.settings: AppSettings = AppSettings()
        self.selected_date: date = date.today()
        self.info_mode: bool = False
        self.edit_mode: bool = False
        self.graph_mode: bool = False
        self.graph_selected_habits: set = set()
        self.graph_time_period: str = "1M"  # default: 1 month
        self.selected_info_habit: Optional[Habit] = None
        self.selected_edit_index: int = -1
        self.move_pending_source_index: int = -1
        self.habit_screens: List[HabitScreen] = []
        self.active_screen_index: int = 0
        self.cached_db: HabitsDatabase = {}

        # Callbacks for UI updates
        self._on_state_changed: Optional[Callable] = None

        # Load settings and data
        self._load_initial()

    def set_on_state_changed(self, callback: Callable):
        """Set a callback that fires whenever state changes and UI should refresh."""
        self._on_state_changed = callback

    def _notify(self):
        """Notify the UI that state has changed."""
        if self._on_state_changed:
            self._on_state_changed()

    def _load_initial(self):
        """Load settings and database on startup."""
        self.settings = settings_repo.load_settings()

        # Sync screens from settings
        if self.settings.habit_screens:
            self.habit_screens = self.settings.habit_screens
            self.active_screen_index = min(
                self.settings.active_screen_index,
                max(0, len(self.habit_screens) - 1)
            )
        elif self.settings.habit_order:
            pass  # Use flat order

        # Load screens from relay file if settings screens are empty
        if not self.habit_screens:
            self._load_screens_from_relay()

        # Load database
        self.cached_db = repo.ensure_days_exist(HABITSDB_PATH)
        self._rebuild_habit_list()

    def _load_screens_from_relay(self):
        """Load screens from the relay file (shared with Android)."""
        try:
            with open(SCREENS_RELAY_FILE, 'r') as f:
                data = json.load(f)
            screens_data = data.get('screens', [])
            habit_icons = data.get('habit_icons', {})
            if screens_data:
                self.habit_screens = []
                for s in screens_data:
                    self.habit_screens.append(HabitScreen(
                        id=s.get('id', ''),
                        name=s.get('name', ''),
                        habit_names=s.get('habits', [])
                    ))
                self.settings.habit_icons = habit_icons
                self.active_screen_index = min(
                    data.get('active_screen_index', 0),
                    max(0, len(self.habit_screens) - 1)
                )
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def active_habit_order(self) -> List[str]:
        """Returns the ordered list of habit names for the currently active screen."""
        if self.habit_screens:
            idx = min(self.active_screen_index, max(0, len(self.habit_screens) - 1))
            return self.habit_screens[idx].habit_names
        order = self.settings.habit_order
        return order if order else HABIT_ORDER

    def screen_index_for_habit(self, habit_name: str) -> int:
        """Returns the screen index containing the habit, or -1."""
        for i, screen in enumerate(self.habit_screens):
            if habit_name in screen.habit_names:
                return i
        return -1

    def _rebuild_habit_list(self):
        """Rebuilds the displayed habit list from cached data."""
        effective_order = self.active_habit_order()
        if not effective_order and self.habit_screens:
            self.habits = []
            return
        settings_copy = AppSettings(
            custom_input_habits=self.settings.custom_input_habits,
            habit_order=effective_order,
            habit_dividers=self.settings.habit_dividers,
            max_one_habits=self.settings.max_one_habits,
            text_input_habits=self.settings.text_input_habits,
        )
        self.habits = repo.build_habit_list(self.cached_db, settings_copy, self.selected_date)

    # ── Day navigation ─────────────────────────────────────────────────────────

    def navigate_day(self, delta_days: int):
        """Navigate the selected date by delta_days. Cannot go past today."""
        new_date = self.selected_date + timedelta(days=delta_days)
        today = date.today()
        self.selected_date = min(new_date, today)
        self._rebuild_habit_list()
        self._notify()

    @property
    def is_today(self) -> bool:
        return self.selected_date == date.today()

    # ── Habit increment ────────────────────────────────────────────────────────

    def increment_habit(self, habit_name: str, amount: int = 1):
        """Increment a habit's count for the selected date."""
        date_str = date_string(self.selected_date)
        current_entries = self.cached_db.get(habit_name, {})
        raw_new = (current_entries.get(date_str, 0)) + amount

        # Apply 1-max cap
        if habit_name in self.settings.max_one_habits:
            raw_new = min(raw_new, 1)

        # Check if count actually changed
        if raw_new == current_entries.get(date_str, 0):
            return

        # Update in-memory cache
        self.cached_db = repo.apply_increment_to_db(
            self.cached_db, habit_name, amount, self.selected_date
        )

        # Rebuild and persist
        self._rebuild_habit_list()
        repo.persist_database(HABITSDB_PATH, self.cached_db)
        self._write_screens_relay_file()
        self._notify()

    def set_habit_count(self, habit_name: str, new_count: int):
        """Set the count for a habit to an absolute value."""
        clamped = max(0, new_count)
        date_str = date_string(self.selected_date)
        current_entries = self.cached_db.get(habit_name, {})
        current_count = current_entries.get(date_str, 0)
        delta = clamped - current_count
        if delta != 0:
            self.cached_db = repo.apply_increment_to_db(
                self.cached_db, habit_name, delta, self.selected_date
            )
        self._rebuild_habit_list()
        repo.persist_database(HABITSDB_PATH, self.cached_db)
        self._notify()

    # ── Mode toggles ───────────────────────────────────────────────────────────

    def toggle_info_mode(self):
        turning_on = not self.info_mode
        self.info_mode = turning_on
        if not turning_on:
            self.selected_info_habit = None
        else:
            self.edit_mode = False
            self.selected_edit_index = -1
            self.move_pending_source_index = -1
        self._notify()

    def toggle_edit_mode(self):
        turning_on = not self.edit_mode
        self.edit_mode = turning_on
        if not turning_on:
            self.selected_edit_index = -1
            self.move_pending_source_index = -1
        else:
            self.info_mode = False
            self.selected_info_habit = None
            self.graph_mode = False
            self.graph_selected_habits = set()
        self._notify()

    def toggle_graph_mode(self):
        """Toggle graph mode on/off, matching Android's toggleGraphMode()."""
        turning_on = not self.graph_mode
        self.graph_mode = turning_on
        if turning_on:
            # Deactivate other modes
            self.info_mode = False
            self.selected_info_habit = None
            self.edit_mode = False
            self.selected_edit_index = -1
            self.move_pending_source_index = -1
        else:
            self.graph_selected_habits = set()
        self._notify()

    def toggle_graph_habit_selection(self, habit_name: str):
        """Toggle a habit's selection for graphing, matching Android's toggleGraphHabitSelection()."""
        if habit_name in self.graph_selected_habits:
            self.graph_selected_habits.discard(habit_name)
        else:
            self.graph_selected_habits.add(habit_name)
        self._notify()

    def set_graph_time_period(self, period: str):
        """Set the graph time period (e.g. '1W', '2W', '1M', '3M', '6M', '1Y', 'Max')."""
        self.graph_time_period = period
        self._notify()

    def get_graph_data(self, habit_name: str, start_date: date, end_date: date) -> list:
        """
        Returns list of (date_str, value) tuples for a habit in the given date range.
        Matches Android's getGraphData().
        """
        from habit_calculator import build_habit
        entries = self.cached_db.get(habit_name, {})
        divider = self.settings.habit_dividers.get(habit_name, 1)
        result = []
        current = start_date
        while current <= end_date:
            ds = current.strftime('%Y-%m-%d')
            raw = entries.get(ds, 0)
            # Apply divider (same as applyDivider in Android)
            value = raw // divider if divider > 1 else raw
            result.append((ds, value))
            from datetime import timedelta
            current += timedelta(days=1)
        return result

    def select_info_habit(self, habit: Habit):
        """Select a habit for info display, computing full stats on demand."""
        # Compute full stats for this single habit (rolling averages, ATH)
        entries = self.cached_db.get(habit.name, {})
        full_habit = build_habit(
            name=habit.name,
            entries=entries,
            use_custom_input=habit.use_custom_input,
            divider=habit.divider,
            target_date=self.selected_date,
            compute_full_stats=True
        )
        self.selected_info_habit = full_habit
        self._notify()

    def select_edit_habit(self, index: int):
        """Select or deselect a cell in edit mode. If move pending, perform the move."""
        if self.move_pending_source_index >= 0:
            from_idx = self.move_pending_source_index
            self.move_pending_source_index = -1
            if index != from_idx:
                self._apply_move(from_idx, index)
            self.selected_edit_index = index
            self._notify()
            return

        if self.selected_edit_index == index:
            self.selected_edit_index = -1
        else:
            self.selected_edit_index = index
        self._notify()

    def start_move_mode(self):
        """Enter or cancel move-pending mode."""
        if self.selected_edit_index < 0:
            return
        if self.move_pending_source_index >= 0:
            self.move_pending_source_index = -1
        else:
            self.move_pending_source_index = self.selected_edit_index
        self._notify()

    def _apply_move(self, from_idx: int, to_idx: int):
        """Move a habit from one grid position to another."""
        if from_idx == to_idx:
            return

        if self.habit_screens:
            screen_idx = min(self.active_screen_index, len(self.habit_screens) - 1)
            screen = self.habit_screens[screen_idx]
            current = list(screen.habit_names)
            if from_idx >= len(current):
                return

            while len(current) <= to_idx:
                current.append("")

            habit_to_move = current[from_idx]
            current[from_idx] = ""

            if not current[to_idx]:
                current[to_idx] = habit_to_move
            else:
                # Shift right to find empty slot
                empty_slot = -1
                for i in range(to_idx, len(current)):
                    if not current[i]:
                        empty_slot = i
                        break
                if empty_slot < 0:
                    current.append("")
                    empty_slot = len(current) - 1
                for i in range(empty_slot, to_idx, -1):
                    current[i] = current[i - 1]
                current[to_idx] = habit_to_move

            self.habit_screens[screen_idx] = HabitScreen(
                id=screen.id, name=screen.name, habit_names=current
            )
            self._rebuild_habit_list()
            self._persist_screens()
        else:
            order = list(self.settings.habit_order or HABIT_ORDER)
            if from_idx >= len(order):
                return
            while len(order) <= to_idx:
                order.append("")
            habit_to_move = order[from_idx]
            order[from_idx] = ""
            if not order[to_idx]:
                order[to_idx] = habit_to_move
            else:
                empty_slot = -1
                for i in range(to_idx, len(order)):
                    if not order[i]:
                        empty_slot = i
                        break
                if empty_slot < 0:
                    order.append("")
                    empty_slot = len(order) - 1
                for i in range(empty_slot, to_idx, -1):
                    order[i] = order[i - 1]
                order[to_idx] = habit_to_move
            self.settings.habit_order = order
            settings_repo.save_habit_order(order)
            self._rebuild_habit_list()

    # ── Screen management ──────────────────────────────────────────────────────

    def switch_screen(self, index: int):
        if not self.habit_screens or index < 0 or index >= len(self.habit_screens):
            return
        self.active_screen_index = index
        self.selected_edit_index = -1
        self._rebuild_habit_list()
        settings_repo.save_active_screen_index(index)
        self._notify()

    def add_screen(self, name: str):
        if not self.habit_screens:
            general_habits = self.settings.habit_order or HABIT_ORDER
            self.habit_screens.append(HabitScreen(
                id=str(uuid.uuid4()), name="general", habit_names=list(general_habits)
            ))
        new_screen = HabitScreen(id=str(uuid.uuid4()), name=name, habit_names=[])
        self.habit_screens.append(new_screen)
        self.active_screen_index = len(self.habit_screens) - 1
        self.selected_edit_index = -1
        self._rebuild_habit_list()
        self._persist_screens()
        self._notify()

    def delete_screen(self, screen_index: Optional[int] = None):
        if screen_index is None:
            screen_index = self.active_screen_index
        if len(self.habit_screens) <= 1:
            return
        if screen_index < 0 or screen_index >= len(self.habit_screens):
            return

        orphans = self.habit_screens[screen_index].habit_names
        target_idx = 1 if screen_index == 0 else 0
        self.habit_screens[target_idx] = HabitScreen(
            id=self.habit_screens[target_idx].id,
            name=self.habit_screens[target_idx].name,
            habit_names=self.habit_screens[target_idx].habit_names + orphans
        )
        self.habit_screens.pop(screen_index)
        self.active_screen_index = min(self.active_screen_index, len(self.habit_screens) - 1)
        self.selected_edit_index = -1
        self._rebuild_habit_list()
        self._persist_screens()
        self._notify()

    def rename_screen(self, screen_index: int, new_name: str):
        if screen_index < 0 or screen_index >= len(self.habit_screens):
            return
        trimmed = new_name.strip()
        if not trimmed:
            return
        screen = self.habit_screens[screen_index]
        self.habit_screens[screen_index] = HabitScreen(
            id=screen.id, name=trimmed, habit_names=screen.habit_names
        )
        self._persist_screens()
        self._notify()

    def move_habit_to_screen(self, target_screen_index: int):
        idx = self.selected_edit_index
        if idx < 0 or not self.habit_screens:
            return
        if target_screen_index < 0 or target_screen_index >= len(self.habit_screens):
            return
        current_screen_idx = min(self.active_screen_index, len(self.habit_screens) - 1)
        if target_screen_index == current_screen_idx:
            return

        current_screen = self.habit_screens[current_screen_idx]
        habit_names = list(current_screen.habit_names)
        if idx >= len(habit_names):
            return
        habit_name = habit_names[idx]
        if not habit_name:
            return

        habit_names[idx] = ""
        self.habit_screens[current_screen_idx] = HabitScreen(
            id=current_screen.id, name=current_screen.name, habit_names=habit_names
        )
        target = self.habit_screens[target_screen_index]
        self.habit_screens[target_screen_index] = HabitScreen(
            id=target.id, name=target.name,
            habit_names=target.habit_names + [habit_name]
        )
        self.selected_edit_index = -1
        self._rebuild_habit_list()
        self._persist_screens()
        self._notify()

    def add_habit(self, habit_name: str, at_index: int):
        trimmed = habit_name.strip()
        if not trimmed:
            return

        if self.habit_screens:
            screen_idx = min(self.active_screen_index, len(self.habit_screens) - 1)
            screen = self.habit_screens[screen_idx]
            current = list(screen.habit_names)
            if at_index < len(current) and not current[at_index]:
                current[at_index] = trimmed
            else:
                insert_at = min(at_index, len(current))
                current.insert(insert_at, trimmed)
            self.habit_screens[screen_idx] = HabitScreen(
                id=screen.id, name=screen.name, habit_names=current
            )
            self._persist_screens()
        else:
            order = list(self.settings.habit_order or HABIT_ORDER)
            if at_index < len(order) and not order[at_index]:
                order[at_index] = trimmed
            else:
                insert_at = min(at_index, len(order))
                order.insert(insert_at, trimmed)
            self.settings.habit_order = order
            settings_repo.save_habit_order(order)

        # Add to database file
        repo.add_habit_to_file(HABITSDB_PATH, trimmed)
        self.cached_db = repo.ensure_days_exist(HABITSDB_PATH)
        self._rebuild_habit_list()
        self._notify()

    def delete_habit(self, index: int):
        if self.habit_screens:
            screen_idx = min(self.active_screen_index, len(self.habit_screens) - 1)
            screen = self.habit_screens[screen_idx]
            current = list(screen.habit_names)
            if index < 0 or index >= len(current):
                return
            if not current[index]:
                return
            current.pop(index)
            self.habit_screens[screen_idx] = HabitScreen(
                id=screen.id, name=screen.name, habit_names=current
            )
            self._persist_screens()
        else:
            order = list(self.settings.habit_order or HABIT_ORDER)
            if index < 0 or index >= len(order):
                return
            if not order[index]:
                return
            order.pop(index)
            self.settings.habit_order = order
            settings_repo.save_habit_order(order)

        self.selected_edit_index = -1
        self._rebuild_habit_list()
        self._notify()

    # ── Per-habit settings ─────────────────────────────────────────────────────

    def toggle_max_one(self, habit_name: str):
        current = set(self.settings.max_one_habits)
        if habit_name in current:
            current.discard(habit_name)
        else:
            current.add(habit_name)
        self.settings.max_one_habits = current
        settings_repo.save_max_one_habits(current)
        self._notify()

    def toggle_custom_input(self, habit_name: str):
        current = set(self.settings.custom_input_habits)
        if habit_name in current:
            current.discard(habit_name)
        else:
            current.add(habit_name)
        self.settings.custom_input_habits = current
        settings_repo.save_custom_input_habits(current)
        self._rebuild_habit_list()
        self._notify()

    def toggle_text_input(self, habit_name: str):
        current = set(self.settings.text_input_habits)
        if habit_name in current:
            current.discard(habit_name)
            opts = set(self.settings.text_input_options_habits)
            opts.discard(habit_name)
            self.settings.text_input_options_habits = opts
            settings_repo.save_text_input_options_habits(opts)
        else:
            current.add(habit_name)
        self.settings.text_input_habits = current
        settings_repo.save_text_input_habits(current)
        self._notify()

    def toggle_text_input_options(self, habit_name: str):
        current = set(self.settings.text_input_options_habits)
        if habit_name in current:
            current.discard(habit_name)
        else:
            current.add(habit_name)
        self.settings.text_input_options_habits = current
        settings_repo.save_text_input_options_habits(current)
        self._notify()

    def set_text_input_file_uri(self, habit_name: str, path: str):
        uris = dict(self.settings.text_input_file_uris)
        uris[habit_name] = path
        self.settings.text_input_file_uris = uris
        settings_repo.save_text_input_file_uris(uris)
        self._notify()

    def set_habit_icon(self, habit_name: str, icon_name: Optional[str]):
        icons = dict(self.settings.habit_icons)
        if icon_name is None:
            icons.pop(habit_name, None)
        else:
            icons[habit_name] = icon_name
        self.settings.habit_icons = icons
        settings_repo.save_habit_icons(icons)
        self._write_screens_relay_file()
        self._notify()

    def set_habit_divider(self, habit_name: str, divisor: int):
        dividers = dict(self.settings.habit_dividers)
        if divisor <= 1:
            dividers.pop(habit_name, None)
        else:
            dividers[habit_name] = divisor
        self.settings.habit_dividers = dividers
        settings_repo.save_habit_dividers(dividers)
        self._rebuild_habit_list()
        self._notify()

    def toggle_dated_entry(self, habit_name: str):
        current = set(self.settings.dated_entry_habits)
        if habit_name in current:
            current.discard(habit_name)
        else:
            current.add(habit_name)
        self.settings.dated_entry_habits = current
        settings_repo.save_dated_entry_habits(current)
        self._notify()

    def set_dated_entry_file_uri(self, habit_name: str, path: str):
        uris = dict(self.settings.dated_entry_file_uris)
        uris[habit_name] = path
        self.settings.dated_entry_file_uris = uris
        settings_repo.save_dated_entry_file_uris(uris)
        self._notify()

    # ── Persistence helpers ────────────────────────────────────────────────────

    def _persist_screens(self):
        settings_repo.save_habit_screens(self.habit_screens)
        settings_repo.save_active_screen_index(self.active_screen_index)
        self._write_screens_relay_file()

    def _write_screens_relay_file(self):
        """Write the current screen layout to the relay file for the Android app."""
        try:
            screens_data = []
            for screen in self.habit_screens:
                screens_data.append({
                    'id': screen.id,
                    'name': screen.name,
                    'habits': screen.habit_names
                })
            data = {
                'version': 1,
                'active_screen_index': self.active_screen_index,
                'habit_icons': self.settings.habit_icons,
                'screens': screens_data
            }
            relay_dir = os.path.dirname(SCREENS_RELAY_FILE)
            if os.path.isdir(relay_dir):
                with open(SCREENS_RELAY_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception:
            pass

    def refresh(self):
        """Full refresh: reload database and rebuild."""
        self.cached_db = repo.ensure_days_exist(HABITSDB_PATH)
        self._load_screens_from_relay()
        self._rebuild_habit_list()
        self._notify()
