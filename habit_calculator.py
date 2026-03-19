"""
Pure calculation functions for habit stats, matching the Android app's HabitCalculator.kt.
"""
from datetime import date, timedelta, datetime
from typing import Dict, Optional, Tuple
from habit_models import Habit, RollingHigh, apply_divider


def today_string() -> str:
    """Returns today's date string in YYYY-MM-DD format."""
    return date.today().strftime('%Y-%m-%d')


def date_string(d: date) -> str:
    """Formats any date as YYYY-MM-DD."""
    return d.strftime('%Y-%m-%d')


def parse_date(s: str) -> Optional[date]:
    """Parses a YYYY-MM-DD string back to a date, or None if invalid."""
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def get_count_for_date(entries: Dict[str, int], d: date) -> int:
    """Gets the raw count for a specific date from a habit's date map."""
    return entries.get(date_string(d), 0)


def get_today_count(entries: Dict[str, int]) -> int:
    """Gets the raw count for today from a habit's date map."""
    return get_count_for_date(entries, date.today())


def calculate_streak_display(entries: Dict[str, int]) -> int:
    """
    Calculates current streak (positive) or antistreak (negative) matching desktop logic.
    Works directly with sorted entries (habitsdb.txt already has every day filled in).
    
    Desktop logic (streak_helper.py):
      get_days_since_not_zero: index of first non-zero from most-recent end
      get_days_since_zero_minus: index of first zero from most-recent end, SKIPPING index 0
      if days_since_not_zero < 2: left_number = days_since_zero_minus (positive streak)
      else:                        left_number = -days_since_not_zero (negative antistreak)
    """
    if not entries:
        return 0
    sorted_keys = sorted(entries.keys(), reverse=True)

    # days_since_not_zero: index of first non-zero entry from most recent
    days_since_not_zero = len(sorted_keys)
    for i, key in enumerate(sorted_keys):
        if entries[key] != 0:
            days_since_not_zero = i
            break

    if days_since_not_zero < 2:
        # Currently on a streak — use get_days_since_zero_minus:
        # skip index 0 (most recent), find first zero in the rest
        days_since_zero_minus = len(sorted_keys)
        for i, key in enumerate(sorted_keys[1:]):
            if entries[key] == 0:
                days_since_zero_minus = i
                break
        return days_since_zero_minus
    else:
        # On an antistreak
        return -days_since_not_zero


def calculate_longest_streak(entries: Dict[str, int]) -> int:
    """
    Calculates the longest streak of consecutive non-zero days.
    Works directly with sorted entries (habitsdb.txt already has every day filled in).
    """
    if not entries:
        return 0
    longest = 0
    current = 0
    for key in sorted(entries.keys()):
        if entries[key] != 0:
            current += 1
        else:
            if current > longest:
                longest = current
            current = 0
    return max(longest, current)


def calculate_all_time_high_day(entries: Dict[str, int]) -> Tuple[int, str]:
    """
    Returns the all-time high single-day count and the date it occurred.
    """
    if not entries:
        return (0, "")
    max_key = max(entries, key=lambda k: entries[k])
    return (entries[max_key], max_key)


def get_most_recent_value(entries: Dict[str, int]) -> int:
    """Returns the most recent entry's raw value."""
    if not entries:
        return 0
    last_key = sorted(entries.keys())[-1]
    return entries.get(last_key, 0)


def get_average_of_last_n_days(entries: Dict[str, int], n_days: int, today: Optional[date] = None) -> float:
    """
    Calculates the average of the last N days from today.
    Matches desktop get_average_of_last_n_days().
    """
    if not entries:
        return 0.0
    if today is None:
        today = date.today()
    cutoff = today - timedelta(days=n_days)
    cutoff_str = date_string(cutoff)
    today_str = date_string(today)
    relevant = {k: v for k, v in entries.items() if cutoff_str < k <= today_str}
    if not relevant:
        return 0.0
    return sum(relevant.values()) / len(relevant)


def get_all_time_high_rolling(entries: Dict[str, int], window_size: int) -> RollingHigh:
    """
    Calculates the all-time high rolling N-day average and the date it peaked.
    Uses an efficient sliding window sum (O(n) instead of O(n*window)).
    """
    if not entries:
        return RollingHigh(0.0, "")
    sorted_items = sorted(entries.items(), key=lambda x: x[0])
    n = len(sorted_items)
    if n < window_size:
        avg = sum(v for _, v in sorted_items) / n
        return RollingHigh(
            value=round(avg, 2),
            date=sorted_items[-1][0]
        )

    # Sliding window: O(n)
    window_sum = sum(sorted_items[i][1] for i in range(window_size))
    best_sum = window_sum
    best_idx = window_size - 1

    for i in range(window_size, n):
        window_sum += sorted_items[i][1] - sorted_items[i - window_size][1]
        if window_sum > best_sum:
            best_sum = window_sum
            best_idx = i

    best_avg = best_sum / window_size
    return RollingHigh(value=round(best_avg, 2), date=sorted_items[best_idx][0])


def build_habit(
    name: str,
    entries: Dict[str, int],
    use_custom_input: bool = False,
    divider: int = 1,
    target_date: Optional[date] = None,
    compute_full_stats: bool = False
) -> Habit:
    """
    Builds a Habit display object from raw database entries for a specific target_date.
    
    When compute_full_stats=False (default), only computes the stats needed for the grid:
      today_count, raw_today_count, current_streak, longest_streak, all_time_high_day
    
    When compute_full_stats=True, also computes rolling averages and all-time highs
    needed for the info panel.
    """
    if target_date is None:
        target_date = date.today()
    target_date_str = date_string(target_date)

    # Only include entries up to and including target_date
    filtered = {k: v for k, v in entries.items() if k <= target_date_str}

    raw_count = get_count_for_date(filtered, target_date)
    count_for_date = apply_divider(raw_count, divider)
    streak_display = calculate_streak_display(filtered)
    longest_streak = calculate_longest_streak(filtered)
    ath_day_val, ath_day_date = calculate_all_time_high_day(filtered)

    habit = Habit(
        name=name,
        today_count=count_for_date,
        raw_today_count=raw_count,
        current_streak=streak_display,
        longest_streak=longest_streak,
        all_time_high_day=ath_day_val,
        all_time_high_day_date=ath_day_date,
        use_custom_input=use_custom_input,
        divider=divider,
        current_day_value=raw_count,
    )

    if compute_full_stats:
        habit.current_day_value = get_most_recent_value(filtered)
        habit.avg_last_7_days = get_average_of_last_n_days(filtered, 7, target_date)
        habit.avg_last_30_days = get_average_of_last_n_days(filtered, 30, target_date)
        habit.avg_last_365_days = get_average_of_last_n_days(filtered, 365, target_date)
        habit.all_time_high_week = get_all_time_high_rolling(filtered, 7)
        habit.all_time_high_month = get_all_time_high_rolling(filtered, 30)
        habit.all_time_high_year = get_all_time_high_rolling(filtered, 365)

    return habit
