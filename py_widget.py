import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QPushButton,
                              QSpacerItem, QSizePolicy, QInputDialog, QLabel,
                              QComboBox, QDialog, QVBoxLayout, QHBoxLayout,
                              QCheckBox, QTabWidget, QTabBar)
from PyQt5.QtGui import QPainter, QFont, QIcon
from PyQt5.QtCore import QSize, Qt
import matplotlib.pyplot as plt
import os
import json
from IconFinder import IconFinder
import time
from streak_helper import *
from habitdb_streak_finder import *
from utilities import *
import datetime
import re
import math
import subprocess

import habit_helper

# ── Relay file (shared with Android app) ────────────────────────────────────
SCREENS_RELAY_FILE = '/home/twain/noteVault/tail/screens_layout.json'

def load_screens_layout():
    """
    Reads screens_layout.json and returns a tuple:
      (screens, habit_icons)
    where screens is a list of screen dicts:
      [{"id": ..., "name": ..., "habits": [...]}, ...]
    and habit_icons is a dict of {habit_name: icon_name} overrides.
    Falls back to a single screen with the legacy flat habit list if the file
    is missing or malformed.
    """
    try:
        with open(SCREENS_RELAY_FILE, 'r') as f:
            data = json.load(f)
        screens = data.get('screens', [])
        habit_icons = data.get('habit_icons', {})
        if screens:
            return screens, habit_icons
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    # Fallback: single screen with the legacy order, no icon overrides
    return [{"id": "general", "name": "general", "habits": LEGACY_HABIT_ORDER}], {}

# Legacy flat order — used only when screens_layout.json is absent/empty
LEGACY_HABIT_ORDER = [
    'Juggle lights', 'Unique juggle', 'Juggling record broke', 'Dream acted',
    'Sleep watch', 'Apnea walked', 'Cold Shower Widget', 'Programming sessions',
    'Book read', 'Fiction Book Intake', 'Joggle', 'Create juggle', 'Fun juggle',
    'Drm Review', 'Early phone', 'Apnea practiced', 'Launch Squats Widget',
    'Juggling tech sessions', 'Podcast finished', 'Fiction Video Intake',
    'Blind juggle', 'Song juggle', 'Janki used', 'Lucidity trained',
    'Anki created', 'Apnea apb', 'Launch Situps Widget', 'Writing sessions',
    'Educational video watched', 'Chess', 'Juggling Balls Carry', 'Move juggle',
    'Filmed juggle', 'Unusual experience', 'Anki mydis done', 'Apnea spb',
    'Launch Pushups Widget', 'UC post', 'Article read', 'Rabbit Hole',
    'Juggling Others Learn', 'Juggle run', 'Watch juggle', 'Meditations',
    'Some anki', 'Lung stretch', 'Cardio sessions', 'AI tool', 'Read academic',
    'Speak AI', 'Most Collisions', 'Free', 'Inspired juggle', 'Kind stranger',
    'Health learned', 'Sweat', 'Good posture', 'Drew', 'Language studied',
    'Communication Improved', 'No Coffee', 'Magic practiced', 'Juggle goal',
    'Broke record', 'Took pills', 'Fasted', 'HIT', 'Question asked',
    'Music listen', 'Unusually Kind', 'Tracked Sleep', 'Magic performed',
    'Balanced', 'Grumpy blocker', 'Flossed', 'Todos done', 'Fresh air',
    'Talk stranger', 'Memory practice'
]

with open('/home/twain/Projects/py_habits_widget/obsidian_dir.txt', 'r') as f:
    obsidian_dir = f.read().strip()

def notify(message):
    msg = "notify-send ' ' '"+message+"'"
    os.system(msg)

class ButtonWithCheckbox(QWidget):
    def __init__(self, activity, left_number, current_values, all_time_high_values, right_number, parent=None):
        super().__init__(parent)
        self.activity = activity
        self.button = NumberedButton(left_number, current_values, all_time_high_values, right_number, self)
        self.checkbox = QCheckBox(self)
        self.checkbox.setFixedSize(24, 24)

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.button, 0, 0, Qt.AlignLeft)
        self.layout.addWidget(self.checkbox, 0, 0, Qt.AlignTop | Qt.AlignRight)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

