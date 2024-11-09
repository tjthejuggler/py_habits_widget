import json
from datetime import datetime, timedelta

def calculate_habit_stats(dates_dict):
    # Convert dates to datetime objects and sort
    dates = [(datetime.strptime(date, '%Y-%m-%d'), value) 
             for date, value in dates_dict.items()]
    dates.sort()
    
    if not dates:
        return {
            "days_since_not_zero": 0,
            "days_since_zero": 0,
            "longest_streak": 0
        }

    # Use the last date in the sequence instead of today
    reference_date = dates[-1][0]
    
    # Get the most recent entry
    last_date, last_value = dates[-1]
    
    # If the most recent entry is 0, find days since last non-zero
    if last_value == 0:
        days_since_not_zero = 0
        for date, value in reversed(dates):
            if value != 0:
                days_since_not_zero = (reference_date - date).days
                break
        days_since_zero = 0
    # If the most recent entry is non-zero, find days since last zero
    else:
        days_since_zero = 0
        for date, value in reversed(dates):
            if value == 0:
                days_since_zero = (reference_date - date).days
                break
        days_since_not_zero = 0
            
    # Calculate longest streak
    current_streak = 0
    longest_streak = 0
    
    for i in range(len(dates)):
        current_date, value = dates[i]
        
        if value != 0:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0
            
    return {
        "days_since_not_zero": days_since_not_zero,
        "days_since_zero": days_since_zero,
        "longest_streak": longest_streak
    }

try:
    # Read the contents of habitsdb.txt
    print("\nReading habitsdb.txt...")
    with open('/home/twain/noteVault/habitsdb.txt', 'r') as db_file:
        db_data = json.load(db_file)
    print(f"Found {len(db_data)} habits in main database")

    # Calculate stats for all habits
    stats = {}
    print("\nProcessing habits:")
    for habit in db_data:
        print(f"Processing {habit}...")
        stats[habit] = calculate_habit_stats(db_data[habit])

    # Sort the stats by habit name
    stats = dict(sorted(stats.items()))
    print(f"\nTotal habits processed: {len(stats)}")

    # Write the stats to habitsdb_without_phone_totals.txt
    print("Writing results to habitsdb_without_phone_totals.txt...")
    with open('habitsdb_without_phone_totals.txt', 'w') as f:
        json.dump(stats, f, indent=4)
    print("Done!")

except Exception as e:
    print(f"Error occurred: {str(e)}")
