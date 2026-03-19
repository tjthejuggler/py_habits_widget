"""
Data models for the habit tracker, matching the Android app's HabitModels.kt.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class RollingHigh:
    """All-time high for a rolling window: the peak average value and the date it occurred."""
    value: float = 0.0
    date: str = ""


@dataclass
class Habit:
    """
    Represents a single habit with all computed stats for display.
    Matches the Android Habit data class.
    """
    name: str = ""
    # The effective "points" value for today — raw count divided by divider (rounded, min 1 if non-zero)
    today_count: int = 0
    # The raw stored count for today, before any divider is applied
    raw_today_count: int = 0
    current_streak: int = 0       # positive = streak, negative = antistreak
    longest_streak: int = 0
    all_time_high_day: int = 0    # top-left: max single-day raw count
    use_custom_input: bool = False

    # When > 1, the raw stored count is divided by this value (rounded to nearest int)
    divider: int = 1

    # Current rolling averages
    current_day_value: int = 0
    avg_last_7_days: float = 0.0
    avg_last_30_days: float = 0.0
    avg_last_365_days: float = 0.0

    # All-time high rolling windows
    all_time_high_week: RollingHigh = field(default_factory=RollingHigh)
    all_time_high_month: RollingHigh = field(default_factory=RollingHigh)
    all_time_high_year: RollingHigh = field(default_factory=RollingHigh)
    all_time_high_day_date: str = ""


def apply_divider(raw_count: int, divider: int) -> int:
    """
    Returns the effective "points" value for a raw count given a divider.
    When divider <= 1 the raw count is returned unchanged.
    Otherwise the result is rounded to the nearest whole number.
    If the raw count is > 0 the result is always at least 1 (never rounds down to 0).
    """
    if divider <= 1:
        return raw_count
    if raw_count <= 0:
        return 0
    divided = round(raw_count / divider)
    return max(divided, 1)


# Raw database format matching habitsdb.txt:
# { "Habit Name": { "2026-01-05": 1, "2026-01-06": 0 } }
HabitsDatabase = Dict[str, Dict[str, int]]


@dataclass
class HabitScreen:
    """A named screen (page) of habits."""
    id: str = ""
    name: str = ""
    habit_names: List[str] = field(default_factory=list)


@dataclass
class AppSettings:
    """App settings, matching the Android AppSettings data class."""
    custom_input_habits: Set[str] = field(default_factory=lambda: DEFAULT_CUSTOM_INPUT_HABITS.copy())
    habit_order: List[str] = field(default_factory=list)
    habit_screens: List[HabitScreen] = field(default_factory=list)
    active_screen_index: int = 0
    max_one_habits: Set[str] = field(default_factory=set)
    text_input_habits: Set[str] = field(default_factory=set)
    text_input_options_habits: Set[str] = field(default_factory=set)
    text_input_file_uris: Dict[str, str] = field(default_factory=dict)
    habit_icons: Dict[str, str] = field(default_factory=dict)
    dated_entry_habits: Set[str] = field(default_factory=set)
    dated_entry_file_uris: Dict[str, str] = field(default_factory=dict)
    dated_entry_file_sizes: Dict[str, int] = field(default_factory=dict)
    habit_dividers: Dict[str, int] = field(default_factory=dict)


DEFAULT_CUSTOM_INPUT_HABITS: Set[str] = {
    "Launch Pushups Widget",
    "Launch Situps Widget",
    "Launch Squats Widget",
    "Cold Shower Widget",
    "Sweat"
}

# The canonical ordered list of habits matching the Android app exactly (row-major order).
HABIT_ORDER: List[str] = [
    # Row 1
    "Juggle lights", "Joggle", "Blind juggle", "Juggling Balls Carry",
    "Juggling Others Learn", "Most Collisions", "No Coffee", "Tracked Sleep",
    # Row 2
    "Unique juggle", "Create juggle", "Song juggle", "Move juggle",
    "Juggle run", "Free", "Magic practiced", "Magic performed",
    # Row 3
    "Juggling record broke", "Fun juggle", "Janki used", "Filmed juggle",
    "Watch juggle", "Inspired juggle", "Juggle goal", "Balanced",
    # Row 4
    "Dream acted", "Drm Review", "Lucidity trained", "Unusual experience",
    "Meditations", "Kind stranger", "Broke record", "Grumpy blocker",
    # Row 5
    "Sleep watch", "Early phone", "Anki created", "Anki mydis done",
    "Some anki", "Health learned", "Took pills", "Flossed",
    # Row 6
    "Apnea walked", "Apnea practiced", "Apnea apb", "Apnea spb",
    "Lung stretch", "Sweat", "Fasted", "Todos done",
    # Row 7
    "Cold Shower Widget", "Launch Squats Widget", "Launch Situps Widget", "Launch Pushups Widget",
    "Cardio sessions", "Good posture", "HIT", "Fresh air",
    # Row 8
    "Programming sessions", "Juggling tech sessions", "Writing sessions", "UC post",
    "AI tool", "Drew", "Question asked", "Talk stranger",
    # Row 9
    "Book read", "Podcast finished", "Educational video watched", "Article read",
    "Read academic", "Language studied", "Music listen", "Memory practice",
    # Row 10
    "Fiction Book Intake", "Fiction Video Intake", "Chess", "Rabbit Hole",
    "Speak AI", "Communication Improved", "Unusually Kind"
]
