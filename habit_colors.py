"""
Color tiers and icon mapping for habit buttons, matching the Android app's HabitColors.kt.
Uses QColor for PyQt5 compatibility.
"""
import os
from typing import Dict, Optional, List
from PyQt5.QtGui import QColor

# 7 color tiers — progressively brighter/more saturated as count increases
COLOR_RED    = QColor(0x3D, 0x15, 0x15)   # muted dark red         — count 0
COLOR_ORANGE = QColor(0x7A, 0x38, 0x00)   # distinctly orange      — count 1
COLOR_GREEN  = QColor(0x1A, 0x40, 0x20)   # medium-muted green     — count 2
COLOR_BLUE   = QColor(0x10, 0x22, 0x55)   # medium-muted blue      — count 3
COLOR_PINK   = QColor(0x90, 0x10, 0x60)   # semi-bright magenta    — count 4
COLOR_YELLOW = QColor(0xB8, 0xB0, 0x00)   # bright neon yellow     — count 5
COLOR_GLASS  = QColor(0xD0, 0xD0, 0xE0)   # bright near-white      — count 6+


def get_habit_color(habit_name: str, count: int) -> QColor:
    """
    Returns the background color for a habit button based on today's effective points count.
    """
    if count == 0:
        return COLOR_RED
    elif count == 1:
        return COLOR_ORANGE
    elif count == 2:
        return COLOR_GREEN
    elif count == 3:
        return COLOR_BLUE
    elif count == 4:
        return COLOR_PINK
    elif count == 5:
        return COLOR_YELLOW
    else:
        return COLOR_GLASS


# Default icon mapping: habit name → icon filename (without .png)
# Matches the Android HABIT_ICON map and IconFinder.py
HABIT_ICON: Dict[str, str] = {
    'Article read': 'document',
    'Flossed': 'tool_cutter1_sc44',
    'Programming sessions': 'computer_keyboard',
    'Kind stranger': 'baby',
    'Meditations': 'electrical_plug1',
    'Juggling tech sessions': 'gears_sc37',
    'Unusual experience': 'fishbowl',
    'AI tool': 'magic_wand',
    'Broke record': 'disc',
    'Podcast finished': 'headset3',
    'Apnea walked': 'music_trumpet1',
    'Juggling record broke': 'hand22_sc48',
    'Sleep watch': 'clock5_sc44',
    'Early phone': 'ipod1',
    'Drew': 'pen1',
    'Writing sessions': 'pencil1',
    'Cold Shower Widget': 'snowflake3_sc37',
    'Music listen': 'music_eighth_notes',
    'Anki created': 'toolset_sc44',
    'Good posture': 'robot1',
    'Educational video watched': 'computer_monitor',
    'Health learned': 'raindrop2',
    'Language studied': 'globe',
    'Janki used': 'binocular',
    'Apnea practiced': 'music_tuba',
    'Anki mydis done': 'microscope',
    'Launch Situps Widget': 'animal_mouse1',
    'Question asked': 'people_couple_sc44',
    'UC post': 'wireless',
    'Dream acted': 'ship_sc36',
    'Launch Pushups Widget': 'animal_lizard1',
    'Todos done': 'clipboard1',
    'Apnea spb': 'logo_superman_sc37',
    'Apnea apb': 'music_microphone',
    'Cardio sessions': 'bicycle',
    'Launch Squats Widget': 'animal_duck4',
    'Fun juggle': 'a_media29_record',
    'Took pills': 'car_gauge3',
    'Book read': 'registered_mark1',
    'Juggle goal': 'ladder1_sc48',
    'Filmed juggle': 'camera',
    'Inspired juggle': 'information4_sc49',
    'Read academic': 'charts1_sc1',
    'Lung stretch': 'two_directions_left_right',
    'Drm Review': 'anchor6_sc48',
    'Unique juggle': 'animal_cat_print',
    'Create juggle': 'animal_butterfly5_sc48',
    'Song juggle': 'music_cleft',
    'Memory practice': 'diskette4',
    'Grumpy blocker': 'lock_heart',
    'Lucidity trained': 'train8_sc43',
    'HIT': 'animal_crocodile_sc43',
    'Some anki': 'paperclip',
    'Move juggle': 'arrows_rotated',
    'Watch juggle': 'magnifying_glass_ps',
    'Fresh air': 'tree_palm4',
    'Talk stranger': 'magnet',
    'Balanced': 'letter_ii',
    'Fasted': 'eye6',
    'Magic practiced': 'key11_sc48',
    'Magic performed': 'lock6_sc48',
    'Sweat': 'hourglass',
    'Free': 'foot_left_ps',
    'Juggle run': 'robot',
    'Juggle lights': 'flower17',
    'Joggle': 'police_car',
    'Blind juggle': 'moon',
    'Juggling Balls Carry': 'copyright',
    'Juggling Others Learn': 'www_search_ps',
    'No Coffee': 'gas_none_sc49',
    'Tracked Sleep': 'helicopter4',
    'Rabbit Hole': 'chest',
    'Speak AI': 'loud_speaker',
    'Fiction Book Intake': 'document4',
    'Fiction Video Intake': 'a_media22_arrow_forward1',
    'Communication Improved': 'text_size',
    'Unusually Kind': 'thumbs_up1',
    'Most Collisions': 'compass2',
    'Chess': 'key_hole_sc48'
}

