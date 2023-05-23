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
