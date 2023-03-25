import sys
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
import subprocess
import os
import json
from IconFinder import IconFinder

class IconGrid(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()
        

    def get_icons_and_scripts(self):
        
        activities = [ 
            'Dream acted', 'Sleep watch', 'Apnea walked', 'Cold Shower Widget', 'Programming sessions', 'Question asked', 'Unusual experience', 'Early phone', 'Apnea practiced', 'Launch Squats Widget', 'Juggling tech sessions', 'Podcast finished', 'Meditations', 'Anki created', 'Apnea apb', 'Launch Situps Widget', 'Writing sessions', 'Educational video watched', 'Kind stranger', 'Anki mydis done', 'Apnea spb', 'Launch Pushups Widget', 'UC post', 'Article read', 'Broke record', 'Health learned', 'None', 'Cardio sessions', 'AI tool', 'Language studied', 'None', 'Janki used', 'None', 'Good posture',  'Drew', 'Juggling record broke', 'None', 'None', 'None', 'Flossed', 'None', 'Fun juggle', 'None', 'None','Todos done', 'None', 'None', 'Music listen'
            ]

        habitsdb_dir = '~/Documents/obsidian_note_vault/noteVault/habitsdb.txt'
        habitsdb_dir = os.path.expanduser(habitsdb_dir)
        with open(habitsdb_dir, 'r') as f:
            habitsdb = json.load(f)

        habitsdb_to_add_dir = '~/Documents/obsidian_note_vault/noteVault/habitsdb_to_add.txt'
        habitsdb_to_add_dir = os.path.expanduser(habitsdb_to_add_dir)
        with open(habitsdb_to_add_dir, 'r') as f:
            habitsdb_to_add = json.load(f)

        icons_and_scripts = []

        for i in range(len(activities)):
            if activities[i] in habitsdb:
                inner_dict = habitsdb[activities[i]]
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
                elif "Cold Shower" in activities[i]:
                    if last_value > 0 and last_value < 3:
                        last_value = 3
                    last_value = round(last_value/3)

                icon_folder = 'redgoldpainthd'
                if last_value == 1:
                    icon_folder = 'orangewhitepearlhd'
                elif last_value == 2:
                    icon_folder = 'greenfloralhd'
                elif last_value == 3:
                    icon_folder = 'bluewhitepearlhd'
                elif last_value == 4:
                    icon_folder = 'blueorbhd'
                elif last_value == 5:
                    icon_folder = 'glossysilverhd'
                elif last_value == 6:
                    icon_folder = 'transparenthd'

        #MAKE A GITHUB OF THIS!!

                icon_dir = '~/projects/kde_habits_widget/icons/'+icon_folder+'/'
                icon_dir = os.path.expanduser(icon_dir)

                icon_finder = IconFinder()
                icon = icon_finder.find_icon(activities[i])

                icon_file = icon + '.png'
                # script_file = '~/projects/kde_habits_widget/script.py'
                # script_file = os.path.expanduser(habitsdb_dir)
                print(icon_dir + icon_file)
                icons_and_scripts.append((icon_dir + icon_file, activities[i]))
            else:
                icons_and_scripts.append(None)

        return icons_and_scripts

    def init_ui(self):
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)

        # List of icon files and associated script files with arguments
        icons_and_scripts = self.get_icons_and_scripts()

        num_columns = 8
        num_rows = 6
        index = 0

        self.buttons = []

        for col in range(num_columns):
            for row in range(num_rows):
                if index < len(icons_and_scripts):
                    if icons_and_scripts[index] is not None:
                        icon, arg = icons_and_scripts[index]
                        button = QPushButton()
                        button.setIcon(QIcon(icon))
                        button.setIconSize(QSize(64, 64))
                        button.clicked.connect(lambda checked, a=arg: self.run_script(a))
                        grid_layout.addWidget(button, row, col)
                        self.buttons.append(button)
                    else:
                        spacer = QSpacerItem(64, 64, QSizePolicy.Fixed, QSizePolicy.Fixed)
                        grid_layout.addItem(spacer, row, col)
                index += 1

        self.setWindowTitle('Icon Grid')
        self.show()

    def run_script(self, argument):
        habitsdb_to_add_dir = '~/Documents/obsidian_note_vault/noteVault/habitsdb_to_add.txt'
        habitsdb_to_add_dir = os.path.expanduser(habitsdb_to_add_dir)
        with open(habitsdb_to_add_dir, 'r') as f:
            habitsdb_to_add = json.load(f)

        habitsdb_to_add[argument] += 1

        with open(habitsdb_to_add_dir, 'w') as f:
            json.dump(habitsdb_to_add, f)

        self.update_icons()
        
    def update_icons(self):
        icons_and_scripts = self.get_icons_and_scripts()

        button_index = 0
        for index, item in enumerate(icons_and_scripts):
            if item is not None:
                icon, _ = item
                self.buttons[button_index].setIcon(QIcon(icon))
                button_index += 1



if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon_grid = IconGrid()
    sys.exit(app.exec_())
