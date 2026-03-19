"""
Info panel shown below the grid when in info mode.
Matches the Android HabitInfoPanel composable in HabitGridScreen.kt.
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
from typing import Optional

from habit_models import Habit, RollingHigh


def _format_rolling_row(current_val: float, high: RollingHigh) -> str:
    """Format a rolling stats row like the Android app."""
    if current_val == int(current_val):
        cur = str(int(current_val))
    else:
        cur = f"{current_val:.2f}"
    if high.value == int(high.value):
        high_val = str(int(high.value))
    else:
        high_val = f"{high.value:.2f}"
    date_str = high.date if high.date else "—"
    return f"({cur}) {high_val} - {date_str}"


class InfoRow(QWidget):
    """A single label: value row in the info panel."""
    def __init__(self, label: str, value: str,
                 value_color: str = "#FFFFFF",
                 label_color: str = "#ADD8E6", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(4)

        lbl = QLabel(f"{label}: ")
        lbl.setStyleSheet(f"color: {label_color}; font-size: 11px; font-weight: 500;")
        layout.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(f"color: {value_color}; font-size: 11px;")
        val.setWordWrap(True)
        layout.addWidget(val, 1)


class HabitInfoPanel(QWidget):
    """
    Panel showing detailed stats for the selected habit.
    Matches the Android HabitInfoPanel composable.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1A1A2E; border-radius: 8px;")
        self.setMinimumHeight(120)
        self.setMaximumHeight(200)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(3)

        self._placeholder = QLabel("ℹ Tap any habit button to see its stats")
        self._placeholder.setStyleSheet("color: #888888; font-size: 12px;")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._placeholder)

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(3)
        self._content_widget.hide()
        self._layout.addWidget(self._content_widget)

    def update_habit(self, habit: Optional[Habit]):
        """Update the panel to show stats for the given habit, or placeholder if None."""
        # Clear previous content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if habit is None:
            self._placeholder.show()
            self._content_widget.hide()
            return

        self._placeholder.hide()
        self._content_widget.show()

        # Habit name
        name_label = QLabel(habit.name)
        name_label.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: bold;")
        self._content_layout.addWidget(name_label)

        # Streak info
        streak_label = "Current streak" if habit.current_streak >= 0 else "Current antistreak"
        streak_val = f"+{habit.current_streak}" if habit.current_streak >= 0 else str(habit.current_streak)
        streak_color = "#80FF80" if habit.current_streak >= 0 else "#FF8080"
        self._content_layout.addWidget(InfoRow(streak_label, streak_val, streak_color))
        self._content_layout.addWidget(InfoRow("Longest streak", str(habit.longest_streak)))

        # All-time high header
        header = QLabel("(current) All time high - date:")
        header.setStyleSheet("color: #ADD8E6; font-size: 11px; font-weight: 600;")
        self._content_layout.addWidget(header)

        # Rolling stats rows
        self._content_layout.addWidget(InfoRow(
            "day",
            _format_rolling_row(
                float(habit.current_day_value),
                RollingHigh(float(habit.all_time_high_day), habit.all_time_high_day_date)
            ),
            label_color="#888888"
        ))
        self._content_layout.addWidget(InfoRow(
            "week",
            _format_rolling_row(habit.avg_last_7_days, habit.all_time_high_week),
            label_color="#888888"
        ))
        self._content_layout.addWidget(InfoRow(
            "month",
            _format_rolling_row(habit.avg_last_30_days, habit.all_time_high_month),
            label_color="#888888"
        ))
        self._content_layout.addWidget(InfoRow(
            "year",
            _format_rolling_row(habit.avg_last_365_days, habit.all_time_high_year),
            label_color="#888888"
        ))