class NumberedButton(QPushButton):
    def __init__(self, left_number, current_values, all_time_high_values, right_number, *args, **kwargs):
        super(NumberedButton, self).__init__(*args, **kwargs)
        self.left_number = left_number
        self.upper_left_number = int(all_time_high_values["day"][1])
        self.right_number = right_number
        self.setToolTip(f'<nobr><font size="4">{args[0].activity}<br>Current streak/antistreak: {self.left_number}<br>'
                        f'Longest streak: {self.right_number}<br>'
                        f'(current) All time high - date:<br>'
                        f'day: ({current_values["day"]}) {all_time_high_values["day"][1]} - {all_time_high_values["day"][0]}<br>'
                        f'week: ({current_values["week"]}) {all_time_high_values["week"][1]} - {all_time_high_values["week"][0]}<br>'
                        f'month: ({current_values["month"]}) {all_time_high_values["month"][1]} - {all_time_high_values["month"][0]}<br>'
                        f'year: ({current_values["year"]}) {all_time_high_values["year"][1]} - {all_time_high_values["year"][0]}<br></font></nobr>')

    def paintEvent(self, event):
        super(NumberedButton, self).paintEvent(event)
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 10))
        right_number_text = str(self.right_number)
        metrics = painter.fontMetrics()
        right_text_width = metrics.horizontalAdvance(right_number_text)
        painter.drawText(3, 95, str(self.left_number))
        painter.drawText(3, 18, str(self.upper_left_number))
        painter.drawText(95 - right_text_width, 95, right_number_text)

class ClickableLabel(QLabel):
    def mousePressEvent(self, event):
        checked_activities = [button.activity for button in self.parent().button_with_checkboxes if button.checkbox.isChecked()]
        self.create_graph(checked_activities)

    def create_graph(self, checked_activities):
        current_date_streak, current_date_antistreak, longest_streak_record, longest_antistreak_record, highest_net_streak_record, lowest_net_streak_record, week_average, month_average, year_average, overall_average = get_streak_numbers(True, checked_activities)


# ── Per-screen habit grid ────────────────────────────────────────────────────

