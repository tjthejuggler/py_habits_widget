class IconFinder:
    def __init__(self):
        self.activity_to_icon = {
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
            'Drm Review': 'anchor6_sc48'
        }

        # Create a dictionary with the reverse mapping from icons to activities
        self.icon_to_activity = {icon: activity for activity, icon in self.activity_to_icon.items()}

    def find_icon(self, activity):
        return self.activity_to_icon.get(activity, 'Unknown')

    def find_activity(self, icon):
        return self.icon_to_activity.get(icon, 'Unknown')
