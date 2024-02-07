from datetime import datetime, timedelta

import os
import json
import math
#import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import plotly.graph_objs as go
from plotly.subplots import make_subplots

import dash
import dash_core_components as dcc
from dash import html
from datetime import datetime, timedelta
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

import threaded_dash_app
import webbrowser

def make_json(directory):
    directory = os.path.expanduser(directory)
    with open(directory, 'r') as f:
        my_json = json.load(f)
    return my_json

def get_days_since_zero_custom_date(inner_dict, target_date):
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
    days_since_zero = get_days_since_zero_custom_date(inner_dict, target_date)
    total_days_since_zero += days_since_zero

# def find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb):
#     date_format = '%Y-%m-%d'
#     start_date_obj = datetime.strptime(start_date, date_format).date()
#     end_date_obj = datetime.strptime(end_date, date_format).date()

#     longest_streak_record = {'date': None, 'streak': 0}
#     longest_antistreak_record = {'date': None, 'streak': 0}
#     current_date_streak = 0
#     current_date_antistreak = 0

#     current_date = start_date_obj
#     while current_date <= end_date_obj:
#         current_date_str = current_date.strftime(date_format)
#         total_days_since_not_zero = 0
#         total_days_since_zero = 0
#         for activity in activities:
#             inner_dict = habitsdb[activity]
#             days_since_not_zero = get_days_since_not_zero_custom_date(inner_dict, current_date_str)
#             total_days_since_not_zero += days_since_not_zero
#             days_since_zero = get_days_since_zero_custom_datef(inner_dict, current_date_str)
#             total_days_since_zero += days_since_zero

#         if total_days_since_zero > longest_streak_record['streak']:
#             longest_streak_record = {'date': current_date_str, 'streak': total_days_since_zero}

#         if total_days_since_not_zero > longest_antistreak_record['streak']:
#             longest_antistreak_record = {'date': current_date_str, 'streak': total_days_since_not_zero}

#         if current_date == end_date_obj:
#             current_date_streak = total_days_since_zero
#             current_date_antistreak = total_days_since_not_zero

#         current_date += timedelta(days=1)

#     return longest_streak_record, longest_antistreak_record, current_date_streak, current_date_antistreak
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

def get_best_streak_custom_date(inner_dict, target_date):
    best_streak = 0
    sorted_dates = [d for d in inner_dict.keys() if d <= target_date]
    sorted_dates.sort(reverse=True)
    for index, date_str in enumerate(sorted_dates):
        if inner_dict[date_str] == 0:
            break
        else:
            best_streak += 1
    return best_streak

def find_new_habits(habit_dict):
    # Initialize variables
    previous_habits = set()
    most_recent_new_habits = []
    list_of_new_habits = {}

    # Ensure the dates are sorted
    sorted_dates = sorted(habit_dict.keys())

    for date in sorted_dates:
        current_habits = set(habit_dict[date])
        new_habits = current_habits - previous_habits

        # Update the list of new habits only if there are new habits
        if new_habits:
            most_recent_new_habits = list(new_habits)

        # Assign the most recent new habits to the current date
        list_of_new_habits[date] = most_recent_new_habits
        previous_habits = current_habits

    return list_of_new_habits



