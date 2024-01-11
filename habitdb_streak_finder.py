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

def find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb, show_graph):
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

    current_date_streak = 0
    current_date_antistreak = 0

    # Create lists to store daily data
    daily_streaks = []
    daily_antistreaks = []
    daily_net_streaks = []

    daily_total_points = []

    #longest_streaks = {activity: 0 for activity in activities} #new for best ever

    daily_best_streaks = [] #new for best ever

    daily_best_streak_habit_count = [] #new for best ever

    highest_days_since_zero_so_far = {activity: 0 for activity in activities}

    daily_habits_count = []

    current_date = start_date_obj
    while current_date <= end_date_obj:
        current_date_str = current_date.strftime(date_format)
        total_days_since_not_zero = 0
        total_days_since_zero = 0

        # Calculate total points for the day
        total_points = sum(adjust_habit_count(inner_dict.get(str(current_date), 0), habit) for habit, inner_dict in habitsdb.items())

        # Count the number of habits available for the day
        habits_count = sum(1 for habit, inner_dict in habitsdb.items() if str(current_date) in inner_dict)
        daily_habits_count.append(habits_count)

        current_all_time_best_streaks = {activity: 0 for activity in activities} #new for best ever
        habits_currently_all_time_besting = 0 #new for best ever

        best_streaks_sum = 0 #new for best ever
        for activity in activities:
            inner_dict = habitsdb[activity]
            days_since_not_zero = get_days_since_not_zero_custom_date(inner_dict, current_date_str)
            total_days_since_not_zero += days_since_not_zero
            days_since_zero = get_days_since_zero_custom_date(inner_dict, current_date_str)

            total_days_since_zero += days_since_zero

            best_streak_up_until_current_date = get_best_streak_custom_date(inner_dict, current_date_str)
            highest_days_since_zero_so_far[activity] = max(highest_days_since_zero_so_far[activity], days_since_zero)
            if highest_days_since_zero_so_far[activity] <= days_since_zero: #new for best ever
                current_all_time_best_streaks[activity] = days_since_zero #new for best ever
                habits_currently_all_time_besting += 1 #new for best ever

        best_streaks_sum = sum(current_all_time_best_streaks.values()) #new for best ever

        # Append total sum of best ever streaks to list
        daily_best_streaks.append(best_streaks_sum)
        daily_best_streak_habit_count.append(habits_currently_all_time_besting)

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

        daily_total_points.append(total_points)

        # Append daily data to lists
        daily_streaks.append(total_days_since_zero)
        daily_antistreaks.append(total_days_since_not_zero)
        daily_net_streaks.append(net_streak)

        current_date += timedelta(days=1)

    if show_graph:
        # Create graph
        
        

        # Convert the list to a pandas Series
        daily_total_points_series = pd.Series(daily_total_points)

        # Calculate the rolling average
        smoothed_total_points_weekly = daily_total_points_series.rolling(window=7).mean().tolist()
        smoothed_total_points_monthly = daily_total_points_series.rolling(window=30).mean().tolist()

        fig1, ax1 = plt.subplots()

        color = 'tab:blue'
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Streaks', color=color)
        # When plotting, use the dates for the x-axis
        #ax1.plot(dates, daily_habits_count, color='tab:red', label='Habits count')
        ax1.plot(dates, daily_streaks, color='tab:blue', label='Streaks')
        ax1.plot(dates, daily_antistreaks, color='tab:orange', label='Anti-streaks')
        ax1.plot(dates, daily_net_streaks, color='tab:green', label='Net streaks')
        ax1.plot(dates, daily_best_streaks, color='tab:purple', label='Best streaks')
        #ax1.plot(dates, daily_worst_antistreaks, color='tab:yellow', label='Worst antistreaks')

        # Create a second y-axis
        ax1b = ax1.twinx()

        # When plotting, use the dates for the x-axis and daily_habits_count for the y-axis
        ax1b.plot(dates, daily_habits_count, color='tab:red', label='Habits count')
        ax1b.plot(dates, daily_best_streak_habit_count, color='tab:gray', label='Best streak habits count')

        # Set the y-axis label
        ax1b.set_ylabel('Habits count', color='tab:red')

        # Set the y-axis tick parameters
        ax1b.tick_params(axis='y', labelcolor='tab:red')

        # Add a legend
        ax1b.legend(loc='upper right')

        # Set the x-axis ticks and labels
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))  # set x-ticks to be every 3 months
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))  # format x-ticks as 'MM/YY'

        ax1.tick_params(axis='y', labelcolor='tab:blue')
        ax1.legend()  # Add a legend

        fig1.tight_layout()  # otherwise the right y-label is slightly clipped
        plt.show()





        # # Create a figure with secondary y-axis
        # fig = make_subplots(specs=[[{"secondary_y": True}]])

        # # Add traces for streaks
        # fig.add_trace(go.Scatter(x=dates, y=daily_streaks, name='Streaks', line=dict(color='blue')), secondary_y=False)
        # fig.add_trace(go.Scatter(x=dates, y=daily_antistreaks, name='Anti-streaks', line=dict(color='orange')), secondary_y=False)
        # fig.add_trace(go.Scatter(x=dates, y=daily_net_streaks, name='Net streaks', line=dict(color='green')), secondary_y=False)
        # fig.add_trace(go.Scatter(x=dates, y=daily_best_streaks, name='Best streaks', line=dict(color='purple')), secondary_y=False)

        # # Add traces for habit counts
        # fig.add_trace(go.Scatter(x=dates, y=daily_habits_count, name='Habits count', line=dict(color='red')), secondary_y=True)
        # fig.add_trace(go.Scatter(x=dates, y=daily_best_streak_habit_count, name='Best streak habits count', line=dict(color='gray')), secondary_y=True)

        # # Set x-axis title
        # fig.update_xaxes(title_text="Date")

        # # Set y-axes titles
        # fig.update_yaxes(title_text="Streaks", secondary_y=False)
        # fig.update_yaxes(title_text="Habits count", secondary_y=True)

        # # Update layout and show plot
        # fig.update_layout(title_text="Streaks and Habits Count Over Time")
        # fig.show()



        # Create a figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add traces for streaks
        fig.add_trace(go.Scatter(x=dates, y=daily_streaks, name='Streaks', line=dict(color='blue')), secondary_y=False)
        fig.add_trace(go.Scatter(x=dates, y=daily_antistreaks, name='Anti-streaks', line=dict(color='orange')), secondary_y=False)
        fig.add_trace(go.Scatter(x=dates, y=daily_net_streaks, name='Net streaks', line=dict(color='green')), secondary_y=False)
        fig.add_trace(go.Scatter(x=dates, y=daily_best_streaks, name='Best streaks', line=dict(color='purple')), secondary_y=False)

        # Add traces for habit counts
        fig.add_trace(go.Scatter(x=dates, y=daily_habits_count, name='Habits count', line=dict(color='red')), secondary_y=True)
        fig.add_trace(go.Scatter(x=dates, y=daily_best_streak_habit_count, name='Best streak habits count', line=dict(color='gray')), secondary_y=True)

        # Add traces for total points and smoothed total points
        fig.add_trace(go.Scatter(x=dates, y=daily_total_points, name='Daily Total Points', line=dict(color='white')), secondary_y=True)
        fig.add_trace(go.Scatter(x=dates, y=smoothed_total_points_weekly, name='Weekly Smoothed Total Points', line=dict(color='black')), secondary_y=True)
        fig.add_trace(go.Scatter(x=dates, y=smoothed_total_points_monthly, name='Monthly Smoothed Total Points', line=dict(color='gray')), secondary_y=True)

        # Color different regions of the background
        colors = ['red', 'orange', 'green', 'blue', 'pink', 'yellow', 'white']
        ranges = [0.5, 13.5, 20.5, 30.5, 41.5, 48.5, 55.5, 62.5]

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

        # Update layout and show plot
        fig.update_layout(title_text="Streaks, Habits Count, and Total Points Over Time")
        fig.show()





        # Create a new figure for the smoothed total points
        fig2, ax2 = plt.subplots()

        ax2.set_ylabel('Total points', color='black')  # Set the y-axis label to 'Total points' and its color to black
        ax2.tick_params(axis='y', labelcolor='black')  # Set the color of the y-axis ticks to black

        # When plotting, use the dates for the x-axis
        ax2.plot(dates, daily_total_points, color='white', linestyle='-', label='Daily total points')  # solid line
        ax2.plot(dates, smoothed_total_points_weekly, color='black', linestyle='-', label='Weekly smoothed total points')  # dashed line
        ax2.plot(dates, smoothed_total_points_monthly, color='gray', linestyle='-', label='Monthly smoothed total points')  # dash-dot line

        # Set the x-axis ticks and labels
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))  # set x-ticks to be every 3 months
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))  # format x-ticks as 'MM/YY'

        #ranges = [0, 13, 20, 30, 41, 48, 55, 62]
        ranges = [0.5, 13.5, 20.5, 30.5, 41.5, 48.5, 55.5, 62.5]
        #ranges = [1, 14, 21, 31, 42, 49, 56, 63]
        colors = ['red', 'orange', 'green', 'blue', 'pink', 'yellow', 'white']

        # Set the y-axis ticks
        ax2.set_yticks(ranges)

        # Color different regions of the background
        for i in range(len(ranges) - 1):
            ax2.axhspan(ranges[i], ranges[i+1], facecolor=colors[i], alpha=0.5)

        ax2.legend()  # Add a legend

        fig2.tight_layout()  # otherwise the right y-label is slightly clipped
        plt.show()

    return (longest_streak_record, longest_antistreak_record, 
            highest_net_streak_record, lowest_net_streak_record, 
            current_date_streak, current_date_antistreak)


def get_streak_numbers(show_graph):
    # Example usage
    start_date = '2022-09-03'
    end_date = datetime.now().strftime('%Y-%m-%d')

    longest_streak_record, longest_antistreak_record, highest_net_streak_record, lowest_net_streak_record, current_date_streak, current_date_antistreak = find_longest_streaks_and_antistreaks(start_date, end_date, activities, habitsdb, show_graph)

    print('Longest streak date:', longest_streak_record['date'])
    print('Longest streak:', longest_streak_record['streak'])

    print('Longest antistreak date:', longest_antistreak_record['date'])
    print('Longest antistreak:', longest_antistreak_record['streak'])

    print('Current streak:', current_date_streak)
    print('Current antistreak:', current_date_antistreak)

    return(current_date_streak, current_date_antistreak, longest_streak_record['streak'], longest_antistreak_record['streak'],highest_net_streak_record['net_streak'], lowest_net_streak_record['net_streak'])