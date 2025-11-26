import sys
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QSpacerItem, QSizePolicy, QInputDialog, QLabel, QComboBox, QDialog, QVBoxLayout, QCheckBox
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

class ButtonWithCheckbox(QWidget):
    def __init__(self, activity, left_number, current_values, all_time_high_values, right_number, parent=None):
        super().__init__(parent)
        self.activity = activity
        self.button = NumberedButton(left_number, current_values, all_time_high_values, right_number, self)
        self.checkbox = QCheckBox(self)
        self.checkbox.setFixedSize(24,24)  # Adjust the size of the checkbox as needed

        # Create a grid layout
        self.layout = QGridLayout(self)
        self.layout.addWidget(self.button, 0, 0, Qt.AlignLeft)
        self.layout.addWidget(self.checkbox, 0, 0, Qt.AlignTop | Qt.AlignRight)

        # Remove margins and spacing
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

with open('/home/twain/Projects/py_habits_widget/obsidian_dir.txt', 'r') as f:
    obsidian_dir = f.read().strip()

def notify(message):
    msg = "notify-send ' ' '"+message+"'"
    os.system(msg)
    
class NumberedButton(QPushButton):
    def __init__(self, left_number, current_values, all_time_high_values, right_number, *args, **kwargs):
        super(NumberedButton, self).__init__(*args, **kwargs)
        self.left_number = left_number
        self.upper_left_number = int(all_time_high_values["day"][1])
        self.right_number = right_number
        # Set the tooltip with HTML tags to make the text bigger
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
        # Calculate text width for right alignment
        right_number_text = str(self.right_number)
        metrics = painter.fontMetrics()
        right_text_width = metrics.horizontalAdvance(right_number_text)
        
        # Position numbers with proper margins - adjusted for 100x100 button size
        painter.drawText(3, 95, str(self.left_number))  # Bottom left
        painter.drawText(3, 18, str(self.upper_left_number))  # Top left
        painter.drawText(95 - right_text_width, 95, right_number_text)  # Bottom right, properly aligned

class ClickableLabel(QLabel):
    def mousePressEvent(self, event):
        checked_activities = [button.activity for button in self.parent().button_with_checkboxes if button.checkbox.isChecked()]
        self.create_graph(checked_activities)

    def create_graph(self, checked_activities):
        current_date_streak, current_date_antistreak, longest_streak_record, longest_antistreak_record, highest_net_streak_record, lowest_net_streak_record, week_average, month_average, year_average, overall_average = get_streak_numbers(True, checked_activities)

class IconGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.button_with_checkboxes = []
        self.init_ui()

    def get_icons_and_scripts(self):   
        
        activities = [ 
            'Juggle lights', 'Unique juggle', 'Juggling record broke', 'Dream acted', 'Sleep watch', 'Apnea walked', 'Cold Shower Widget', 'Programming sessions', 'Book read', 'Fiction Book Intake', 'Joggle', 'Create juggle', 'Fun juggle', 'Drm Review',  'Early phone', 'Apnea practiced', 'Launch Squats Widget', 'Juggling tech sessions', 'Podcast finished', 'Fiction Video Intake', 'Blind juggle', 'Song juggle', 'Janki used', 'Lucidity trained', 'Anki created', 'Apnea apb', 'Launch Situps Widget', 'Writing sessions', 'Educational video watched', 'Chess', 'Juggling Balls Carry', 'Move juggle', 'Filmed juggle', 'Unusual experience', 'Anki mydis done', 'Apnea spb', 'Launch Pushups Widget', 'UC post', 'Article read', 'Rabbit Hole', 'Juggling Others Learn', 'Juggle run', 'Watch juggle', 'Meditations', 'Some anki', 'Lung stretch', 'Cardio sessions', 'AI tool', 'Read academic', 'Speak AI', 'Most Collisions', 'Free', 'Inspired juggle', 'Kind stranger', 'Health learned', 'Sweat', 'Good posture',  'Drew', 'Language studied', 'Communication Improved', 'No Coffee', 'Magic practiced', 'Juggle goal', 'Broke record',  'Took pills', 'Fasted', 'HIT', 'Question asked', 'Music listen', 'Unusually Kind', 'Tracked Sleep', 'Magic performed',  'Balanced', 'Grumpy blocker', 'Flossed', 'Todos done', 'Fresh air', 'Talk stranger', 'Memory practice'
            ]

        # Load both habitsdb files and merge them for streak calculations
        habitsdb = make_json(obsidian_dir+'habitsdb.txt')
        habitsdb_phone = make_json(obsidian_dir+'habitsdb_phone.txt')
        
        # Merge habitsdb_phone into habitsdb
        for habit, dates in habitsdb_phone.items():
            if habit not in habitsdb:
                habitsdb[habit] = {}
            habitsdb[habit].update(dates)

        habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt')

        icons_and_scripts = []

        total_right_number = 0

        for i in range(len(activities)):
            if activities[i] in habitsdb:
                inner_dict = habitsdb[activities[i]]
                days_since_not_zero = get_days_since_not_zero(inner_dict)
                days_since_zero = get_days_since_zero(inner_dict)
                left_number = -days_since_not_zero
                if days_since_not_zero < 2:
                    days_since_zero = get_days_since_zero_minus(inner_dict)
                    left_number = days_since_zero
                
                current_values = {}
                
                # For day value, use the most recent entry from merged data
                current_values["day"] = inner_dict[list(inner_dict.keys())[-1]]
                
                # For week and month averages, use phone data if available
                if activities[i] in habitsdb_phone:
                    phone_inner_dict = habitsdb_phone[activities[i]]
                    current_values["week"] = get_average_of_last_n_days(phone_inner_dict, 7)
                    current_values["month"] = get_average_of_last_n_days(phone_inner_dict, 30)
                else:
                    # Fall back to merged data if not in phone data
                    current_values["week"] = get_average_of_last_n_days(inner_dict, 7)
                    current_values["month"] = get_average_of_last_n_days(inner_dict, 30)
                
                # For year average, use merged data
                current_values["year"] = get_average_of_last_n_days(inner_dict, 365)

                all_time_high_values={}
                all_time_high_values["day"] = get_all_time_high_rolling(inner_dict, 1)
                all_time_high_values["week"] = get_all_time_high_rolling(inner_dict, 7)
                all_time_high_values["month"] = get_all_time_high_rolling(inner_dict, 30)
                all_time_high_values["year"] = get_all_time_high_rolling(inner_dict, 365)
                right_number = longest_streak = get_longest_streak(inner_dict)
                total_right_number += right_number
                last_value_from_habitsdb = list(inner_dict.values())[-1]
                value_from_habitsdb_to_add = habitsdb_to_add[activities[i]]
                last_value = last_value_from_habitsdb + value_from_habitsdb_to_add
                #print(activities[i], last_value)
                if "Pushups" in activities[i]:
                    last_value = math.floor(last_value/30 + 0.5)
                elif "Situps" in activities[i]:
                    last_value = math.floor(last_value/50 + 0.5)
                elif "Squats" in activities[i]:
                    last_value = math.floor(last_value/30 + 0.5)
                elif "Sweat" in activities[i]:
                    last_value = math.floor(last_value/15 + 0.5)
                elif "Cold Shower" in activities[i]:
                    if last_value > 0 and last_value < 3:
                        last_value = 3
                    last_value = math.floor(last_value/3 + 0.5)

                #print(activities[i], last_value)
                #round last_value
                last_value = math.floor(last_value + 0.5)
                #print(activities[i], last_value)

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

                icon_dir = '~/Projects/py_habits_widget/icons/'+icon_folder+'/'
                icon_dir = os.path.expanduser(icon_dir)
                icon_finder = IconFinder()
                icon = icon_finder.find_icon(activities[i])
                icon_file = icon + '.png'
                
                icons_and_scripts.append((icon_dir + icon_file, activities[i], activities[i], left_number, current_values, all_time_high_values, right_number))

            else:
                icons_and_scripts.append(None)
        print("total_right_number", total_right_number)
        return icons_and_scripts





    # In your init_ui method
    def init_ui(self):
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        icons_and_scripts = self.get_icons_and_scripts()
        num_columns, num_rows, index = 8, 10, 0
        #self.button_with_checkboxes = []

        self.total_label = ClickableLabel()
        grid_layout.addWidget(self.total_label, 0, num_columns)
        
        # Add refresh button
        refresh_button = QPushButton()
        refresh_button.setIcon(QIcon.fromTheme('view-refresh'))
        refresh_button.setFixedSize(32, 32)
        refresh_button.clicked.connect(self.refresh_widget)
        grid_layout.addWidget(refresh_button, 0, num_columns - 1)
        
        # Add wallpaper control panel button
        wallpaper_button = QPushButton()
        wallpaper_button.setIcon(QIcon.fromTheme('preferences-desktop-wallpaper'))
        wallpaper_button.setFixedSize(32, 32)
        wallpaper_button.setToolTip('Open Wallpaper Color Manager')
        wallpaper_button.clicked.connect(self.open_wallpaper_control_panel)
        grid_layout.addWidget(wallpaper_button, 0, num_columns - 2)
        
        self.update_total()

        for col in range(num_columns):
            for row in range(1, num_rows + 1):
                if index < len(icons_and_scripts):
                    if icons_and_scripts[index] is not None:
                        icon, arg, activity, left_number, current_values, all_time_high_values, right_number = icons_and_scripts[index]
                        button_with_checkbox = ButtonWithCheckbox(activity, left_number, current_values, all_time_high_values, right_number, self)
                        button_with_checkbox.button.setIcon(QIcon(icon))
                        button_with_checkbox.button.setIconSize(QSize(100, 100))
                        button_with_checkbox.button.setFixedSize(100, 100)  # Force the button size
                        button_with_checkbox.button.clicked.connect(lambda checked, a=arg: self.increment_habit(a))
                        button_with_checkbox.button.setFocusPolicy(Qt.NoFocus)
                        grid_layout.addWidget(button_with_checkbox, row, col)
                        self.button_with_checkboxes.append(button_with_checkbox)
                    else:
                        spacer = QSpacerItem(100, 100, QSizePolicy.Fixed, QSizePolicy.Fixed)
                        grid_layout.addItem(spacer, row, col)
                index += 1
        self.setWindowTitle('Habit Tracker Widget')
        
        # Set the window icon explicitly
        icon_path = '/home/twain/Projects/py_habits_widget/icons/blue_icon.png'
        self.setWindowIcon(QIcon(icon_path))
        
        self.show()

    def increment_habit(self, argument):
        write_updated_habitsdb_to_add = False
        write_updated_personal_records = False
        habitsdb_to_add_dir = obsidian_dir+'habitsdb_to_add.txt'
        habitsdb_to_add = make_json(habitsdb_to_add_dir)
        if "Widget" in argument:
            value, ok = QInputDialog.getInt(self, 'Input Dialog', f'Enter the increment for {argument}:', min=1)
            if ok:
                habitsdb_to_add[argument] += value
                write_updated_habitsdb_to_add = True
        elif "Broke record" in argument or "Apnea spb" in argument:
            personal_records_dir = obsidian_dir+'tail/personal_records.txt'
            if "Apnea spb" in argument:
                personal_records_dir = obsidian_dir+'tail/apnea_records.txt'
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

            #combo.addItems(keys)
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
            os.system('python3 '+update_theme_script)
            self.update_icons()
            self.update_total()
        if write_updated_personal_records:
            personal_records_dir = os.path.expanduser(personal_records_dir)
            with open(personal_records_dir, 'w') as f:
                json.dump(personal_records, f, indent=4, sort_keys=True)

    def refresh_widget(self):
        # Kill any existing instance of the startup script
        subprocess.run(['pkill', '-f', 'habits_kde_theme_watchdog_phone.sh'])
        
        # Start a new instance of the startup script and exit this widget
        # (the startup script will handle restarting the widget)
        startup_script = '/home/twain/Projects/tail/habits_kde_theme_watchdog_phone.sh'
        subprocess.Popen(['bash', startup_script])
        
        # Exit current widget instance
        self.close()
        sys.exit(0)
        
    def open_wallpaper_control_panel(self):
        # Path to the wallpaper control panel program
        wallpaper_control_panel = '/home/twain/Projects/tail/wallpaper_color_manager_new/color_control_panel.py'
        
        # Run the wallpaper control panel program in a separate process
        subprocess.Popen(['python3', wallpaper_control_panel])

    def update_icons(self):
        print("Updating icons")
        icons_and_scripts = self.get_icons_and_scripts()
        button_index = 0
        for index, item in enumerate(icons_and_scripts):
            if item is not None:
                #print("item", item)
                icon, _, _, left_number, current_values, all_time_high_values, right_number = item
                self.button_with_checkboxes[button_index].button.setIcon(QIcon(icon))
                button_index += 1

    def update_total(self):
        icons_and_scripts = self.get_icons_and_scripts()
        today_total = 0

        # Read the total_habits.txt2 file to get the daily totals
        try:
            with open('/home/twain/noteVault/habitCounters/total_habits.txt2', 'r') as f:
                totals_str = f.read().strip()
                totals = [int(x) for x in totals_str.split(',')]
                
                # Calculate week and month averages from the totals file
                week_totals = totals[:7]  # First 7 values are the most recent
                month_totals = totals[:30]  # First 30 values are the most recent
                
                # Calculate the averages
                week_avg = sum(week_totals) / len(week_totals)
                month_avg = sum(month_totals) / len(month_totals)
                
                # Print debug information
                print(f"Week totals from file: {week_totals}")
                print(f"Week average from file: {week_avg:.2f}")
                print(f"Month totals from file: {month_totals[:7]}")  # Just show first 7 for brevity
                print(f"Month average from file: {month_avg:.2f}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error reading total_habits.txt2: {e}")
            # Fallback to old method if file can't be read
            week_avg = 0
            month_avg = 0
            
            # Initialize for fallback calculation
            last_7_days_total, last_30_days_total = 0, 0
            days_counted_week, days_counted_month = 0, 0

        # Still calculate today_total from the activities
        for item in icons_and_scripts:
            if item is not None:
                icon, arg, activity, left_number, current_values, all_time_high_values, right_number = item
                
                # For today's total, we need both habitsdb files and habitsdb_to_add
                habitsdb = make_json(obsidian_dir+'habitsdb.txt')
                habitsdb_phone = make_json(obsidian_dir+'habitsdb_phone.txt')
                
                # Merge habitsdb_phone into habitsdb
                if arg in habitsdb_phone:
                    if arg not in habitsdb:
                        habitsdb[arg] = {}
                    habitsdb[arg].update(habitsdb_phone[arg])
                
                habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt')
                
                if arg in habitsdb:
                    inner_dict = habitsdb[arg]
                    sorted_dates = sorted(inner_dict.keys(), reverse=True)
                    if sorted_dates:
                        current_habit_today = inner_dict[sorted_dates[0]] + habitsdb_to_add[arg]
                        today_total += habit_helper.adjust_habit_count(current_habit_today, arg)
                
                # Only calculate these if we're using the fallback method
                if week_avg == 0 and month_avg == 0:
                    # Use only phone data for recent calculations
                    if arg in habitsdb_phone:
                        inner_dict = habitsdb_phone[arg]
                        sorted_dates = sorted(inner_dict.keys(), reverse=True)
                        
                        # Use a time-based approach for week and month calculations
                        current_date = datetime.datetime.now().date()
                        seven_days_ago = current_date - datetime.timedelta(days=7)
                        thirty_days_ago = current_date - datetime.timedelta(days=30)
                        
                        # Calculate last 7 days total
                        last_7_days_count = 0
                        activity_days_week = set()
                        for date_str in sorted_dates:
                            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                            if date_obj >= seven_days_ago and date_obj <= current_date:
                                last_7_days_count += habit_helper.adjust_habit_count(inner_dict[date_str], arg)
                                activity_days_week.add(date_str)
                        last_7_days_total += last_7_days_count
                        days_counted_week = max(days_counted_week, len(activity_days_week))
                        
                        # Calculate last 30 days total
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
        # If we're using the fallback method, calculate the averages
        if 'week_avg' not in locals() or week_avg == 0:
            # Calculate averages using actual days counted or default to 7/30 if no days counted
            # This ensures we don't artificially inflate averages when data is sparse
            week_avg = last_7_days_total / min(max(days_counted_week, 1), 7)
            month_avg = last_30_days_total / min(max(days_counted_month, 1), 30)
        
        self.total_label.setText(f"{streak_text}{today_total}|{week_avg:.1f}|{month_avg:.1f}\n{week_average[-1]:.1f}|{month_average[-1]:.1f}|{year_average[-1]:.1f}|{overall_average[-1]:.1f}")

        #write a json file that has net streak, current streak, longest streak, current antistreak, longest antistreak
        streaks_dir = os.path.expanduser(obsidian_dir+'/tail/streaks.txt')
        
        # Round the week and month averages to one decimal place
        last_7_days_average = math.floor(week_avg * 10 + 0.5) / 10
        last_30_days_average = math.floor(month_avg * 10 + 0.5) / 10
        with open(streaks_dir, 'w') as f:
            json.dump({"net_streak": net_streak, "highest_net_streak_record":highest_net_streak_record,"lowest_net_streak_record":lowest_net_streak_record,"current_streak": current_date_streak, "longest_streak": longest_streak_record, "current_antistreak": current_date_antistreak, "longest_antistreak": longest_antistreak_record,"today_total":today_total,"last_7_days_average":last_7_days_average,"last_30_days_average":last_30_days_average, "week_average":int(week_average[-1]), "month_average":int(month_average[-1]), "year_average":int(year_average[-1]),"overall_average":int(overall_average[-1]) }, f, indent=4, sort_keys=True)
            
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
    # else :
    #     icon_path = '/home/twain/Projects/py_habits_widget/icons/redgoldpainthd/Screenshot_20231124_181238.png'

    return icon_path

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application name for better window manager recognition
    app.setApplicationName("py_habits_widget")
    app.setApplicationDisplayName("Habit Tracker Widget")
    app.setDesktopFileName("py_habits_widget.desktop")

    # Set the application icon to blue_icon.png
    icon_path = '/home/twain/Projects/py_habits_widget/icons/blue_icon.png'
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    # Run the update_habitsdb_without_phone_totals.py script when the app opens
    subprocess.run(['python3', '/home/twain/Projects/py_habits_widget/update_habitsdb_without_phone_totals.py'])

    icon_grid = IconGrid()
    # Set the icon on the main window as well
    icon_grid.setWindowIcon(app_icon)
    # Set a proper window title
    icon_grid.setWindowTitle('Habit Tracker Widget')
    
    # Set window class name for X11
    icon_grid.setProperty("WM_CLASS", "py_habits_widget")

    sys.exit(app.exec_())