# All available icon names (without .png extension), sorted alphabetically.
# These correspond to PNG files in the icons/ directory.
ALL_ICON_NAMES: List[str] = sorted(set(HABIT_ICON.values()) | {
    "a_media21_arrow_back", "a_media22_arrow_forward1", "a_media23_arrows_seek_back",
    "a_media24_arrows_seek_forward", "a_media25_arrows_skip_back", "a_media26_arrows_skip_forward",
    "a_media27_pause_sign", "a_media28_stop", "a_media29_record",
    "a_media31_back", "a_media32_forward", "a_media33_down", "a_media34_up",
    "a_media35_add", "a_media36_delete",
    "airplane1", "airplane4", "ambulance2",
    "anchor6_sc48", "animal_antz", "animal_butterfly5_sc48", "animal_cat_print",
    "animal_crocodile_sc43", "animal_duck4", "animal_lizard1", "animal_mouse1",
    "animal_snail", "animal_spider", "arrow_styled_right", "arrows_rotated",
    "at_sign", "baby", "bag_paper1", "bag_paper3", "basket", "battery1",
    "bicycle", "binocular", "box1", "briefcase", "brush_paint55",
    "brush_paint57_sc52", "brush_painting_sc43", "cabinet", "calculator",
    "calendar", "camera", "camera1_sc49", "car12", "car9_sc44", "car_gauge3",
    "car_gears", "cart2", "cart_arrow", "cart_solid", "cd_load", "cd_refresh",
    "cd_sc52", "charcoal_cart", "charts1_sc1", "chest", "clipboard1",
    "clock1", "clock3", "clock4", "clock5_sc44", "clock7_sc43",
    "compass2", "compass4", "computer_desktop1", "computer_keyboard",
    "computer_laptop2", "computer_monitor", "computer_mouse", "computer_mouse2",
    "computer_server2", "computer_usb_drive_sc7", "copyright", "creditcard2",
    "currency_british_pound_sc35", "currency_cent_sc35", "currency_euro3",
    "currency_japanese_yen2_sc35", "cursor", "diamond5_sc27", "disc",
    "diskette4", "diskette_save", "document", "document1", "document3",
    "document4", "document5", "document6", "document9", "dollar",
    "electrical_plug1", "envelope1", "envelope5", "eye6", "fax",
    "fishbowl", "flower17", "folder", "folder1", "folder2_sc1",
    "foot_left_ps", "foot_steps", "gas_none_sc49", "gas_station4_sc49",
    "gear1", "gear3", "gear4", "gear8", "gear_c_sc44", "gears1_sc44",
    "gears_sc37", "globe", "hand22_sc48", "hat2_sc44", "head_set",
    "headset3", "helicopter4", "home5", "home6", "home7", "horn_sc48",
    "hourglass", "hourglass2", "icon_002", "icon_003", "information4_sc49",
    "ipod1", "ipod2", "key11_sc48", "key9", "key_hole_sc48", "keys_sc43",
    "ladder1_sc48", "lamp_aladin", "last_arrow_down", "last_arrow_left",
    "last_arrow_right", "leaf3", "letter_ii", "letter_nn", "light_bulb",
    "light_bulb2_sc52", "light_off", "lightning2_sc48", "lock3", "lock4",
    "lock5", "lock6_sc48", "lock_heart", "logo_superman_sc37",
    "loud_speaker", "loud_speaker1_ps", "magic_wand", "magnet",
    "magnify_zoom", "magnify_zoom_out", "magnifying_glass_ps", "mail",
    "mailbox", "mailbox1", "media2_arrow_down", "media2_arrow_up",
    "microscope", "moon", "music_accordian", "music_clarinet", "music_cleft",
    "music_drum1_sc44", "music_eighth_note", "music_eighth_notes",
    "music_guitar", "music_guitar1", "music_harp2", "music_microphone",
    "music_off_ps", "music_on_ps", "music_piano2_sc52", "music_piano_keys",
    "music_sax4", "music_sixteenth_note", "music_speaker", "music_tamborine",
    "music_trumpet1", "music_tuba", "music_violin", "notepad", "number_sign",
    "oil_well", "paperclip", "paperclip2", "pen1", "pen6_ps", "pen_crayon",
    "pencil1", "pencil7_sc49", "people_couple_sc44", "percent_sign",
    "phone", "phone1", "phone_cell", "phone_cell2", "phone_clear",
    "phone_solid", "picture_frame1_sc52", "police_car", "power_button4",
    "printer", "race_car", "raindrop2", "registered_mark1", "robot",
    "robot1", "satellite_dish_sc43", "scissors", "ship2", "ship_sc36",
    "ship_wheel1", "signature1", "snowflake3_sc37", "space_satelite",
    "spaceship", "spaceship2_sc43", "spiderweb2", "star_trek_sc43",
    "starburst", "tag", "tape_reel1", "tape_reel2", "text_size",
    "thumbs_down", "thumbs_down1", "thumbs_up1", "thumb_tack_ps",
    "tool", "tool_axe1_sc48", "tool_cutter1_sc44", "tool_hammer4_sc44",
    "tool_screw_sc44", "tool_shovel2_sc44", "tool_sword_sc48",
    "tool_wheelbarrow1_sc32", "tool_wrench8_sc44", "toolset_sc44",
    "trademark_ps", "train8_sc43", "train9_sc43", "trashcan", "trashcan3",
    "tree_palm4", "triangle_clear_up", "two_directions_left_right",
    "wall", "wand1_sc43", "webcam", "wireless", "www_search_ps", "x_solid"
})