def find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb, show_graph, checked_activities):
    date_format = '%Y-%m-%d'
    start_date_obj = datetime.strptime(start_date, date_format).date()
    end_date_obj = datetime.strptime(end_date, date_format).date()

    # Create a list of dates from start_date_obj to end_date_obj
    dates = pd.date_range(start=start_date_obj, end=end_date_obj)

    # Convert the list of dates to datetime objects
    dates = pd.to_datetime(dates)

    longest_streak_record = {'date': None, 'streak': 0}
    longest_antistreak_record = {'date': None, 'streak': 0}
    highest_net_streak_record = {'date': None, 'net_streak': 0}
    lowest_net_streak_record = {'date': None, 'net_streak': 0}

    current_date_streak, current_date_antistreak = 0, 0
    daily_streaks, daily_antistreaks, daily_net_streaks, daily_total_points = [], [], [], []
    # percent_days_previous_week, percent_days_previous_month, percent_days_previous_yea, percent_days_previous_all = [], [], []
    daily_best_streaks, daily_best_streak_habit_count = [], [] #new for best ever
    highest_days_since_zero_so_far = {activity: 0 for activity in activities}
    habits_currently_besting = {}

    daily_worst_anti_streaks, daily_worst_anti_streak_habit_count = [], [] #new for worst ever
    highest_days_since_not_zero_so_far = {activity: 0 for activity in activities}
    habits_currently_worsting = {}

    daily_habits_count = []
    list_of_habits = {}

    currently_streaking_habits = {}
    currently_antistreaking_habits = {}
    checked_activity_daily_count = []
    checked_activity_streak = []
    unique_habits_count_per_day = []

    # Initialize dictionaries for tracking highest and lowest points and unique habits
    records = {
        'points': {
            'highest': {'all_time': {'date': None, 'value': 0}, 'last_week': {'date': None, 'value': 0}, 'last_month': {'date': None, 'value': 0}, 'last_year': {'date': None, 'value': 0}},
            'lowest': {'all_time': {'date': None, 'value': float('inf')}, 'last_week': {'date': None, 'value': float('inf')}, 'last_month': {'date': None, 'value': float('inf')}, 'last_year': {'date': None, 'value': float('inf')}},
        },
        'unique_habits': {
            'highest': {'all_time': {'date': None, 'value': 0}, 'last_week': {'date': None, 'value': 0}, 'last_month': {'date': None, 'value': 0}, 'last_year': {'date': None, 'value': 0}},
            'lowest': {'all_time': {'date': None, 'value': float('inf')}, 'last_week': {'date': None, 'value': float('inf')}, 'last_month': {'date': None, 'value': float('inf')}, 'last_year': {'date': None, 'value': float('inf')}},
        },    
        'streak': {
            'highest': {'all_time': {'date': None, 'value': 0}, 'last_week': {'date': None, 'value': 0}, 'last_month': {'date': None, 'value': 0}, 'last_year': {'date': None, 'value': 0}},
            'lowest': {'all_time': {'date': None, 'value': float('inf')}, 'last_week': {'date': None, 'value': float('inf')}, 'last_month': {'date': None, 'value': float('inf')}, 'last_year': {'date': None, 'value': float('inf')}},
        },
        'antistreak': {
            'highest': {'all_time': {'date': None, 'value': 0}, 'last_week': {'date': None, 'value': 0}, 'last_month': {'date': None, 'value': 0}, 'last_year': {'date': None, 'value': 0}},
            'lowest': {'all_time': {'date': None, 'value': float('inf')}, 'last_week': {'date': None, 'value': float('inf')}, 'last_month': {'date': None, 'value': float('inf')}, 'last_year': {'date': None, 'value': float('inf')}},
        },
        'net_streak': {
            'highest': {'all_time': {'date': None, 'value': 0}, 'last_week': {'date': None, 'value': 0}, 'last_month': {'date': None, 'value': 0}, 'last_year': {'date': None, 'value': 0}},
            'lowest': {'all_time': {'date': None, 'value': float('inf')}, 'last_week': {'date': None, 'value': float('inf')}, 'last_month': {'date': None, 'value': float('inf')}, 'last_year': {'date': None, 'value': float('inf')}},
        }
    }



    def update_records(date, value, category, type, period):
        """
        Update the records dictionary.

        :param date: The date of the record
        :param value: The value (points or unique habits count) for the record
        :param category: 'points' or 'unique_habits'
        :param type: 'highest' or 'lowest'
        :param period: 'all_time', 'last_week', 'last_month', 'last_year'
        """
        current_record = records[category][type][period]
        if (type == 'highest' and value > current_record['value']) or \
        (type == 'lowest' and value < current_record['value']):
            records[category][type][period] = {'date': date, 'value': value}

    # Calculate the start dates for the last week, month, and year
    one_week_ago = end_date_obj - timedelta(days=7)
    one_month_ago = end_date_obj - timedelta(days=30)
    one_year_ago = end_date_obj - timedelta(days=365)

    for i in range(len(activities)):
        checked_activity_daily_count.append([])
        checked_activity_streak.append([])
    current_date = start_date_obj
    while current_date <= end_date_obj:
        current_date_str = current_date.strftime(date_format)
        daily_counts = []
        for i, activity in enumerate(activities):
            count = habitsdb[activity].get(current_date_str, 0) * 10
            daily_counts.append(count)
            checked_activity_daily_count[i].append(count)
            if count > 0:
                streak = 1 if not checked_activity_streak[i] else checked_activity_streak[i][-1] + 1
            elif count < 0:
                streak = -1 if not checked_activity_streak[i] else checked_activity_streak[i][-1] - 1
            else:
                streak = 0
            checked_activity_streak[i].append(streak)        
        # Count the number of unique habits done on the current date
        unique_habits_count = sum(1 for count in daily_counts if count > 0)

        # Add the number of unique habits to the list
        unique_habits_count_per_day.append(unique_habits_count)

        current_date_str = current_date.strftime('%Y-%m-%d')
        total_days_since_not_zero = 0
        total_days_since_zero = 0
        # Calculate total points and count habits for the day
        # total_points = sum(adjust_habit_count(inner_dict.get(str(current_date), 0), habit) for habit, inner_dict in habitsdb.items())
        habits_count = sum(str(current_date) in inner_dict for _, inner_dict in habitsdb.items())
        daily_habits_count.append(habits_count)
        # List of habits for the day
        list_of_habits[current_date_str] = [habit for habit, inner_dict in habitsdb.items() if str(current_date) in inner_dict]
        #print(f'list of habits {current_date_str}', list_of_habits[current_date_str])
        # Initialize streak and antistreak dictionaries
        current_all_time_best_streaks = current_all_time_worst_antistreaks = {activity: 0 for activity in activities}
        habits_currently_all_time_besting = habits_currently_all_time_worsting = 0

        habits_currently_besting[current_date_str] = []
        habits_currently_worsting[current_date_str] = []
        currently_streaking_habits[current_date_str] = []
        currently_antistreaking_habits[current_date_str] = []

        best_streaks_sum = 0

        for activity in activities:
            inner_dict = habitsdb[activity]
            days_since_zero = get_days_since_zero_custom_date(inner_dict, current_date_str)
            total_days_since_zero += days_since_zero
            days_since_not_zero = get_days_since_not_zero_custom_date(inner_dict, current_date_str)
            total_days_since_not_zero += days_since_not_zero
            highest_days_since_zero_so_far[activity] = max(highest_days_since_zero_so_far[activity], days_since_zero)
            if highest_days_since_zero_so_far[activity] <= days_since_zero and days_since_zero != 0: #new for best ever
                current_all_time_best_streaks[activity] = days_since_zero #new for best ever
                habits_currently_all_time_besting += 1 #new for best ever
                habits_currently_besting[current_date.strftime('%Y-%m-%d')].append(activity +': '+str(days_since_zero)) #new for best ever
            highest_days_since_not_zero_so_far[activity] = max(highest_days_since_not_zero_so_far[activity], days_since_not_zero)
            if highest_days_since_not_zero_so_far[activity] <= days_since_not_zero and days_since_not_zero != 0: #new for worst ever
                current_all_time_worst_antistreaks[activity] = days_since_not_zero #new for worst ever
                habits_currently_all_time_worsting += 1 #new for worst ever
                habits_currently_worsting[current_date.strftime('%Y-%m-%d')].append(activity +': '+str(days_since_not_zero)) #new for worst ever
                #print('worst antistreak', activity, days_since_not_zero, current_date_str)
            if days_since_not_zero > 0:
                currently_antistreaking_habits[current_date.strftime('%Y-%m-%d')].append(activity +': '+str(days_since_not_zero)+'('+str(highest_days_since_not_zero_so_far[activity])+')')
            if days_since_zero > 0:
                currently_streaking_habits[current_date.strftime('%Y-%m-%d')].append(activity +': '+str(days_since_zero)+'('+str(highest_days_since_zero_so_far[activity])+')')

        best_streaks_sum = sum(current_all_time_best_streaks.values()) #new for best ever
        worst_antistreaks_sum = sum(current_all_time_worst_antistreaks.values()) #new for worst ever

        # Append total sum of best ever streaks to list
        daily_best_streaks.append(best_streaks_sum)
        daily_best_streak_habit_count.append(habits_currently_all_time_besting)

        # Append total sum of worst ever antistreaks to list
        daily_worst_anti_streaks.append(worst_antistreaks_sum)
        daily_worst_anti_streak_habit_count.append(habits_currently_all_time_worsting)

        # Calculate net streak
        net_streak = total_days_since_zero - total_days_since_not_zero

        # Update longest streak and antistreak records
        if total_days_since_zero > longest_streak_record['streak']:
            longest_streak_record = {'date': current_date_str, 'streak': total_days_since_zero}

        if total_days_since_not_zero > longest_antistreak_record['streak']:
            longest_antistreak_record = {'date': current_date_str, 'streak': total_days_since_not_zero}

        # Update highest and lowest net streak records
        if net_streak > highest_net_streak_record['net_streak']:
            highest_net_streak_record = {'date': current_date_str, 'net_streak': net_streak}

        if net_streak < lowest_net_streak_record['net_streak']:
            lowest_net_streak_record = {'date': current_date_str, 'net_streak': net_streak}

        # Handle the end date
        if current_date == end_date_obj:
            current_date_streak = total_days_since_zero
            current_date_antistreak = total_days_since_not_zero

        # Calculate total points for the day
        #total_points = sum(inner_dict.get(str(current_date), 0) for inner_dict in habitsdb.values())
        total_points = sum(adjust_habit_count(inner_dict.get(str(current_date), 0), habit) for habit, inner_dict in habitsdb.items())

        # Assuming total_points and unique_habits_count are calculated for the current_date

        # Update records for points
        update_records(current_date_str, total_points, 'points', 'highest', 'all_time')
        update_records(current_date_str, total_points, 'points', 'lowest', 'all_time')

        # Update records for unique habits
        update_records(current_date_str, unique_habits_count, 'unique_habits', 'highest', 'all_time')
        update_records(current_date_str, unique_habits_count, 'unique_habits', 'lowest', 'all_time')

        # Update records for streaks
        update_records(current_date_str, total_days_since_zero, 'streak', 'highest', 'all_time')
        update_records(current_date_str, total_days_since_zero, 'streak', 'lowest', 'all_time')

        # Update records for antistreaks
        update_records(current_date_str, total_days_since_not_zero, 'antistreak', 'highest', 'all_time')
        update_records(current_date_str, total_days_since_not_zero, 'antistreak', 'lowest', 'all_time')

        # Update records for net streaks
        update_records(current_date_str, net_streak, 'net_streak', 'highest', 'all_time')
        update_records(current_date_str, net_streak, 'net_streak', 'lowest', 'all_time')
        
        todays_date = datetime.now().date()

        # Check periods for both points and unique habits
        for period_key, start_date in [('last_week', one_week_ago), ('last_month', one_month_ago), ('last_year', one_year_ago)]:
            if current_date > start_date and current_date != todays_date:
                # Points
                update_records(current_date_str, total_points, 'points', 'highest', period_key)
                update_records(current_date_str, total_points, 'points', 'lowest', period_key)
                # Unique habits
                update_records(current_date_str, unique_habits_count, 'unique_habits', 'highest', period_key)
                update_records(current_date_str, unique_habits_count, 'unique_habits', 'lowest', period_key)
                # Streaks
                update_records(current_date_str, total_days_since_zero, 'streak', 'highest', period_key)
                update_records(current_date_str, total_days_since_zero, 'streak', 'lowest', period_key)
                # Antistreaks
                update_records(current_date_str, total_days_since_not_zero, 'antistreak', 'highest', period_key)
                update_records(current_date_str, total_days_since_not_zero, 'antistreak', 'lowest', period_key)
                # Net streaks
                update_records(current_date_str, net_streak, 'net_streak', 'highest', period_key)
                update_records(current_date_str, net_streak, 'net_streak', 'lowest', period_key)



        daily_total_points.append(total_points)

        # Convert the list to a pandas Series
        daily_total_points_series = pd.Series(daily_total_points)

        # Calculate the rolling average
        smoothed_total_points_weekly = daily_total_points_series.rolling(window=7).mean().tolist()
        smoothed_total_points_monthly = daily_total_points_series.rolling(window=30).mean().tolist()

        # Append daily data to lists
        daily_streaks.append(total_days_since_zero)
        daily_antistreaks.append(total_days_since_not_zero)
        daily_net_streaks.append(net_streak)

        current_date += timedelta(days=1)
    
    list_of_new_habits = {}    
    list_of_new_habits = find_new_habits(list_of_habits)
    # Initialize lists for the averages
    week_percentages_all = []
    month_percentages_all = []
    year_percentages_all = []
    overall_percentages_all = []

    for i in range(len(activities)):
        week_percentage = calculate_moving_percentage(dates, checked_activity_daily_count[i], 7)    # Last week
        month_percentage = calculate_moving_percentage(dates, checked_activity_daily_count[i], 30)  # Last month
        year_percentage = calculate_moving_percentage(dates, checked_activity_daily_count[i], 365)  # Last year
        overall_percentage = calculate_moving_percentage(dates, checked_activity_daily_count[i], 'overall')  # Overall

        week_percentages_all.append(week_percentage)
        month_percentages_all.append(month_percentage)
        year_percentages_all.append(year_percentage)
        overall_percentages_all.append(overall_percentage)

    # Calculate the averages
    week_average = [sum(x) / len(x) for x in zip(*week_percentages_all)]
    month_average = [sum(x) / len(x) for x in zip(*month_percentages_all)]
    year_average = [sum(x) / len(x) for x in zip(*year_percentages_all)]
    overall_average = [sum(x) / len(x) for x in zip(*overall_percentages_all)]

    if show_graph:
        # Create graph
        make_graph(daily_habits_count, list_of_habits, daily_net_streaks, daily_streaks, daily_best_streaks, daily_best_streak_habit_count, daily_antistreaks, daily_worst_anti_streaks, daily_worst_anti_streak_habit_count, daily_total_points, smoothed_total_points_weekly, smoothed_total_points_monthly, dates, activities, checked_activities, currently_streaking_habits, currently_antistreaking_habits, list_of_new_habits, habits_currently_besting, habits_currently_worsting, week_average, month_average, year_average, overall_average, unique_habits_count_per_day, checked_activity_daily_count, checked_activity_streak, week_percentages_all, month_percentages_all, year_percentages_all, overall_percentages_all, records)


    return (longest_streak_record, longest_antistreak_record, highest_net_streak_record, lowest_net_streak_record, 
            current_date_streak, current_date_antistreak, week_average, month_average, year_average, overall_average)


