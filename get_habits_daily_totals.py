import os
import json
import math

with open('/home/twain/Projects/py_habits_widget/obsidian_dir.txt', 'r') as f:
    obsidian_dir = f.read().strip()

def make_json(directory):
    directory = os.path.expanduser(directory)
    with open(directory, 'r') as f:
        my_json = json.load(f)
    return my_json

def adjust_habit_count(count, habit_name):
    if "Pushups" in habit_name:
        return math.floor(count / 30 + 0.5)
    elif "Situps" in habit_name:
        return math.floor(count / 50 + 0.5)
    elif "Squats" in habit_name:
        return math.floor(count / 30 + 0.5)
    elif "Sweat" in habit_name:
        return math.floor(count / 15 + 0.5)
    elif "Cold Shower" in habit_name:
        if count > 0 and count < 3:
            count = 3
        return math.floor(count / 3 + 0.5)
    else:
        return count
            
def output_habits_per_day():
    habitsdb = make_json(obsidian_dir+'habitsdb.txt')
    habitsdb_phone = make_json(obsidian_dir+'habitsdb_phone.txt')
    
    # Merge habitsdb_phone into habitsdb
    for habit, dates in habitsdb_phone.items():
        if habit not in habitsdb:
            habitsdb[habit] = {}
        habitsdb[habit].update(dates)

    habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt')

    with open('habits_per_day.txt', 'w') as f:
        for habit_name, inner_dict in habitsdb.items():
            sorted_dates = sorted(inner_dict.keys(), reverse=True)
            for date_str in sorted_dates:
                count = inner_dict[date_str] + habitsdb_to_add.get(habit_name, 0)
                count = adjust_habit_count(count, habit_name)
                f.write(f"{date_str}: {count}\n")

# Load all database files
habits = make_json(obsidian_dir+'habitsdb.txt')
habitsdb_phone = make_json(obsidian_dir+'habitsdb_phone.txt')
habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt')

# Merge habitsdb_phone into habits
for habit, dates in habitsdb_phone.items():
    if habit not in habits:
        habits[habit] = {}
    habits[habit].update(dates)

# Get a list of all the dates
dates = sorted(set(date for habit in habits.values() for date in habit.keys()))

# Count the number of habits done each day
totals = []
for date in dates:
    daily_total = 0
    for habit_name, habit in habits.items():
        value = habit.get(date, 0)
        if date == sorted(habit.keys())[-1]:  # If it's the latest date
            value += habitsdb_to_add.get(habit_name, 0)  # Add pending value from habitsdb_to_add
        daily_total += adjust_habit_count(value, habit_name)
    totals.append(daily_total)

#reverse the order of totals
totals.reverse()

# Write the totals to a text file
with open('/home/twain/noteVault/habitCounters/total_habits.txt2', 'w') as f:
    f.write(','.join(str(total) for total in totals))

#get the average of the first 7 numbes in totals
week_average = sum(totals[:7]) / 7
month_average = sum(totals[:30]) / 30

with open('/home/twain/noteVault/habitCounters/week_average.txt', 'w') as f:
    f.write(str(week_average))

with open('/home/twain/noteVault/habitCounters/month_average.txt', 'w') as f:
    f.write(str(month_average))