# Base directory for icon PNG files
ICONS_BASE_DIR = os.path.expanduser('~/Projects/py_habits_widget/icons/')

# Use the exact same drawable icons as the Android app.
# These are shape-only icons (transparent background) that look correct when white-tinted.
# The pinkorbhd/blueorbhd folders have icons inside orb circles — those become solid white circles.
ICON_DIR = os.path.expanduser(
    '~/AndroidStudioProjects/tail/app/src/main/res/drawable/')


def get_habit_icon_name(habit_name: str, custom_overrides: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    Returns the icon name for a habit, checking custom overrides first,
    then falling back to the default HABIT_ICON map.
    """
    if custom_overrides:
        custom = custom_overrides.get(habit_name)
        if custom:
            return custom
    return HABIT_ICON.get(habit_name)


def get_habit_icon_path(habit_name: str, custom_overrides: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    Returns the full file path to the icon PNG for a habit.
    Returns None if no icon is mapped.
    """
    icon_name = get_habit_icon_name(habit_name, custom_overrides)
    if icon_name is None:
        return None
    path = os.path.join(ICON_DIR, icon_name + '.png')
    if os.path.exists(path):
        return path
    # Try other icon directories as fallback
    for subdir in os.listdir(ICONS_BASE_DIR):
        alt_path = os.path.join(ICONS_BASE_DIR, subdir, icon_name + '.png')
        if os.path.exists(alt_path):
            return alt_path
    return None