class ScreenGrid(QWidget):
    """
    A single screen (tab) of habit buttons.  Mirrors one entry from screens_layout.json.
    The habits list is in row-major order (left-to-right, top-to-bottom), matching Android.
    """
    def __init__(self, screen_name, habit_names, habitsdb, habitsdb_to_add, parent_grid, habit_icon_overrides=None):
        super().__init__()
        self.screen_name = screen_name
        self.habit_names = habit_names   # ordered list in row-major order, may contain "" placeholders
        self.habitsdb = habitsdb
        self.habitsdb_to_add = habitsdb_to_add
        self.parent_grid = parent_grid   # reference to IconGrid for increment_habit
        self.habit_icon_overrides = habit_icon_overrides or {}  # {habit_name: icon_name}
        self.button_with_checkboxes = []
        self._build_grid()

    def _resolve_icon(self, activity):
        """Return the icon name for an activity, respecting overrides from the relay file."""
        if activity in self.habit_icon_overrides:
            return self.habit_icon_overrides[activity]
        icon_finder = IconFinder()
        return icon_finder.find_icon(activity)

    def _build_grid(self):
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(0)
        self.setLayout(grid_layout)

        num_columns = 8
        num_rows = 10
        index = 0

        # habits list is row-major: index = row * num_columns + col
        # so we iterate row-first (outer=row, inner=col) to place left-to-right
        for row in range(num_rows):
            for col in range(num_columns):
                if index < len(self.habit_names):
                    activity = self.habit_names[index]
                    if activity and activity in self.habitsdb:
                        inner_dict = self.habitsdb[activity]
                        days_since_not_zero = get_days_since_not_zero(inner_dict)
                        days_since_zero = get_days_since_zero(inner_dict)
                        left_number = -days_since_not_zero
                        if days_since_not_zero < 2:
                            days_since_zero = get_days_since_zero_minus(inner_dict)
                            left_number = days_since_zero

                        current_values = {}
                        current_values["day"] = inner_dict[list(inner_dict.keys())[-1]]
                        current_values["week"] = get_average_of_last_n_days(inner_dict, 7)
                        current_values["month"] = get_average_of_last_n_days(inner_dict, 30)
                        current_values["year"] = get_average_of_last_n_days(inner_dict, 365)

                        all_time_high_values = {}
                        all_time_high_values["day"] = get_all_time_high_rolling(inner_dict, 1)
                        all_time_high_values["week"] = get_all_time_high_rolling(inner_dict, 7)
                        all_time_high_values["month"] = get_all_time_high_rolling(inner_dict, 30)
                        all_time_high_values["year"] = get_all_time_high_rolling(inner_dict, 365)
                        right_number = get_longest_streak(inner_dict)

                        last_value_from_habitsdb = list(inner_dict.values())[-1]
                        value_from_habitsdb_to_add = self.habitsdb_to_add.get(activity, 0)
                        last_value = last_value_from_habitsdb + value_from_habitsdb_to_add

                        if "Pushups" in activity:
                            last_value = math.floor(last_value / 30 + 0.5)
                        elif "Situps" in activity:
                            last_value = math.floor(last_value / 50 + 0.5)
                        elif "Squats" in activity:
                            last_value = math.floor(last_value / 30 + 0.5)
                        elif "Sweat" in activity:
                            last_value = math.floor(last_value / 15 + 0.5)
                        elif "Cold Shower" in activity:
                            if last_value > 0 and last_value < 3:
                                last_value = 3
                            last_value = math.floor(last_value / 3 + 0.5)
                        last_value = math.floor(last_value + 0.5)

                        icon_folder = 'redgoldpainthd'
                        if last_value == 1:
                            icon_folder = 'orangewhitepearlhd'
                        elif last_value == 2:
                            icon_folder = 'greenfloralhd'
                        elif last_value == 3:
                            icon_folder = 'bluewhitepearlhd'
                        elif last_value == 4:
                            icon_folder = 'pinkorbhd'
                        elif last_value == 5:
                            icon_folder = 'yellowpainthd'
                        elif last_value > 5:
                            icon_folder = 'transparentglasshd'

                        icon_dir = os.path.expanduser('~/Projects/py_habits_widget/icons/' + icon_folder + '/')
                        icon = self._resolve_icon(activity)
                        icon_file = icon + '.png'
                        icon_path = icon_dir + icon_file

                        button_with_checkbox = ButtonWithCheckbox(
                            activity, left_number, current_values, all_time_high_values, right_number, self
                        )
                        button_with_checkbox.button.setIcon(QIcon(icon_path))
                        button_with_checkbox.button.setIconSize(QSize(100, 100))
                        button_with_checkbox.button.setFixedSize(100, 100)
                        button_with_checkbox.button.clicked.connect(
                            lambda checked, a=activity: self.parent_grid.increment_habit(a)
                        )
                        button_with_checkbox.button.setFocusPolicy(Qt.NoFocus)
                        grid_layout.addWidget(button_with_checkbox, row, col)
                        self.button_with_checkboxes.append(button_with_checkbox)
                    else:
                        # Empty placeholder cell (activity name is "" or not in habitsdb)
                        spacer = QSpacerItem(100, 100, QSizePolicy.Fixed, QSizePolicy.Fixed)
                        grid_layout.addItem(spacer, row, col)
                else:
                    # Index beyond the habits list — fill with empty spacer
                    spacer = QSpacerItem(100, 100, QSizePolicy.Fixed, QSizePolicy.Fixed)
                    grid_layout.addItem(spacer, row, col)
                index += 1

    def update_icons(self, habitsdb, habitsdb_to_add, habit_icon_overrides=None):
        """Refresh icon images after an increment (no layout rebuild needed)."""
        self.habitsdb = habitsdb
        self.habitsdb_to_add = habitsdb_to_add
        if habit_icon_overrides is not None:
            self.habit_icon_overrides = habit_icon_overrides
        button_index = 0
        for activity in self.habit_names:
            if not activity or activity not in habitsdb:
                continue
            if button_index >= len(self.button_with_checkboxes):
                break
            inner_dict = habitsdb[activity]
            last_value_from_habitsdb = list(inner_dict.values())[-1]
            value_from_habitsdb_to_add = habitsdb_to_add.get(activity, 0)
            last_value = last_value_from_habitsdb + value_from_habitsdb_to_add

            if "Pushups" in activity:
                last_value = math.floor(last_value / 30 + 0.5)
            elif "Situps" in activity:
                last_value = math.floor(last_value / 50 + 0.5)
            elif "Squats" in activity:
                last_value = math.floor(last_value / 30 + 0.5)
            elif "Sweat" in activity:
                last_value = math.floor(last_value / 15 + 0.5)
            elif "Cold Shower" in activity:
                if last_value > 0 and last_value < 3:
                    last_value = 3
                last_value = math.floor(last_value / 3 + 0.5)
            last_value = math.floor(last_value + 0.5)

            icon_folder = 'redgoldpainthd'
            if last_value == 1:
                icon_folder = 'orangewhitepearlhd'
            elif last_value == 2:
                icon_folder = 'greenfloralhd'
            elif last_value == 3:
                icon_folder = 'bluewhitepearlhd'
            elif last_value == 4:
                icon_folder = 'pinkorbhd'
            elif last_value == 5:
                icon_folder = 'yellowpainthd'
            elif last_value > 5:
                icon_folder = 'transparentglasshd'

            icon_dir = os.path.expanduser('~/Projects/py_habits_widget/icons/' + icon_folder + '/')
            icon = self._resolve_icon(activity)
            icon_file = icon + '.png'
            icon_path = icon_dir + icon_file
            self.button_with_checkboxes[button_index].button.setIcon(QIcon(icon_path))
            button_index += 1


