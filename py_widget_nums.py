import sys
#from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QSpacerItem, QSizePolicy
#from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QSpacerItem, QSizePolicy, QInputDialog
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QSpacerItem, QSizePolicy, QInputDialog, QLabel

from PyQt5.QtGui import QPainter, QFont
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
import os
import json
from IconFinder import IconFinder
import time

with open('/home/twain/Projects/py_habits_widget/obsidian_dir.txt', 'r') as f:
    obsidian_dir = f.read().strip()

class NumberedButton(QPushButton):
    def __init__(self, left_number, right_number, *args, **kwargs):
        super(NumberedButton, self).__init__(*args, **kwargs)
        self.left_number = left_number
        self.right_number = right_number

    def paintEvent(self, event):
        super(NumberedButton, self).paintEvent(event)
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 12))
        painter.drawText(4, 76, str(self.left_number))
        right_number_length = len(str(self.right_number))

        painter.drawText(72-(right_number_length*8), 76, str(self.right_number))

class IconGrid(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()


    def get_days_since_zero(self, inner_dict):
        days_since_zero = None
        sorted_dates = sorted(inner_dict.keys(), reverse=True)
        for index, date_str in enumerate(sorted_dates):
            #index = max(1, index)
            if inner_dict[date_str] == 0:
                days_since_zero = index
                break
        if days_since_zero is None:
            days_since_zero = len(sorted_dates)
        return days_since_zero
    
    def get_days_since_zero_minus(self, inner_dict):
        days_since_zero = None
        sorted_dates = sorted(inner_dict.keys(), reverse=True)
        for index, date_str in enumerate(sorted_dates[1:]):
            #index = max(1, index)
            if inner_dict[date_str] == 0:
                days_since_zero = index
                break
        if days_since_zero is None:
            days_since_zero = len(sorted_dates)
        return days_since_zero

    def get_days_since_not_zero(self, inner_dict):
        days_since_not_zero = None
        sorted_dates = sorted(inner_dict.keys(), reverse=True)
        for index, date_str in enumerate(sorted_dates):
            if inner_dict[date_str] != 0:
                days_since_not_zero = index
                break
        if days_since_not_zero is None:
            days_since_not_zero = len(sorted_dates)
        return days_since_not_zero

    def get_longest_streak(self, inner_dict):
        longest_streak = 0
        current_streak = 0
        for date_str, value in sorted(inner_dict.items()):
            if value != 0:
                current_streak += 1
            else:
                longest_streak = max(longest_streak, current_streak)
                current_streak = 0
        longest_streak = max(longest_streak, current_streak)
        return longest_streak


    def get_icons_and_scripts(self):
        
        
        activities = [ 
            'Dream acted', 'Sleep watch', 'Apnea walked', 'Cold Shower Widget', 'Programming sessions', 'Question asked', 'Unusual experience', 'Early phone', 'Apnea practiced', 'Launch Squats Widget', 'Juggling tech sessions', 'Podcast finished', 'Meditations', 'Anki created', 'Apnea apb', 'Launch Situps Widget', 'Writing sessions', 'Educational video watched', 'Kind stranger', 'Anki mydis done', 'Apnea spb', 'Launch Pushups Widget', 'UC post', 'Article read', 'Broke record', 'Health learned', 'None', 'Cardio sessions', 'AI tool', 'Language studied', 'None', 'Janki used', 'None', 'Good posture',  'Drew', 'Juggling record broke', 'None', 'None', 'None', 'Flossed', 'None', 'Fun juggle', 'None', 'None','Todos done', 'None', 'None', 'Music listen'
            ]

        habitsdb_dir = obsidian_dir+'habitsdb.txt'
        habitsdb_dir = os.path.expanduser(habitsdb_dir)
        with open(habitsdb_dir, 'r') as f:
            habitsdb = json.load(f)

        habitsdb_to_add_dir = obsidian_dir+'habitsdb_to_add.txt'
        habitsdb_to_add_dir = os.path.expanduser(habitsdb_to_add_dir)
        with open(habitsdb_to_add_dir, 'r') as f:
            habitsdb_to_add = json.load(f)

        icons_and_scripts = []

        for i in range(len(activities)):
            if activities[i] in habitsdb:
                inner_dict = habitsdb[activities[i]]
                days_since_not_zero = self.get_days_since_not_zero(inner_dict)
                days_since_zero = self.get_days_since_zero(inner_dict)
                left_number = -days_since_not_zero
                if days_since_not_zero < 2:
                    days_since_zero = self.get_days_since_zero_minus(inner_dict) 
                    left_number = days_since_zero               
                right_number = longest_streak = self.get_longest_streak(inner_dict)
                print("activities[i]", activities[i], "days_since_zero", days_since_zero, "days_since_not_zero", days_since_not_zero, "longest_streak", longest_streak)
                last_value_from_habitsdb = list(inner_dict.values())[-1]

                value_from_habitsdb_to_add = habitsdb_to_add[activities[i]]

                last_value = last_value_from_habitsdb + value_from_habitsdb_to_add

                if "Pushups" in activities[i]:
                    last_value = round(last_value/30)
                elif "Situps" in activities[i]:
                    print(last_value)
                    last_value = round(last_value/50)
                elif "Squats" in activities[i]:
                    last_value = round(last_value/30)
                    print(last_value)
                elif "Cold Shower" in activities[i]:
                    if last_value > 0 and last_value < 3:
                        last_value = 3
                    last_value = round(last_value/3)

                icon_folder = 'redgoldpainthd'
                if last_value == 1:
                    print("last_value == 1", activities[i])
                    icon_folder = 'orangewhitepearlhd'
                elif last_value == 2:
                    icon_folder = 'greenfloralhd'
                elif last_value == 3:
                    icon_folder = 'bluewhitepearlhd'
                elif last_value == 4:
                    icon_folder = 'pinkorbhd'
                elif last_value == 5:
                    icon_folder = 'glossysilverhd'
                elif last_value > 5:
                    icon_folder = 'transparentglasshd'

        #MAKE A GITHUB OF THIS!!

                icon_dir = '~/Projects/py_habits_widget/icons/'+icon_folder+'/'
                icon_dir = os.path.expanduser(icon_dir)

                icon_finder = IconFinder()
                icon = icon_finder.find_icon(activities[i])

                icon_file = icon + '.png'
                # script_file = '~/Projects/py_habits_widget/script.py'
                # script_file = os.path.expanduser(habitsdb_dir)
                print(icon_dir + icon_file)
                icons_and_scripts.append((icon_dir + icon_file, activities[i], left_number, right_number))

            else:
                icons_and_scripts.append(None)

        return icons_and_scripts

    def init_ui(self):
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        icons_and_scripts = self.get_icons_and_scripts()
        num_columns = 8
        num_rows = 6
        index = 0
        self.buttons = []

        # Add a QLabel for the total number
        self.total_label = QLabel()
        grid_layout.addWidget(self.total_label, 0, num_columns - 1)
        self.update_total()

        for col in range(num_columns):
            for row in range(1, num_rows + 1):  # Start from row 1 to accommodate the total_label
                if index < len(icons_and_scripts):
                    if icons_and_scripts[index] is not None:
                        icon, arg, left_number, right_number = icons_and_scripts[index]
                        button = NumberedButton(left_number, right_number, self)
                        button.setIcon(QIcon(icon))
                        button.setIconSize(QSize(64, 64))
                        button.clicked.connect(lambda checked, a=arg: self.increment_habit(a))
                        grid_layout.addWidget(button, row, col)
                        self.buttons.append(button)
                    else:
                        spacer = QSpacerItem(64, 64, QSizePolicy.Fixed, QSizePolicy.Fixed)
                        grid_layout.addItem(spacer, row, col)
                index += 1
        self.setWindowTitle('Icon Grid')
        self.show()



    def increment_habit(self, argument):
        write_updated_habitsdb_to_add = False
        habitsdb_to_add_dir = obsidian_dir+'habitsdb_to_add.txt'
        habitsdb_to_add_dir = os.path.expanduser(habitsdb_to_add_dir)
        with open(habitsdb_to_add_dir, 'r') as f:
            habitsdb_to_add = json.load(f)
        if "Widget" in argument:
            # Display an input dialog
            value, ok = QInputDialog.getInt(self, 'Input Dialog', f'Enter the increment for {argument}:', min=1)
            if ok:
                habitsdb_to_add[argument] += value
                write_updated_habitsdb_to_add = True
        else:
            habitsdb_to_add[argument] += 1
            write_updated_habitsdb_to_add = True        
        if write_updated_habitsdb_to_add:
            with open(habitsdb_to_add_dir, 'w') as f:
                json.dump(habitsdb_to_add, f, indent=4, sort_keys=True)
            self.update_icons()
            time.sleep(1)
            update_theme_script = '~/Projects/tail/habits_kde_theme.py'
            update_theme_script = os.path.expanduser(update_theme_script)
            os.system('python3 '+update_theme_script)
        
    def update_icons(self):
        icons_and_scripts = self.get_icons_and_scripts()
        button_index = 0
        for index, item in enumerate(icons_and_scripts):
            if item is not None:
                icon, _ = item
                self.buttons[button_index].setIcon(QIcon(icon))
                button_index += 1

    def update_total(self):
        icons_and_scripts = self.get_icons_and_scripts()
        today_total = 0
        last_7_days_total = 0
        last_30_days_total = 0

        for item in icons_and_scripts:
            if item is not None:
                icon, arg, left_number, right_number = item

                habitsdb_dir = obsidian_dir+'habitsdb.txt'
                habitsdb_dir = os.path.expanduser(habitsdb_dir)
                with open(habitsdb_dir, 'r') as f:
                    habitsdb = json.load(f)

                habitsdb_to_add_dir = obsidian_dir+'habitsdb_to_add.txt'
                habitsdb_to_add_dir = os.path.expanduser(habitsdb_to_add_dir)
                with open(habitsdb_to_add_dir, 'r') as f:
                    habitsdb_to_add = json.load(f)

                inner_dict = habitsdb[arg]
                sorted_dates = sorted(inner_dict.keys(), reverse=True)
                current_habit_today = inner_dict[sorted_dates[0]] + habitsdb_to_add[arg]

                def adjust_habit_count(count, habit_name):
                    if "Pushups" in habit_name:
                        return round(count / 30)
                    elif "Situps" in habit_name:
                        return round(count / 50)
                    elif "Squats" in habit_name:
                        return round(count / 30)
                    elif "Cold Shower" in habit_name:
                        if count > 0 and count < 3:
                            count = 3
                        return round(count / 3)
                    else:
                        return count

                today_total += adjust_habit_count(current_habit_today, arg)

                last_7_days_count = 0
                for date_str in sorted_dates[:7]:
                    last_7_days_count += adjust_habit_count(inner_dict[date_str], arg)
                last_7_days_total += last_7_days_count

                last_30_days_count = 0
                for date_str in sorted_dates[:30]:
                    last_30_days_count += adjust_habit_count(inner_dict[date_str], arg)
                last_30_days_total += last_30_days_count
        #self.total_label.setText(f"Today: {today_total} | Last 7 days: {last_7_days_total / 7:.1f} | Last 30 days: {last_30_days_total / 30:.1f}")

        self.total_label.setText(f"{today_total}|{last_7_days_total / 7:.1f}|{last_30_days_total / 30:.1f}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon_grid = IconGrid()
    sys.exit(app.exec_())