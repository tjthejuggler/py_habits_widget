import sys
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QSpacerItem, QSizePolicy, QInputDialog, QLabel, QComboBox
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtGui import QPainter, QFont, QIcon
from PyQt5.QtCore import QSize
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

#change obsidian_dir to this for zenbook ~/Documents/obsidian_note_vault/noteVault

with open('/home/lunkwill/projects/py_habits_widget/obsidian_dir.txt', 'r') as f:
    obsidian_dir = f.read().strip()

def notify(message):
    msg = "notify-send ' ' '"+message+"'"
    os.system(msg)
class NumberedButton(QPushButton):
    def __init__(self, left_number, right_number, *args, **kwargs):
        super(NumberedButton, self).__init__(*args, **kwargs)
        self.left_number = left_number
        self.right_number = right_number

    def paintEvent(self, event):
        super(NumberedButton, self).paintEvent(event)
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 12))
        painter.drawText(4, 66, str(self.left_number))
        right_number_length = len(str(self.right_number))
        painter.drawText(72-(right_number_length*8), 66, str(self.right_number))

class IconGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def get_icons_and_scripts(self):
        
        activities = [ 
            'Juggling record broke', 'Dream acted', 'Sleep watch', 'Apnea walked', 'Cold Shower Widget', 'Programming sessions', 'Book read', 'Fun juggle', 'Drm Review',  'Early phone', 'Apnea practiced', 'Launch Squats Widget', 'Juggling tech sessions', 'Podcast finished', 'Janki used', 'Unusual experience', 'Anki created', 'Apnea apb', 'Launch Situps Widget', 'Writing sessions', 'Educational video watched', 'Filmed juggle', 'Meditations', 'Anki mydis done', 'Apnea spb', 'Launch Pushups Widget', 'UC post', 'Article read', 'Inspired juggle', 'Kind stranger', 'Health learned', 'Lung stretch', 'Cardio sessions', 'AI tool', 'Read academic', 'Juggle goal', 'Broke record', 'Took pills', 'None', 'Good posture',  'Drew', 'Language studied', 'None', 'None', 'None', 'None', 'Flossed', 'Question asked', 'Music listen', 'None', 'None', 'None', 'Todos done', 'None', 'None', 'None'
            ]

        habitsdb = make_json(obsidian_dir+'habitsdb.txt')
        habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt')

        icons_and_scripts = []

        for i in range(len(activities)):
            if activities[i] in habitsdb:
                inner_dict = habitsdb[activities[i]]
                days_since_not_zero = get_days_since_not_zero(inner_dict)
                days_since_zero = get_days_since_zero(inner_dict)
                left_number = -days_since_not_zero
                if days_since_not_zero < 2:
                    days_since_zero = get_days_since_zero_minus(inner_dict) 
                    left_number = days_since_zero               
                right_number = longest_streak = get_longest_streak(inner_dict)
                last_value_from_habitsdb = list(inner_dict.values())[-1]
                value_from_habitsdb_to_add = habitsdb_to_add[activities[i]]
                last_value = last_value_from_habitsdb + value_from_habitsdb_to_add
                print(activities[i], last_value)
                if "Pushups" in activities[i]:
                    last_value = math.floor(last_value/30 + 0.5)
                elif "Situps" in activities[i]:
                    last_value = math.floor(last_value/50 + 0.5)
                elif "Squats" in activities[i]:
                    last_value = math.floor(last_value/30 + 0.5)
                elif "Cold Shower" in activities[i]:
                    if last_value > 0 and last_value < 3:
                        last_value = 3
                    last_value = math.floor(last_value/3 + 0.5)

                print(activities[i], last_value)
                #round last_value
                last_value = math.floor(last_value + 0.5)
                print(activities[i], last_value)

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

                icon_dir = '~/projects/py_habits_widget/icons/'+icon_folder+'/'
                icon_dir = os.path.expanduser(icon_dir)
                icon_finder = IconFinder()
                icon = icon_finder.find_icon(activities[i])
                icon_file = icon + '.png'
                icons_and_scripts.append((icon_dir + icon_file, activities[i], left_number, right_number))

            else:
                icons_and_scripts.append(None)

        return icons_and_scripts

    def init_ui(self):
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        icons_and_scripts = self.get_icons_and_scripts()
        num_columns, num_rows, index = 8, 7, 0
        self.buttons = []

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
            update_theme_script = '~/projects/tail/habits_kde_theme.py'
            update_theme_script = os.path.expanduser(update_theme_script)
            os.system('python3 '+update_theme_script)
            self.update_icons()
            self.update_total()
        if write_updated_personal_records:
            personal_records_dir = os.path.expanduser(personal_records_dir)
            with open(personal_records_dir, 'w') as f:
                json.dump(personal_records, f, indent=4, sort_keys=True)

    def update_icons(self):
        print("Updating icons")
        icons_and_scripts = self.get_icons_and_scripts()
        button_index = 0
        for index, item in enumerate(icons_and_scripts):
            if item is not None:
                print("item", item)
                icon, _, left_number, right_number = item
                self.buttons[button_index].setIcon(QIcon(icon))
                button_index += 1

    def update_total(self):
        icons_and_scripts = self.get_icons_and_scripts()
        today_total, last_7_days_total, last_30_days_total = 0, 0, 0

        for item in icons_and_scripts:
            if item is not None:
                icon, arg, left_number, right_number = item
                
                habitsdb = make_json(obsidian_dir+'habitsdb.txt')
                habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt')

                inner_dict = habitsdb[arg]
                sorted_dates = sorted(inner_dict.keys(), reverse=True)
                current_habit_today = inner_dict[sorted_dates[0]] + habitsdb_to_add[arg]

                def adjust_habit_count(count, habit_name):
                    if "Pushups" in habit_name:
                        return math.floor(count / 30 + 0.5)
                    elif "Situps" in habit_name:
                        return math.floor(count / 50 + 0.5)
                    elif "Squats" in habit_name:
                        return math.floor(count / 30 + 0.5)
                    elif "Cold Shower" in habit_name:
                        if count > 0 and count < 3:
                            count = 3
                        return math.floor(count / 3 + 0.5)
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

        current_date_streak, current_date_antistreak, longest_streak_record, longest_antistreak_record = get_streak_numbers()
        net_streak = current_date_streak - current_date_antistreak
        streak_text = f"{net_streak}\ns {current_date_streak}:{longest_streak_record}\nas {current_date_antistreak}:{longest_antistreak_record}\n"
        self.total_label.setText(f"{streak_text}{today_total}|{last_7_days_total / 7:.1f}|{last_30_days_total / 30:.1f}")

        #write a json file that has net streak, current streak, longest streak, current antistreak, longest antistreak
        streaks_dir = os.path.expanduser(obsidian_dir+'/tail/streaks.txt')
        with open(streaks_dir, 'w') as f:
            json.dump({"net_streak": net_streak, "current_streak": current_date_streak, "longest_streak": longest_streak_record, "current_antistreak": current_date_antistreak, "longest_antistreak": longest_antistreak_record}, f, indent=4, sort_keys=True)




if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon_grid = IconGrid()
    sys.exit(app.exec_())