# ── Main window ──────────────────────────────────────────────────────────────

class IconGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.button_with_checkboxes = []  # flat list across all screens (for ClickableLabel)
        self.screen_grids = []            # list of ScreenGrid widgets
        self.init_ui()

    def _load_data(self):
        """Load the unified habit database and pending increments."""
        habitsdb = make_json(obsidian_dir + 'habitsdb.txt')
        habitsdb_to_add = make_json(obsidian_dir + 'habitsdb_to_add.txt')
        return habitsdb, habitsdb_to_add

    def init_ui(self):
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        self.setLayout(outer_layout)

        # ── Top bar: total label + wallpaper + refresh ───────────────────────
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 2, 4, 2)
        outer_layout.addLayout(top_bar)

        self.total_label = ClickableLabel()
        self.total_label.setParent(self)
        top_bar.addWidget(self.total_label)

        top_bar.addStretch()

        wallpaper_button = QPushButton()
        wallpaper_button.setIcon(QIcon.fromTheme('preferences-desktop-wallpaper'))
        wallpaper_button.setFixedSize(32, 32)
        wallpaper_button.setToolTip('Open Wallpaper Color Manager')
        wallpaper_button.clicked.connect(self.open_wallpaper_control_panel)
        top_bar.addWidget(wallpaper_button)

        refresh_button = QPushButton()
        refresh_button.setIcon(QIcon.fromTheme('view-refresh'))
        refresh_button.setFixedSize(32, 32)
        refresh_button.clicked.connect(self.refresh_widget)
        top_bar.addWidget(refresh_button)

        # ── Tab widget for screens ───────────────────────────────────────────
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        # Each screen is 8 cols × 10 rows of 100×100 buttons = 800×1000px.
        # Fix the tab widget to exactly that size so the window doesn't balloon.
        self.tab_widget.setFixedSize(800, 1000)
        outer_layout.addWidget(self.tab_widget)

        self._rebuild_tabs()

        self.update_total()

        self.setWindowTitle('Habit Tracker Widget')
        icon_path = '/home/twain/Projects/py_habits_widget/icons/blue_icon.png'
        self.setWindowIcon(QIcon(icon_path))
        self.adjustSize()
        self.show()

    def _rebuild_tabs(self):
        """Clear and rebuild all screen tabs from screens_layout.json."""
        self.tab_widget.clear()
        self.screen_grids.clear()
        self.button_with_checkboxes.clear()

        habitsdb, habitsdb_to_add = self._load_data()
        screens, habit_icons = load_screens_layout()

        for screen in screens:
            screen_name = screen.get('name', 'screen')
            habit_names = screen.get('habits', [])
            sg = ScreenGrid(screen_name, habit_names, habitsdb, habitsdb_to_add, self,
                            habit_icon_overrides=habit_icons)
            self.screen_grids.append(sg)
            self.tab_widget.addTab(sg, screen_name)
            # Accumulate all buttons for the ClickableLabel graph feature
            self.button_with_checkboxes.extend(sg.button_with_checkboxes)

    def increment_habit(self, argument):
        write_updated_habitsdb_to_add = False
        write_updated_personal_records = False
        habitsdb_to_add_dir = obsidian_dir + 'habitsdb_to_add.txt'
        habitsdb_to_add = make_json(habitsdb_to_add_dir)
        if "Widget" in argument:
            value, ok = QInputDialog.getInt(self, 'Input Dialog', f'Enter the increment for {argument}:', min=1)
            if ok:
                habitsdb_to_add[argument] += value
                write_updated_habitsdb_to_add = True
        elif "Broke record" in argument or "Apnea spb" in argument:
            personal_records_dir = obsidian_dir + 'tail/personal_records.txt'
            if "Apnea spb" in argument:
                personal_records_dir = obsidian_dir + 'tail/apnea_records.txt'
            personal_records = make_json(personal_records_dir)

            dialog = QDialog(self)
            dialog.setWindowTitle("Select an item")
            layout = QVBoxLayout()

            combo = QComboBox()
            keys_with_days = []
            for key in personal_records:
                record_dates = personal_records[key]["records"]
                if record_dates:
                    latest_date = max(record_dates, key=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
                    days_since_last_record = (datetime.date.today() - datetime.datetime.strptime(latest_date, '%Y-%m-%d').date()).days
                    display_text = f"{key} ({days_since_last_record} days ago)"
                else:
                    display_text = f"{key} (x)"
                keys_with_days.append(display_text)
            combo.addItems(keys_with_days)

            layout.addWidget(combo)
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(dialog.accept)
            layout.addWidget(ok_button)
            dialog.setLayout(layout)

            result = dialog.exec_()
            if result == QDialog.Accepted:
                selected_key = combo.currentText()
                selected_key = re.sub(r'\s*\([^)]*\)', '', selected_key).rstrip()
                selected_item = personal_records[selected_key]

                description = selected_item["description"]
                if selected_item["records"]:
                    latest_date = max(selected_item["records"], key=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
                    latest_value = selected_item["records"][latest_date]
                    description += f'\nMost recent record: {latest_date} - {latest_value}'
                value, ok = QInputDialog.getText(self, 'Input Dialog', f'{description}\nEnter the value for {selected_key}:')

                if ok:
                    selected_item["records"][str(datetime.date.today())] = value
                    write_updated_personal_records = True
                    habitsdb_to_add[argument] += 1
                    write_updated_habitsdb_to_add = True
                else:
                    write_updated_personal_records = False
            else:
                write_updated_personal_records = False
        else:
            habitsdb_to_add[argument] += 1
            write_updated_habitsdb_to_add = True

        if write_updated_habitsdb_to_add:
            result = "Pending habits\n"
            for key, value in habitsdb_to_add.items():
                if value > 0:
                    result += f"{key}: {value}\n"
            notify(result)
            habitsdb_to_add_dir = os.path.expanduser(habitsdb_to_add_dir)
            with open(habitsdb_to_add_dir, 'w') as f:
                json.dump(habitsdb_to_add, f, indent=4, sort_keys=True)
            time.sleep(1)
            update_theme_script = '~/Projects/tail/habits_kde_theme.py'
            update_theme_script = os.path.expanduser(update_theme_script)
            os.system('python3 ' + update_theme_script)
            self.update_icons()
            self.update_total()
        if write_updated_personal_records:
            personal_records_dir = os.path.expanduser(personal_records_dir)
            with open(personal_records_dir, 'w') as f:
                json.dump(personal_records, f, indent=4, sort_keys=True)

    def refresh_widget(self):
        subprocess.run(['pkill', '-f', 'habits_kde_theme_watchdog_phone.sh'])
        startup_script = '/home/twain/Projects/tail/habits_kde_theme_watchdog_phone.sh'
        subprocess.Popen(['bash', startup_script])
        self.close()
        sys.exit(0)

    def open_wallpaper_control_panel(self):
        wallpaper_control_panel = '/home/twain/Projects/tail/wallpaper_color_manager_new/color_control_panel.py'
        subprocess.Popen(['python3', wallpaper_control_panel])

    def update_icons(self):
        """Refresh icon images on all screen tabs after an increment."""
        habitsdb, habitsdb_to_add = self._load_data()
        # Re-read icon overrides in case they changed (e.g. relay file updated)
        _, habit_icons = load_screens_layout()
        for sg in self.screen_grids:
            sg.update_icons(habitsdb, habitsdb_to_add, habit_icon_overrides=habit_icons)

    def get_icons_and_scripts(self):
        """
        Returns a flat list of icon data tuples for all habits across all screens,
        used by update_total() for today's count calculation.
        """
        habitsdb, habitsdb_to_add = self._load_data()
        screens, _habit_icons = load_screens_layout()
        # Collect unique habit names across all screens (preserve order, skip duplicates/empty)
        seen = set()
        all_habits = []
        for screen in screens:
            for h in screen.get('habits', []):
                if h and h not in seen:
                    seen.add(h)
                    all_habits.append(h)

        icons_and_scripts = []
        total_right_number = 0
        for activity in all_habits:
            if activity in habitsdb:
                inner_dict = habitsdb[activity]
                days_since_not_zero = get_days_since_not_zero(inner_dict)
                days_since_zero = get_days_since_zero(inner_dict)
                left_number = -days_since_not_zero
                if days_since_not_zero < 2:
                    days_since_zero = get_days_since_zero_minus(inner_dict)
                    left_number = days_since_zero

                current_values = {}
                current_values["day"] = inner_dict[list(inner_dict.keys())[-1]]
                current_values["week"] = get_average_of_last_n_days(inner_dict, 7)
                current_values["month"] = get_average_of_last_n_days(inner_dict, 30)
                current_values["year"] = get_average_of_last_n_days(inner_dict, 365)

                all_time_high_values = {}
                all_time_high_values["day"] = get_all_time_high_rolling(inner_dict, 1)
                all_time_high_values["week"] = get_all_time_high_rolling(inner_dict, 7)
                all_time_high_values["month"] = get_all_time_high_rolling(inner_dict, 30)
                all_time_high_values["year"] = get_all_time_high_rolling(inner_dict, 365)
                right_number = get_longest_streak(inner_dict)
                total_right_number += right_number

                last_value_from_habitsdb = list(inner_dict.values())[-1]
                value_from_habitsdb_to_add = habitsdb_to_add.get(activity, 0)
                last_value = last_value_from_habitsdb + value_from_habitsdb_to_add

                icon_folder = 'redgoldpainthd'
                icon_dir = os.path.expanduser('~/Projects/py_habits_widget/icons/' + icon_folder + '/')
                icon_finder = IconFinder()
                icon = icon_finder.find_icon(activity)
                icon_file = icon + '.png'
                icons_and_scripts.append((icon_dir + icon_file, activity, activity, left_number, current_values, all_time_high_values, right_number))
            else:
                icons_and_scripts.append(None)

        print("total_right_number", total_right_number)
        return icons_and_scripts

    def update_total(self):
        icons_and_scripts = self.get_icons_and_scripts()
        today_total = 0

        # Compute week/month averages directly from the unified habitsdb
        week_avg = 0
        month_avg = 0
        last_7_days_total, last_30_days_total = 0, 0
        days_counted_week, days_counted_month = 0, 0

        habitsdb, habitsdb_to_add = self._load_data()

        for item in icons_and_scripts:
            if item is not None:
                icon, arg, activity, left_number, current_values, all_time_high_values, right_number = item

                if arg in habitsdb:
                    inner_dict = habitsdb[arg]
                    sorted_dates = sorted(inner_dict.keys(), reverse=True)
                    if sorted_dates:
                        current_habit_today = inner_dict[sorted_dates[0]] + habitsdb_to_add.get(arg, 0)
                        today_total += habit_helper.adjust_habit_count(current_habit_today, arg)

                if arg in habitsdb:
                    inner_dict = habitsdb[arg]
                    sorted_dates = sorted(inner_dict.keys(), reverse=True)
                    current_date = datetime.datetime.now().date()
                    seven_days_ago = current_date - datetime.timedelta(days=7)
                    thirty_days_ago = current_date - datetime.timedelta(days=30)

                    last_7_days_count = 0
                    activity_days_week = set()
                    for date_str in sorted_dates:
                        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        if date_obj >= seven_days_ago and date_obj <= current_date:
                            last_7_days_count += habit_helper.adjust_habit_count(inner_dict[date_str], arg)
                            activity_days_week.add(date_str)
                    last_7_days_total += last_7_days_count
                    days_counted_week = max(days_counted_week, len(activity_days_week))

                    last_30_days_count = 0
                    activity_days_month = set()
                    for date_str in sorted_dates:
                        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        if date_obj >= thirty_days_ago and date_obj <= current_date:
                            last_30_days_count += habit_helper.adjust_habit_count(inner_dict[date_str], arg)
                            activity_days_month.add(date_str)
                    last_30_days_total += last_30_days_count
                    days_counted_month = max(days_counted_month, len(activity_days_month))

        current_date_streak, current_date_antistreak, longest_streak_record, longest_antistreak_record, highest_net_streak_record, lowest_net_streak_record, week_average, month_average, year_average, overall_average = get_streak_numbers(False, [])

        net_streak = current_date_streak - current_date_antistreak
        streak_text = f"{net_streak}:{lowest_net_streak_record}:{highest_net_streak_record}\ns {current_date_streak}:{longest_streak_record}\nas {current_date_antistreak}:{longest_antistreak_record}\n"

        week_avg = last_7_days_total / min(max(days_counted_week, 1), 7)
        month_avg = last_30_days_total / min(max(days_counted_month, 1), 30)

        self.total_label.setText(f"{streak_text}{today_total}|{week_avg:.1f}|{month_avg:.1f}\n{week_average[-1]:.1f}|{month_average[-1]:.1f}|{year_average[-1]:.1f}|{overall_average[-1]:.1f}")

        streaks_dir = os.path.expanduser(obsidian_dir + '/tail/streaks.txt')
        last_7_days_average = math.floor(week_avg * 10 + 0.5) / 10
        last_30_days_average = math.floor(month_avg * 10 + 0.5) / 10
        with open(streaks_dir, 'w') as f:
            json.dump({"net_streak": net_streak, "highest_net_streak_record": highest_net_streak_record, "lowest_net_streak_record": lowest_net_streak_record, "current_streak": current_date_streak, "longest_streak": longest_streak_record, "current_antistreak": current_date_antistreak, "longest_antistreak": longest_antistreak_record, "today_total": today_total, "last_7_days_average": last_7_days_average, "last_30_days_average": last_30_days_average, "week_average": int(week_average[-1]), "month_average": int(month_average[-1]), "year_average": int(year_average[-1]), "overall_average": int(overall_average[-1])}, f, indent=4, sort_keys=True)


def get_icon_image_based_on_theme(current_theme):
    if current_theme == "Moe-Dark":
        icon_path = '/home/twain/Projects/py_habits_widget/icons/Screenshot_20231124_181238.png'
    elif current_theme == "E5150-Orange":
        icon_path = '/home/twain/Projects/py_habits_widget/icons/Screenshot_20231124_181238.png'
    elif current_theme == "spectrum-mawsitsit":
        icon_path = '/home/twain/Projects/py_habits_widget/icons/Screenshot_20231217_084422.png'
    elif current_theme == "Shadows-Global":
        icon_path = '/home/twain/Projects/py_habits_widget/icons/Screenshot_20231203_091003.png'
    elif current_theme == "spectrum-strawberryquartz":
        icon_path = '/home/twain/Projects/py_habits_widget/icons/Screenshot_20231124_181238.png'
    elif current_theme == "Neon-Knights-Yellow":
        icon_path = '/home/twain/Projects/py_habits_widget/icons/Screenshot_20231124_234618.png'
    elif current_theme == "Glassy":
        icon_path = '/home/twain/Projects/py_habits_widget/icons/Screenshot_20231124_181238.png'
    return icon_path


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("py_habits_widget")
    app.setApplicationDisplayName("Habit Tracker Widget")
    app.setDesktopFileName("py_habits_widget.desktop")

    icon_path = '/home/twain/Projects/py_habits_widget/icons/blue_icon.png'
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    icon_grid = IconGrid()
    icon_grid.setWindowIcon(app_icon)
    icon_grid.setWindowTitle('Habit Tracker Widget')
    icon_grid.setProperty("WM_CLASS", "py_habits_widget")

    sys.exit(app.exec_())
