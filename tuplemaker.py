icon_path = '/path/to/icon/folder/'  # replace with actual path to icon folder
script_path = '/path/to/script.py'  # replace with actual path to script file

icon_names = ['document', 'tool_cutter1_sc44', 'computer_keyboard', 'baby', 'electrical_plug1', 'gears_sc37', 'fishbowl', 'magic_wand', 'disc', 'headset3', 'music_trumpet1', 'hand22_sc48', 'clock5_sc44', 'ipod1', 'pen1', 'pencil1', 'snowflake3_sc37', 'music_eighth_notes', 'toolset_sc44', 'robot1', 'computer_monitor', 'raindrop2', 'globe', 'binocular', 'music_tuba', 'microscope', 'animal_mouse1', 'people_couple_sc44', 'wireless', 'ship_sc36', 'animal_lizard1', 'clipboard1', 'logo_superman_sc37', 'music_microphone', 'bicycle', 'animal_duck4', 'a_media29_record', 'Unknown']

icons_and_scripts = []

for icon_name in icon_names:
    icon_file = icon_name + '.png'
    script_file = script_path
    argument = icon_name
    icons_and_scripts.append((icon_path + icon_file, script_file, argument))

print(icons_and_scripts)
