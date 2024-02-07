stats= '''
Habits count
Net streaks
Streaks
Best streaks
Best streak habits count
Anti-streaks
Worst anti-streaks
Worst anti-streak habits count
Daily Total Points
Weekly Smoothed Total Points
Monthly Smoothed Total Points
AI tool
AI tool streak
AI tool % week
AI tool % month
AI tool % year
AI tool % overall
Anki created
Anki created streak
Anki created % week
Anki created % month
Anki created % year
Anki created % overall
Anki mydis done
Anki mydis done streak
Anki mydis done % week
Anki mydis done % month
Anki mydis done % year
Anki mydis done % overall
Apnea apb
Apnea apb streak
Apnea apb % week
Apnea apb % month
Apnea apb % year
Apnea apb % overall
Apnea practiced
Apnea practiced streak
Apnea practiced % week
Apnea practiced % month
Apnea practiced % year
Apnea practiced % overall
Apnea spb
Apnea spb streak
Apnea spb % week
Apnea spb % month
Apnea spb % year
Apnea spb % overall
Apnea walked
Apnea walked streak
Apnea walked % week
Apnea walked % month
Apnea walked % year
Apnea walked % overall
Article read
Article read streak
Article read % week
Article read % month
Article read % year
Article read % overall
Book read
Book read streak
Book read % week
Book read % month
Book read % year
Book read % overall
Broke record
Broke record streak
Broke record % week
Broke record % month
Broke record % year
Broke record % overall
Cardio sessions
Cardio sessions streak
Cardio sessions % week
Cardio sessions % month
Cardio sessions % year
Cardio sessions % overall
Cold Shower Widget
Cold Shower Widget streak
Cold Shower Widget % week
Cold Shower Widget % month
Cold Shower Widget % year
Cold Shower Widget % overall
Create juggle
Create juggle streak
Create juggle % week
Create juggle % month
Create juggle % year
Create juggle % overall
Dream acted
Dream acted streak
Dream acted % week
Dream acted % month
Dream acted % year
Dream acted % overall
Drew
Drew streak
Drew % week
Drew % month
Drew % year
Drew % overall
Drm Review
Drm Review streak
Drm Review % week
Drm Review % month
Drm Review % year
Drm Review % overall
Early phone
Early phone streak
Early phone % week
Early phone % month
Early phone % year
Early phone % overall
Educational video watched
Educational video watched streak
Educational video watched % week
Educational video watched % month
Educational video watched % year
Educational video watched % overall
Filmed juggle
Filmed juggle streak
Filmed juggle % week
Filmed juggle % month
Filmed juggle % year
Filmed juggle % overall
Flossed
Flossed streak
Flossed % week
Flossed % month
Flossed % year
Flossed % overall
Fun juggle
Fun juggle streak
Fun juggle % week
Fun juggle % month
Fun juggle % year
Fun juggle % overall
Good posture
Good posture streak
Good posture % week
Good posture % month
Good posture % year
Good posture % overall
Grumpy blocker
Grumpy blocker streak
Grumpy blocker % week
Grumpy blocker % month
Grumpy blocker % year
Grumpy blocker % overall
HIT
HIT streak
HIT % week
HIT % month
HIT % year
HIT % overall
Health learned
Health learned streak
Health learned % week
Health learned % month
Health learned % year
Health learned % overall
Inspired juggle
Inspired juggle streak
Inspired juggle % week
Inspired juggle % month
Inspired juggle % year
Inspired juggle % overall
Janki used
Janki used streak
Janki used % week
Janki used % month
Janki used % year
Janki used % overall
Juggle goal
Juggle goal streak
Juggle goal % week
Juggle goal % month
Juggle goal % year
Juggle goal % overall
Juggling record broke
Juggling record broke streak
Juggling record broke % week
Juggling record broke % month
Juggling record broke % year
Juggling record broke % overall
Juggling tech sessions
Juggling tech sessions streak
Juggling tech sessions % week
Juggling tech sessions % month
Juggling tech sessions % year
Juggling tech sessions % overall
Kind stranger
Kind stranger streak
Kind stranger % week
Kind stranger % month
Kind stranger % year
Kind stranger % overall
Language studied
Language studied streak
Language studied % week
Language studied % month
Language studied % year
Language studied % overall
Launch Pushups Widget
Launch Pushups Widget streak
Launch Pushups Widget % week
Launch Pushups Widget % month
Launch Pushups Widget % year
Launch Pushups Widget % overall
Launch Situps Widget
Launch Situps Widget streak
Launch Situps Widget % week
Launch Situps Widget % month
Launch Situps Widget % year
Launch Situps Widget % overall
Launch Squats Widget
Launch Squats Widget streak
Launch Squats Widget % week
Launch Squats Widget % month
Launch Squats Widget % year
Launch Squats Widget % overall
Lucidity trained
Lucidity trained streak
Lucidity trained % week
Lucidity trained % month
Lucidity trained % year
Lucidity trained % overall
Lung stretch
Lung stretch streak
Lung stretch % week
Lung stretch % month
Lung stretch % year
Lung stretch % overall
Meditations
Meditations streak
Meditations % week
Meditations % month
Meditations % year
Meditations % overall
Memory practice
Memory practice streak
Memory practice % week
Memory practice % month
Memory practice % year
Memory practice % overall
Music listen
Music listen streak
Music listen % week
Music listen % month
Music listen % year
Music listen % overall
Podcast finished
Podcast finished streak
Podcast finished % week
Podcast finished % month
Podcast finished % year
Podcast finished % overall
Programming sessions
Programming sessions streak
Programming sessions % week
Programming sessions % month
Programming sessions % year
Programming sessions % overall
Question asked
Question asked streak
Question asked % week
Question asked % month
Question asked % year
Question asked % overall
Read academic
Read academic streak
Read academic % week
Read academic % month
Read academic % year
Read academic % overall
Sleep watch
Sleep watch streak
Sleep watch % week
Sleep watch % month
Sleep watch % year
Sleep watch % overall
Song juggle
Song juggle streak
Song juggle % week
Song juggle % month
Song juggle % year
Song juggle % overall
Todos done
Todos done streak
Todos done % week
Todos done % month
Todos done % year
Todos done % overall
Took pills
Took pills streak
Took pills % week
Took pills % month
Took pills % year
Took pills % overall
UC post
UC post streak
UC post % week
UC post % month
UC post % year
UC post % overall
Unique juggle
Unique juggle streak
Unique juggle % week
Unique juggle % month
Unique juggle % year
Unique juggle % overall
Unusual experience
Unusual experience streak
Unusual experience % week
Unusual experience % month
Unusual experience % year
Unusual experience % overall
Writing sessions
Writing sessions streak
Writing sessions % week
Writing sessions % month
Writing sessions % year
Writing sessions % overall
Unique habits per day
Average % week
Average % month
Average % year
Average % overall
'''

#add a number before each habit
stats = stats.split('\n')
stats = [str(i-1) + '. ' + stats[i] for i in range(len(stats))]
stats = '\n'.join(stats)
print(stats)