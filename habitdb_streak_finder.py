from datetime import datetime, timedelta

import os
import json

def make_json(directory):
    directory = os.path.expanduser(directory)
    with open(directory, 'r') as f:
        my_json = json.load(f)
    return my_json

def get_days_since_zero_custom_datef(inner_dict, target_date):
    days_since_zero = None
    sorted_dates = [d for d in inner_dict.keys() if d <= target_date]
    sorted_dates.sort(reverse=True)
    for index, date_str in enumerate(sorted_dates):
        if inner_dict[date_str] == 0:
            days_since_zero = index
            break
    if days_since_zero is None:
        days_since_zero = len(sorted_dates)
    return days_since_zero

def get_days_since_not_zero_custom_date(inner_dict, target_date):
    days_since_not_zero = None
    sorted_dates = [d for d in inner_dict.keys() if d <= target_date]
    sorted_dates.sort(reverse=True)
    for index, date_str in enumerate(sorted_dates):
        if inner_dict[date_str] != 0:
            days_since_not_zero = index
            break
    if days_since_not_zero is None:
        days_since_not_zero = len(sorted_dates)
    return days_since_not_zero

# Example usage
target_date = '2022-09-03'
date_format = '%Y-%m-%d'
target_date_obj = datetime.strptime(target_date, date_format).date()

with open('/home/lunkwill/projects/tail/obsidian_dir.txt', 'r') as f:
    obsidian_dir = f.read().strip()

habitsdb = make_json(obsidian_dir+'habitsdb.txt')
habitsdb_to_add = make_json(obsidian_dir+'habitsdb_to_add.txt')

#activities is the list of keys from habitsdb
activities = list(habitsdb.keys())

icons_and_scripts = []
total_days_since_not_zero = 0
total_days_since_zero = 0
for i in range(len(activities)):
    inner_dict = habitsdb[activities[i]]
    days_since_not_zero = get_days_since_not_zero_custom_date(inner_dict, target_date)
    total_days_since_not_zero += days_since_not_zero
    days_since_zero = get_days_since_zero_custom_datef(inner_dict, target_date)
    total_days_since_zero += days_since_zero

def find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb):
    date_format = '%Y-%m-%d'
    start_date_obj = datetime.strptime(start_date, date_format).date()
    end_date_obj = datetime.strptime(end_date, date_format).date()

    longest_streak_record = {'date': None, 'streak': 0}
    longest_antistreak_record = {'date': None, 'streak': 0}
    current_date_streak = 0
    current_date_antistreak = 0

    current_date = start_date_obj
    while current_date <= end_date_obj:
        current_date_str = current_date.strftime(date_format)
        total_days_since_not_zero = 0
        total_days_since_zero = 0
        for activity in activities:
            inner_dict = habitsdb[activity]
            days_since_not_zero = get_days_since_not_zero_custom_date(inner_dict, current_date_str)
            total_days_since_not_zero += days_since_not_zero
            days_since_zero = get_days_since_zero_custom_datef(inner_dict, current_date_str)
            total_days_since_zero += days_since_zero

        if total_days_since_zero > longest_streak_record['streak']:
            longest_streak_record = {'date': current_date_str, 'streak': total_days_since_zero}

        if total_days_since_not_zero > longest_antistreak_record['streak']:
            longest_antistreak_record = {'date': current_date_str, 'streak': total_days_since_not_zero}

        if current_date == end_date_obj:
            current_date_streak = total_days_since_zero
            current_date_antistreak = total_days_since_not_zero

        current_date += timedelta(days=1)

    return longest_streak_record, longest_antistreak_record, current_date_streak, current_date_antistreak



def get_streak_numbers():
    # Example usage
    start_date = '2022-09-03'
    end_date = datetime.now().strftime('%Y-%m-%d')

    longest_streak_record, longest_antistreak_record, current_date_streak, current_date_antistreak = find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb)

    print('Longest streak date:', longest_streak_record['date'])
    print('Longest streak:', longest_streak_record['streak'])

    print('Longest antistreak date:', longest_antistreak_record['date'])
    print('Longest antistreak:', longest_antistreak_record['streak'])

    print('Current streak:', current_date_streak)
    print('Current antistreak:', current_date_antistreak)

    return(current_date_streak, current_date_antistreak, longest_streak_record['streak'], longest_antistreak_record['streak'])