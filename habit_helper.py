import math

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