"""
Persists app settings using a JSON file, matching the Android app's SettingsRepository.kt.
On desktop we use a simple JSON file instead of Android DataStore.
"""
import json
import os
from typing import Optional

from habit_models import AppSettings, HabitScreen, DEFAULT_CUSTOM_INPUT_HABITS

SETTINGS_FILE = os.path.expanduser('~/.config/py_habits_widget/settings.json')


def _ensure_dir():
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)


def load_settings() -> AppSettings:
    """Loads settings from the JSON file. Returns defaults if missing/malformed."""
    try:
        with open(SETTINGS_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return AppSettings()

    screens = []
    for s in data.get('habit_screens', []):
        screens.append(HabitScreen(
            id=s.get('id', ''),
            name=s.get('name', ''),
            habit_names=s.get('habit_names', [])
        ))

    return AppSettings(
        custom_input_habits=set(data.get('custom_input_habits', list(DEFAULT_CUSTOM_INPUT_HABITS))),
        habit_order=data.get('habit_order', []),
        habit_screens=screens,
        active_screen_index=data.get('active_screen_index', 0),
        max_one_habits=set(data.get('max_one_habits', [])),
        text_input_habits=set(data.get('text_input_habits', [])),
        text_input_options_habits=set(data.get('text_input_options_habits', [])),
        text_input_file_uris=data.get('text_input_file_uris', {}),
        habit_icons=data.get('habit_icons', {}),
        dated_entry_habits=set(data.get('dated_entry_habits', [])),
        dated_entry_file_uris=data.get('dated_entry_file_uris', {}),
        dated_entry_file_sizes=data.get('dated_entry_file_sizes', {}),
        habit_dividers=data.get('habit_dividers', {})
    )


def save_settings(settings: AppSettings) -> None:
    """Saves all settings to the JSON file."""
    _ensure_dir()
    screens_data = []
    for s in settings.habit_screens:
        screens_data.append({
            'id': s.id,
            'name': s.name,
            'habit_names': s.habit_names
        })

    data = {
        'custom_input_habits': sorted(settings.custom_input_habits),
        'habit_order': settings.habit_order,
        'habit_screens': screens_data,
        'active_screen_index': settings.active_screen_index,
        'max_one_habits': sorted(settings.max_one_habits),
        'text_input_habits': sorted(settings.text_input_habits),
        'text_input_options_habits': sorted(settings.text_input_options_habits),
        'text_input_file_uris': settings.text_input_file_uris,
        'habit_icons': settings.habit_icons,
        'dated_entry_habits': sorted(settings.dated_entry_habits),
        'dated_entry_file_uris': settings.dated_entry_file_uris,
        'dated_entry_file_sizes': settings.dated_entry_file_sizes,
        'habit_dividers': settings.habit_dividers
    }

    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)


def save_habit_screens(screens: list) -> None:
    """Saves just the habit screens."""
    settings = load_settings()
    settings.habit_screens = screens
    save_settings(settings)


def save_active_screen_index(index: int) -> None:
    """Saves just the active screen index."""
    settings = load_settings()
    settings.active_screen_index = index
    save_settings(settings)


def save_custom_input_habits(habits: set) -> None:
    settings = load_settings()
    settings.custom_input_habits = habits
    save_settings(settings)


def save_max_one_habits(habits: set) -> None:
    settings = load_settings()
    settings.max_one_habits = habits
    save_settings(settings)


def save_habit_icons(icons: dict) -> None:
    settings = load_settings()
    settings.habit_icons = icons
    save_settings(settings)


def save_habit_order(order: list) -> None:
    settings = load_settings()
    settings.habit_order = order
    save_settings(settings)


def save_text_input_habits(habits: set) -> None:
    settings = load_settings()
    settings.text_input_habits = habits
    save_settings(settings)


def save_text_input_options_habits(habits: set) -> None:
    settings = load_settings()
    settings.text_input_options_habits = habits
    save_settings(settings)


def save_text_input_file_uris(uris: dict) -> None:
    settings = load_settings()
    settings.text_input_file_uris = uris
    save_settings(settings)


def save_habit_dividers(dividers: dict) -> None:
    settings = load_settings()
    settings.habit_dividers = dividers
    save_settings(settings)


def save_dated_entry_habits(habits: set) -> None:
    settings = load_settings()
    settings.dated_entry_habits = habits
    save_settings(settings)


def save_dated_entry_file_uris(uris: dict) -> None:
    settings = load_settings()
    settings.dated_entry_file_uris = uris
    save_settings(settings)


def save_dated_entry_file_sizes(sizes: dict) -> None:
    settings = load_settings()
    settings.dated_entry_file_sizes = sizes
    save_settings(settings)
