"""
Handles all read/write operations for habitsdb.txt.
Matches the Android app's HabitsRepository.kt.
"""
import json
import os
from datetime import date, timedelta
from typing import List, Optional

from habit_models import AppSettings, HabitsDatabase, HABIT_ORDER, Habit
from habit_calculator import build_habit, date_string, parse_date


def load_database(path: str) -> HabitsDatabase:
    """
    Reads and parses the habits JSON file.
    Returns an empty dict if the file is missing or malformed.
    """
    path = os.path.expanduser(path)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_database(path: str, db: HabitsDatabase) -> None:
    """Writes the habits database as formatted JSON."""
    path = os.path.expanduser(path)
    # Use sort_keys=False for speed — entries are already sorted by date
    with open(path, 'w') as f:
        json.dump(db, f, indent=4)


def ensure_days_exist(path: str, today: Optional[date] = None) -> HabitsDatabase:
    """
    Ensures every habit in the database has an entry for today.
    Only fills in the gap between the latest recorded date and today for each habit.
    Returns the updated database (and saves it if any dates were added).
    """
    if today is None:
        today = date.today()
    db = load_database(path)
    today_str = date_string(today)
    any_added = False

    # Only process habits already in the DB — don't create entries for all HABIT_ORDER
    for name in list(db.keys()):
        entries = db[name]
        if not entries:
            entries[today_str] = 0
            any_added = True
            continue

        latest_existing = max(entries.keys())
        if latest_existing < today_str:
            cursor_date = parse_date(latest_existing)
            if cursor_date is None:
                continue
            cursor_date += timedelta(days=1)
            while cursor_date <= today:
                ds = date_string(cursor_date)
                if ds not in entries:
                    entries[ds] = 0
                    any_added = True
                cursor_date += timedelta(days=1)

    if any_added:
        save_database(path, db)
    return db


def apply_increment_to_db(
    db: HabitsDatabase,
    habit_name: str,
    amount: int,
    target_date: date
) -> HabitsDatabase:
    """
    Applies an increment to db in memory only — no disk I/O.
    Returns the updated database.
    """
    date_str = date_string(target_date)
    mutable = dict(db)
    habit_entries = dict(mutable.get(habit_name, {}))
    habit_entries[date_str] = habit_entries.get(date_str, 0) + amount
    mutable[habit_name] = dict(sorted(habit_entries.items()))
    return mutable


def persist_database(path: str, db: HabitsDatabase) -> None:
    """Writes db to disk. Call this after an optimistic in-memory update."""
    save_database(path, db)


def increment_habit(path: str, habit_name: str, amount: int, target_date: Optional[date] = None) -> HabitsDatabase:
    """
    Increments the count for a habit on target_date by amount, then saves.
    Performs atomic read-modify-write.
    """
    if target_date is None:
        target_date = date.today()
    db = load_database(path)
    date_str = date_string(target_date)
    habit_entries = dict(db.get(habit_name, {}))
    current = habit_entries.get(date_str, 0)
    habit_entries[date_str] = current + amount
    db[habit_name] = dict(sorted(habit_entries.items()))
    save_database(path, db)
    return db


def add_habit_to_file(path: str, habit_name: str, today: Optional[date] = None) -> None:
    """
    Adds a new habit to the JSON database file.
    Reads the file, adds the habit with today's date = 0 if not already present, then saves.
    """
    if today is None:
        today = date.today()
    today_str = date_string(today)
    db = load_database(path)
    if habit_name not in db:
        db[habit_name] = {today_str: 0}
        save_database(path, db)


def build_habit_list(
    db: HabitsDatabase,
    settings: AppSettings,
    target_date: Optional[date] = None
) -> List[Habit]:
    """
    Builds the display Habit list from raw database + settings for a specific target_date.
    """
    if target_date is None:
        target_date = date.today()
    order = settings.habit_order if settings.habit_order else HABIT_ORDER
    habits = []
    for name in order:
        entries = db.get(name, {})
        habit = build_habit(
            name=name,
            entries=entries,
            use_custom_input=name in settings.custom_input_habits,
            divider=settings.habit_dividers.get(name, 1),
            target_date=target_date
        )
        habits.append(habit)
    return habits