def calculate_moving_percentage(dates, daily_counts, timeframe):
    percentages = []
    window_counts = 0
    start_index = 0

    for end_index, current_date in enumerate(dates):
        # Add the current count to the window
        window_counts += 1 if daily_counts[end_index] > 0 else 0

        # For the 'overall' timeframe, consider all days up to the current date
        if timeframe != 'overall':
            # Remove counts that are outside the window
            while current_date - dates[start_index] > timedelta(days=timeframe):
                window_counts -= 1 if daily_counts[start_index] > 0 else 0
                start_index += 1

        # Calculate the percentage
        total_days = end_index - start_index + 1
        percentages.append((window_counts / total_days) * 100 if total_days > 0 else 0)

    return percentages

# Create custom hover text including date, value, and words from hover_dict
def create_hover_text(date_series, value_series, hover_dict):
    hover_texts = []
    for date, value in zip(date_series, value_series):
        date_str = date.strftime('%Y-%m-%d')
        words = '<br>'.join(hover_dict.get(date_str, []))  # Join words with line breaks
        hover_text = f'{date_str}<br>Value: {value}<br>{words}'
        hover_texts.append(hover_text)
    return hover_texts

# Initialize a dictionary to store the ordered list of streaks for each date
def get_streak_number(streak):
    return int(streak.split('(')[0].split(':')[1])

