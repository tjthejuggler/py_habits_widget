import pandas as pd
from datetime import datetime, timedelta

def get_days_since_zero(inner_dict):
    days_since_zero = None
    sorted_dates = sorted(inner_dict.keys(), reverse=True)
    for index, date_str in enumerate(sorted_dates):
        #index = max(1, index)
        if inner_dict[date_str] == 0:
            days_since_zero = index
            break
    if days_since_zero is None:
        days_since_zero = len(sorted_dates)
    return days_since_zero

def get_days_since_zero_minus(inner_dict):
    days_since_zero = None
    sorted_dates = sorted(inner_dict.keys(), reverse=True)
    for index, date_str in enumerate(sorted_dates[1:]):
        #index = max(1, index)
        if inner_dict[date_str] == 0:
            days_since_zero = index
            break
    if days_since_zero is None:
        days_since_zero = len(sorted_dates)
    return days_since_zero

def get_days_since_not_zero(inner_dict):
    days_since_not_zero = None
    sorted_dates = sorted(inner_dict.keys(), reverse=True)
    for index, date_str in enumerate(sorted_dates):
        if inner_dict[date_str] != 0:
            days_since_not_zero = index
            break
    if days_since_not_zero is None:
        days_since_not_zero = len(sorted_dates)
    return days_since_not_zero

def get_longest_streak(inner_dict):
    longest_streak = 0
    current_streak = 0
    for date_str, value in sorted(inner_dict.items()):
        if value != 0:
            current_streak += 1
        else:
            longest_streak = max(longest_streak, current_streak)
            current_streak = 0
    longest_streak = max(longest_streak, current_streak)
    return longest_streak

def get_all_time_high_rolling(inner_dict, time_period=7):
    
    data_series = pd.Series(inner_dict)

    # Sort the series by date
    data_series = data_series.sort_index()

    # Calculate the rolling weekly average
    n_days_averages = data_series.rolling(window=time_period).mean()
    
    date_of_highest_rolling_n_days_average = n_days_averages.idxmax()

    # Find the highest rolling weekly average
    highest_rolling_n_days_average = n_days_averages.max()

    highest_rolling_n_days_average = round(highest_rolling_n_days_average, 2)

    return date_of_highest_rolling_n_days_average, highest_rolling_n_days_average

def get_average_of_last_n_days(inner_dict, n_days):
    inner_dict = {datetime.strptime(key, "%Y-%m-%d"): value for key, value in inner_dict.items()}

    data_series = pd.Series(inner_dict)

    # Sort the series by date
    data_series = data_series.sort_index()

    # Get the date 7 days ago
    n_days_ago = datetime.now() - timedelta(days=n_days)

    # Get the values from the last 7 days
    last_n_days_values = data_series[n_days_ago:]

    # Calculate the average of the last 7 days' values
    average_last_n_days = last_n_days_values.mean()

    average_last_n_days = round(average_last_n_days, 2)

    return average_last_n_days