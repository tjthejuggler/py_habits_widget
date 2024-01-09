from datetime import datetime, timedelta

import os
import json
import math
#import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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

    longest_streaks = {activity: 0 for activity in activities} #new for best ever

    daily_best_streaks = [] #new for best ever

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

        best_streaks_sum = 0 #new for best ever
        for activity in activities:
            inner_dict = habitsdb[activity]
            days_since_not_zero = get_days_since_not_zero_custom_date(inner_dict, current_date_str)
            total_days_since_not_zero += days_since_not_zero
            days_since_zero = get_days_since_zero_custom_date(inner_dict, current_date_str)
            total_days_since_zero += days_since_zero

            #I DONT THINK THIS IS ACTUALLY DOING WHAT I WANT IT TO DO
            #IT SHOULD BE GETTING THE TOTAL OF CURRENT ALL TIME BEST STREAKS
            #ANOTHER THING I WANT IS TO GET THE TOTAL OF HABITS IM ALLTIME BESTING AT ANY GIVEN TIME
            longest_streaks[activity] = max(longest_streaks[activity], days_since_zero) #new for best ever
            best_streaks_sum += longest_streaks[activity] #new for best ever

        # Append total sum of best ever streaks to list
        daily_best_streaks.append(best_streaks_sum)

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



        # # Plot daily total points
        # color = 'white'
        # ax2.plot(daily_total_points, color=color, linestyle='-', label='Daily total points')  # solid line

        # # Plot weekly smoothed total points
        # color = 'black'
        # ax2.plot(smoothed_total_points_weekly, color=color, linestyle='-', label='Weekly smoothed total points')  # dashed line

        # # Plot monthly smoothed total points
        # color = 'gray'
        # ax2.plot(smoothed_total_points_monthly, color=color, linestyle='-', label='Monthly smoothed total points')  # dash-dot line
        # # Define the total habit count ranges
        ranges = [0, 13, 20, 30, 41, 48, 55, 62]
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