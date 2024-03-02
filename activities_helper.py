import os
import json

def make_json(directory):
    directory = os.path.expanduser(directory)
    with open(directory, 'r') as f:
        my_json = json.load(f)
    return my_json

with open('/home/lunkwill/projects/tail/obsidian_dir.txt', 'r') as f:
    obsidian_dir = f.read().strip()

habitsdb = make_json(obsidian_dir+'habitsdb.txt')
habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt')

#activities is the list of keys from habitsdb
activities = list(habitsdb.keys())

#print(activities)

#colors=(["#000008"] * 7) + (["red"] * 7), 

#['AI tool']+['Anki created']+['Anki mydis done']+['Apnea apb']+['Apnea practiced']+['Apnea spb']+['Apnea walked']+['Article read']+['Book read']+['Broke record']+['Cardio sessions']+['Cold Shower Widget']+['Create juggle']+['Dream acted']+['Drew']+['Drm Review']+['Early phone']+['Educational video watched']+['Filmed juggle']+['Flossed']+['Fun juggle']+['Good posture']+['Grumpy blocker']+['HIT']+['Health learned']+['Inspired juggle']+['Janki used']+['Juggle goal']+['Juggling record broke']+['Juggling tech sessions']+['Kind stranger']+['Language studied']+['Launch Pushups Widget']+['Launch Situps Widget']+['Launch Squats Widget']+['Lucidity trained']+['Lung stretch']+['Meditations']+['Memory practice']+['Music listen']+['Podcast finished']+['Programming sessions']+['Question asked']+['Read academic']+['Sleep watch']+['Song juggle']+['Todos done']+['Took pills']+['UC post']+['Unique juggle']+['Unusual experience']+['Writing sessions']

hything = ['AI_tool']+['Anki_created']+['Anki_mydis_done']+['Apnea_apb']+['Apnea_practiced']+['Apnea_spb']+['Apnea_walked']+['Article_read']+['Book_read']+['Broke_record']+['Cardio_sessions']+['Cold_Shower_Widget']+['Create_juggle']+['Dream_acted']+['Drew']+['Drm_Review']+['Early_phone']+['Educational_video_watched']+['Filmed_juggle']+['Flossed']+['Fun_juggle']+['Good_posture']+['Grumpy_blocker']+['HIT']+['Health_learned']+['Inspired_juggle']+['Janki_used']+['Juggle_goal']+['Juggling_record_broke']+['Juggling_tech_sessions']+['Kind_stranger']+['Language_studied']+['Launch_Pushups_Widget']+['Launch_Situps_Widget']+['Launch_Squats_Widget']+['Lucidity_trained']+['Lung_stretch']+['Meditations']+['Memory_practice']+['Music_listen']+['Podcast_finished']+['Programming_sessions']+['Question_asked']+['Read_academic']+['Sleep_watch']+['Song_juggle']+['Todos_done']+['Took_pills']+['UC_post']+['Unique_juggle']+['Unusual_experience']+['Writing_sessions']

print(hything)

#replace any item that has 'jug' or 'Jug' in its name
for i in range(len(hything)):
    if 'jug' in hything[i] or 'Jug' in hything[i]:
        hything[i] = '#D5869D'

print(hything)

new = ['#b6bd21', '#696a69', '#696a69', '#2e48e8', '#2e48e8', '#2e48e8', '#2e48e8', '#b6bd21', '#b6bd21', '#ffffff', '#19fe89', '#b225b0', '#D5869D', '#4b25e9', '#1ac6dd', '#4b25e9', '#6900e1', '#b6bd21', '#D5869D', '#19fee8', '#D5869D', '#19fee8', '#ffffff', '#19fe89', '#19fee8', '#D5869D', '#D5869D', '#D5869D', '#D5869D', '#afe516', '#ffffff', '#b6bd21', '#19fe89', '#19fe89', '#19fe89', '#4b25e9', '#2e48e8', '#4b25e9', '#4b25e9', '#4b25e9', '#b6bd21', '#afe516', '#b6bd21', '#b6bd21', '#6900e1', '#D5869D', '#ffffff', '#6900e1', '#afe516', '#D5869D', '#ffffff', '#afe516']