def add_trace_with_hover(fig, x, y, name, line_color, line_dash, hover_text, visible, sec):
    fig.add_trace(
        go.Scatter(
            x=x, 
            y=y,
            name=name, 
            line=dict(color=line_color, dash=line_dash),
            text=hover_text,
            hoverinfo='text',
            visible=visible
        ), 
        secondary_y=sec
    )

def make_graph(daily_habits_count, list_of_habits, daily_net_streaks, daily_streaks, daily_best_streaks, daily_best_streak_habit_count, daily_antistreaks, daily_worst_anti_streaks, daily_worst_anti_streak_habit_count, daily_total_points, smoothed_total_points_weekly, smoothed_total_points_monthly, dates, activities, checked_activities, currently_streaking_habits, currently_antistreaking_habits, list_of_new_habits, habits_currently_besting, habits_currently_worsting, week_average, month_average, year_average, overall_average, unique_habits_per_day, checked_activity_daily_count, checked_activity_streak, week_percentages_all, month_percentages_all, year_percentages_all, overall_percentages_all, records):

    ordered_streaks_per_date = {}
    # Iterate over the dates in currently_streaking_habits
    for date, streaks in currently_streaking_habits.items():
        ordered_streaks = sorted(streaks, key=get_streak_number, reverse=True)
        ordered_streaks_per_date[date] = ordered_streaks
    # Iterate over the dates in currently_antistreaking_habits
    ordered_antistreaks_per_date = {}
    for date, antistreaks in currently_antistreaking_habits.items():
        ordered_antistreaks = sorted(antistreaks, key=get_streak_number, reverse=True)
        ordered_antistreaks_per_date[date] = ordered_antistreaks
    # Create custom hover text for the list of habits
    custom_hover_text_for_list_of_habits = create_hover_text(dates, daily_habits_count, list_of_new_habits)
    custom_hover_text_best_streaks = create_hover_text(dates, daily_best_streaks, habits_currently_besting)
    custom_hover_text_best_streak_habit_count = create_hover_text(dates, daily_best_streak_habit_count, habits_currently_besting)
    custom_hover_text_worst_anti_streaks = create_hover_text(dates, daily_worst_anti_streaks, habits_currently_worsting)
    custom_hover_text_worst_anti_streak_habit_count = create_hover_text(dates, daily_worst_anti_streak_habit_count, habits_currently_worsting)
    custom_hover_text_currently_streaking_habits = create_hover_text(dates, daily_streaks, ordered_streaks_per_date)
    custom_hover_text_currently_antistreaking_habits = create_hover_text(dates, daily_antistreaks, ordered_antistreaks_per_date)

    # Create a figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    chart_visible=True
    if len(checked_activities) > 0:
        chart_visible = 'legendonly'

    add_trace_with_hover(fig, dates, daily_habits_count, 'Habits count', 'red', 'solid', custom_hover_text_for_list_of_habits, chart_visible, True)
    fig.add_trace(go.Scatter(x=dates, y=daily_net_streaks, name='Net streaks', line=dict(color='green'),visible=chart_visible), secondary_y=False)
    add_trace_with_hover(fig, dates, daily_streaks, 'Streaks', 'blue', 'solid', custom_hover_text_currently_streaking_habits, chart_visible, False)
    add_trace_with_hover(fig, dates, daily_best_streaks, 'Best streaks', 'blue', 'dash', custom_hover_text_best_streaks, chart_visible, False)
    add_trace_with_hover(fig, dates, daily_best_streak_habit_count, 'Best streak habits count', 'blue', 'dot', custom_hover_text_best_streak_habit_count, chart_visible, True)
    add_trace_with_hover(fig, dates, daily_antistreaks, 'Anti-streaks', 'yellow', 'solid', custom_hover_text_currently_antistreaking_habits, chart_visible, False)
    add_trace_with_hover(fig, dates, daily_worst_anti_streaks, 'Worst anti-streaks', 'yellow', 'dash', custom_hover_text_worst_anti_streaks, chart_visible, False)
    add_trace_with_hover(fig, dates, daily_worst_anti_streak_habit_count, 'Worst anti-streak habits count', 'yellow', 'dot', custom_hover_text_worst_anti_streak_habit_count, chart_visible, True)

    # Add traces for total points and smoothed total points
    fig.add_trace(go.Scatter(x=dates, y=daily_total_points, name='Daily Total Points', line=dict(color='white'), visible=chart_visible), secondary_y=True)
    fig.add_trace(go.Scatter(x=dates, y=smoothed_total_points_weekly, name='Weekly Smoothed Total Points', line=dict(color='black'), visible=chart_visible), secondary_y=True)
    fig.add_trace(go.Scatter(x=dates, y=smoothed_total_points_monthly, name='Monthly Smoothed Total Points', line=dict(color='gray'), visible=chart_visible), secondary_y=True)

    color_list = ["red", "orange", "green", "blue", "pink", "yellow", "white", "purple", "gray", "black"]

    for i in range(len(activities)):
        color = color_list[i % 10]
        chart_visible = 'legendonly'
        if activities[i] in checked_activities:
            chart_visible = True
        #print('activities[i]', activities[i])

        # #if i < 2:
        # # Calculate moving percentages for different timeframes for each activity
        week_percentage = calculate_moving_percentage(dates, checked_activity_daily_count[i], 7)    # Last week
        month_percentage = calculate_moving_percentage(dates, checked_activity_daily_count[i], 30)  # Last month
        year_percentage = calculate_moving_percentage(dates, checked_activity_daily_count[i], 365)  # Last year
        overall_percentage = calculate_moving_percentage(dates, checked_activity_daily_count[i], 'overall')  # Overall

        week_percentages_all.append(week_percentage)
        month_percentages_all.append(month_percentage)
        year_percentages_all.append(year_percentage)
        overall_percentages_all.append(overall_percentage)

        # Plotting
        fig.add_trace(go.Scatter(x=dates, y=checked_activity_daily_count[i], name=activities[i], line=dict(color=color), visible=chart_visible), secondary_y=True)
        fig.add_trace(go.Scatter(x=dates, y=checked_activity_streak[i], name=activities[i]+' streak', line=dict(color=color, dash='dash'), visible=chart_visible), secondary_y=False)

    #if i < 2:
        fig.add_trace(go.Scatter(x=dates, y=week_percentage, name=activities[i] + ' % week', line=dict(color=color, dash='dot'), visible=chart_visible), secondary_y=True)
        fig.add_trace(go.Scatter(x=dates, y=month_percentage, name=activities[i] + ' % month', line=dict(color=color, dash='dot'), visible=chart_visible), secondary_y=True)
        fig.add_trace(go.Scatter(x=dates, y=year_percentage, name=activities[i] + ' % year', line=dict(color=color, dash='dot'), visible=chart_visible), secondary_y=True)
        fig.add_trace(go.Scatter(x=dates, y=overall_percentage, name=activities[i] + ' % overall', line=dict(color=color, dash='dot'), visible=chart_visible), secondary_y=True)

    # Add traces for the averages
    fig.add_trace(go.Scatter(x=dates, y=unique_habits_per_day, name='Unique habits per day', line=dict(color='black'), visible=chart_visible), secondary_y=True)
    fig.add_trace(go.Scatter(x=dates, y=week_average, name='Average % week', line=dict(color='black', dash='dot'), visible=chart_visible), secondary_y=True)
    fig.add_trace(go.Scatter(x=dates, y=month_average, name='Average % month', line=dict(color='black', dash='dot'),visible=chart_visible), secondary_y=True)
    fig.add_trace(go.Scatter(x=dates, y=year_average, name='Average % year', line=dict(color='black', dash='dot'),visible=chart_visible), secondary_y=True)
    fig.add_trace(go.Scatter(x=dates, y=overall_average, name='Average % overall', line=dict(color='black', dash='dot'),visible=chart_visible), secondary_y=True)

    # Color different regions of the background
    colors = ['red', 'orange', 'green', 'blue', 'pink', 'yellow', 'white']
    #ranges = [0.5, 13.5, 20.5, 30.5, 41.5, 48.5, 55.5, 62.5] CHANGED TO 31 BECAUSE THATS WHEN THEME CHANGED
    ranges = [0.5, 13.5, 20.5, 31, 41.5, 48.5, 55.5, 62.5]

    # Set x-axis title
    fig.update_xaxes(title_text="Date")

    # Set y-axes titles
    fig.update_yaxes(title_text="Streaks and Total Points", secondary_y=False)

    # Update the secondary y-axis to have ticks based on 'ranges' list
    fig.update_yaxes(title_text="Habits count", tickvals=ranges, secondary_y=True)

    for i in range(len(ranges) - 1):
        fig.add_hrect(
            y0=ranges[i], y1=ranges[i+1],
            fillcolor=colors[i], opacity=0.5,
            layer="below", line_width=0,
            secondary_y=True  # This ensures the coloring is based on the secondary y-axis
        )

    # Add an annotation on the right, centered vertically
    # fig.add_annotation(
    #     x=1.07,   # X position slightly more than 1 (right of the plot area)
    #     y=0.5,    # Y position at 0.5 to center vertically
    #     xref="paper",  # Reference to the entire figure's area
    #     yref="paper",  # Reference to the entire figure's area
    #     text="Interesting and useful stats",  # Your note text
    #     showarrow=False,
    #     align="left"  # Align text to the left of the x position
    # )

    # Adjust the margins to ensure there's space for the annotation
    fig.update_layout(margin=dict(r=120))  # Increase right margin

    # Update layout and show plot
    fig.update_layout(title_text="Streaks, Habits Count, and Total Points Over Time")
    #fig.show()

    legend_text = [trace.name for trace in fig.data]
    stats = ""
    for text in legend_text:
        stats += text + '\n'

    stats = stats.split('\n')
    stats = ['['+str(i) + '] ' + stats[i] + ' (off)' for i in range(len(stats))]
    stats = '\n'.join(stats)
    print(stats)


    highest_date = max(currently_streaking_habits.keys(), key=lambda date: datetime.strptime(date, '%Y-%m-%d'))
    ordered_antistreaks = sorted(currently_antistreaking_habits[highest_date], key=get_streak_number, reverse=True)
    antistreak_list_longest_ordered = '\n'.join(ordered_antistreaks)
    # app.run_server(debug=True)
    dash_thread = threaded_dash_app.DashApp(fig, ordered_streaks_per_date, ordered_antistreaks_per_date, dates, daily_streaks, daily_antistreaks, records)
    dash_thread.start()
    url = "http://127.0.0.1:8050"
    webbrowser.get('firefox').open_new_tab(url)

def get_streak_numbers(show_graph, checked_activities):
    
    # Example usage
    start_date = '2022-09-03'
    end_date = datetime.now().strftime('%Y-%m-%d')

    longest_streak_record, longest_antistreak_record, highest_net_streak_record, lowest_net_streak_record, current_date_streak, current_date_antistreak, week_average, month_average, year_average, overall_average = find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb, show_graph, checked_activities)

    print('Longest streak date:', longest_streak_record['date'])
    print('Longest streak:', longest_streak_record['streak'])

    print('Longest antistreak date:', longest_antistreak_record['date'])
    print('Longest antistreak:', longest_antistreak_record['streak'])

    print('Current streak:', current_date_streak)
    print('Current antistreak:', current_date_antistreak)

    print('checked_activities', checked_activities)

    return(current_date_streak, current_date_antistreak, longest_streak_record['streak'], longest_antistreak_record['streak'],highest_net_streak_record['net_streak'], lowest_net_streak_record['net_streak'], week_average, month_average, year_average, overall_average)