"""
graphs_panel.py — Graph panel for the Habit Tracker desktop widget.

Matches the Android GraphsPanel composable from GraphsScreen.kt:
  - Time period selector row: 1W, 2W, 1M, 3M, 6M, 1Y, Max
  - Line chart drawn with QPainter (one line per selected habit)
  - Legend row showing habit names with their line colors
  - Stats summary: current streak, avg, all-time high for each selected habit
  - "Open Legacy Graphs" button to launch habitdb_streak_finder.py in browser

Graph colors match Android's GRAPH_COLORS list.
"""
import os
import subprocess
import sys
from datetime import date, timedelta
from typing import List, Optional, Tuple, Set

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QFont, QFontMetrics, QPainterPath
)
from PyQt5.QtCore import Qt, QRect, QRectF, QSize, pyqtSignal

# ── Graph colors matching Android's GRAPH_COLORS ──────────────────────────────

GRAPH_COLORS = [
    QColor(0x4F, 0xC3, 0xF7),  # light blue
    QColor(0xFF, 0x8A, 0x65),  # orange
    QColor(0x81, 0xC7, 0x84),  # green
    QColor(0xBA, 0x68, 0xC8),  # purple
    QColor(0xFF, 0xD5, 0x4F),  # yellow
    QColor(0xE5, 0x73, 0x73),  # red
    QColor(0x4D, 0xD0, 0xE1),  # cyan
    QColor(0xA1, 0x88, 0x7F),  # brown
    QColor(0xAE, 0xD5, 0x81),  # lime
    QColor(0xF0, 0x62, 0x92),  # pink
]

# Time period options matching Android's GraphTimePeriod enum
GRAPH_TIME_PERIODS = [
    ("1W", 7),
    ("2W", 14),
    ("1M", 30),
    ("3M", 90),
    ("6M", 180),
    ("1Y", 365),
    ("Max", None),
]


# ── Line chart widget ─────────────────────────────────────────────────────────

class LineChartWidget(QWidget):
    """
    A QPainter-based line chart for multiple habits over a date range.
    Matches the Canvas-based chart in Android's GraphsScreen.kt.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: List[Tuple[str, QColor, List[Tuple[str, int]]]] = []
        # Each entry: (habit_name, color, [(date_str, value), ...])
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #0A0A1A;")
        self._hovered_x: Optional[int] = None
        self.setMouseTracking(True)

    def set_series(self, series: List[Tuple[str, QColor, List[Tuple[str, int]]]]):
        """Set the data series. Each entry: (name, color, [(date_str, value)])."""
        self._series = series
        self.update()

    def mouseMoveEvent(self, event):
        self._hovered_x = event.x()
        self.update()

    def leaveEvent(self, event):
        self._hovered_x = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(0x0A, 0x0A, 0x1A))

        if not self._series:
            painter.setPen(QColor(0x44, 0x44, 0x66))
            painter.setFont(QFont("Arial", 11))
            painter.drawText(QRect(0, 0, w, h), Qt.AlignCenter,
                             "📊 Tap habit squares to select habits for graphing")
            painter.end()
            return

        # Margins
        margin_left = 36
        margin_right = 12
        margin_top = 10
        margin_bottom = 24

        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        if chart_w <= 0 or chart_h <= 0:
            painter.end()
            return

        # Collect all data points to find global min/max
        all_values = []
        max_points = 0
        for _, _, data in self._series:
            for _, v in data:
                all_values.append(v)
            if len(data) > max_points:
                max_points = len(data)

        if not all_values or max_points == 0:
            painter.end()
            return

        val_min = 0
        val_max = max(all_values) if all_values else 1
        if val_max == 0:
            val_max = 1

        # Draw grid lines (horizontal)
        painter.setPen(QPen(QColor(0x22, 0x22, 0x44), 1))
        grid_steps = 4
        for i in range(grid_steps + 1):
            y = margin_top + chart_h - int(chart_h * i / grid_steps)
            painter.drawLine(margin_left, y, margin_left + chart_w, y)
            # Y-axis label
            label_val = val_min + (val_max - val_min) * i / grid_steps
            label_str = str(int(label_val)) if label_val == int(label_val) else f"{label_val:.1f}"
            painter.setPen(QColor(0x55, 0x55, 0x88))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(QRect(0, y - 8, margin_left - 2, 16),
                             Qt.AlignRight | Qt.AlignVCenter, label_str)
            painter.setPen(QPen(QColor(0x22, 0x22, 0x44), 1))

        # Draw X-axis date labels (show ~5 evenly spaced)
        if max_points > 1:
            # Use dates from first series
            dates = [ds for ds, _ in self._series[0][2]]
            label_count = min(5, max_points)
            painter.setFont(QFont("Arial", 7))
            painter.setPen(QColor(0x55, 0x55, 0x88))
            for i in range(label_count):
                idx = int(i * (max_points - 1) / max(label_count - 1, 1))
                if idx < len(dates):
                    x = margin_left + int(chart_w * idx / (max_points - 1))
                    # Short date: M/D
                    ds = dates[idx]
                    try:
                        d = date.fromisoformat(ds)
                        label = f"{d.month}/{d.day}"
                    except Exception:
                        label = ds[-5:]
                    painter.drawText(QRect(x - 20, h - margin_bottom + 4, 40, 16),
                                     Qt.AlignCenter, label)

        # Draw each series as a line
        for series_idx, (name, color, data) in enumerate(self._series):
            if len(data) < 2:
                continue

            painter.setPen(QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

            path = QPainterPath()
            first = True
            for i, (ds, v) in enumerate(data):
                x = margin_left + int(chart_w * i / (len(data) - 1))
                y = margin_top + chart_h - int(chart_h * (v - val_min) / (val_max - val_min))
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)

            painter.drawPath(path)

            # Draw dots at each data point (small)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            for i, (ds, v) in enumerate(data):
                x = margin_left + int(chart_w * i / (len(data) - 1))
                y = margin_top + chart_h - int(chart_h * (v - val_min) / (val_max - val_min))
                painter.drawEllipse(x - 2, y - 2, 4, 4)
            painter.setBrush(Qt.NoBrush)

        # Draw hover line
        if self._hovered_x is not None and self._series:
            hx = self._hovered_x
            if margin_left <= hx <= margin_left + chart_w:
                painter.setPen(QPen(QColor(0xFF, 0xFF, 0xFF, 80), 1, Qt.DashLine))
                painter.drawLine(hx, margin_top, hx, margin_top + chart_h)

                # Find nearest data index
                data = self._series[0][2]
                if len(data) > 1:
                    idx = int((hx - margin_left) / chart_w * (len(data) - 1) + 0.5)
                    idx = max(0, min(idx, len(data) - 1))
                    ds = data[idx][0]
                    try:
                        d = date.fromisoformat(ds)
                        date_label = f"{d.month}/{d.day}/{d.year}"
                    except Exception:
                        date_label = ds

                    # Show values for all series at this index
                    lines = [date_label]
                    for name, color, sdata in self._series:
                        if idx < len(sdata):
                            lines.append(f"{name}: {sdata[idx][1]}")

                    tooltip = "\n".join(lines)
                    painter.setFont(QFont("Arial", 8))
                    fm = QFontMetrics(QFont("Arial", 8))
                    line_h = fm.height()
                    tip_w = max(fm.horizontalAdvance(l) for l in lines) + 12
                    tip_h = line_h * len(lines) + 8

                    tx = min(hx + 6, w - tip_w - 4)
                    ty = margin_top + 4

                    painter.fillRect(tx, ty, tip_w, tip_h, QColor(0x1A, 0x1A, 0x2E, 220))
                    painter.setPen(QColor(0x44, 0x44, 0x66))
                    painter.drawRect(tx, ty, tip_w, tip_h)

                    for i, line in enumerate(lines):
                        if i == 0:
                            painter.setPen(QColor(0xFF, 0xFF, 0xFF))
                        else:
                            c = self._series[i - 1][1] if i - 1 < len(self._series) else QColor(Qt.white)
                            painter.setPen(c)
                        painter.drawText(tx + 6, ty + 4 + i * line_h + fm.ascent(), line)

        painter.end()


# ── Stats summary widget ──────────────────────────────────────────────────────

class GraphStatsWidget(QWidget):
    """Shows a compact stats row for each selected habit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        self.setStyleSheet("background-color: #0D0D1A;")

    def update_stats(self, habits_data: List[Tuple[str, QColor, int, float, int]]):
        """
        Update stats display.
        habits_data: list of (name, color, current_streak, avg_30d, all_time_high)
        """
        # Clear existing
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not habits_data:
            lbl = QLabel("Select habits above to see stats")
            lbl.setStyleSheet("color: #444466; font-size: 10px;")
            lbl.setAlignment(Qt.AlignCenter)
            self._layout.addWidget(lbl)
            return

        for name, color, streak, avg30, ath in habits_data:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(2, 1, 2, 1)
            row_layout.setSpacing(8)

            # Color swatch + name
            color_hex = f"#{color.red():02X}{color.green():02X}{color.blue():02X}"
            name_lbl = QLabel(f"● {name}")
            name_lbl.setStyleSheet(f"color: {color_hex}; font-size: 10px; font-weight: bold;")
            name_lbl.setMinimumWidth(100)
            row_layout.addWidget(name_lbl)

            streak_str = f"+{streak}" if streak >= 0 else str(streak)
            streak_color = "#80FF80" if streak >= 0 else "#FF8080"
            streak_lbl = QLabel(f"streak: {streak_str}")
            streak_lbl.setStyleSheet(f"color: {streak_color}; font-size: 10px;")
            row_layout.addWidget(streak_lbl)

            avg_lbl = QLabel(f"avg30: {avg30:.1f}")
            avg_lbl.setStyleSheet("color: #AADDFF; font-size: 10px;")
            row_layout.addWidget(avg_lbl)

            ath_lbl = QLabel(f"ATH: {ath}")
            ath_lbl.setStyleSheet("color: #FFD700; font-size: 10px;")
            row_layout.addWidget(ath_lbl)

            row_layout.addStretch()
            self._layout.addWidget(row)


# ── Main graphs panel ─────────────────────────────────────────────────────────

class GraphsPanel(QWidget):
    """
    The full graphs panel shown below the habit grid when graph mode is active.
    Matches Android's GraphsPanel composable.

    Layout:
      ┌─────────────────────────────────────────────────────┐
      │  [1W] [2W] [1M] [3M] [6M] [1Y] [Max]  [Open Legacy]│  ← time period row
      ├─────────────────────────────────────────────────────┤
      │                                                     │
      │   Line chart (QPainter)                             │  ← chart
      │                                                     │
      ├─────────────────────────────────────────────────────┤
      │  ● habit1  streak: +5  avg30: 3.2  ATH: 10         │  ← stats
      │  ● habit2  streak: -2  avg30: 1.1  ATH: 5          │
      └─────────────────────────────────────────────────────┘
    """

    def __init__(self, view_model, parent=None):
        super().__init__(parent)
        self.vm = view_model
        self._period_buttons = {}
        self._build_ui()
        self.setStyleSheet("background-color: #0A0A1A;")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # ── Time period selector row ──────────────────────────────────────────
        period_row = QWidget()
        period_row.setStyleSheet("background-color: #0A0A1A;")
        period_layout = QHBoxLayout(period_row)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.setSpacing(4)

        for label, days in GRAPH_TIME_PERIODS:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.setFixedWidth(36)
            btn.setCheckable(True)
            btn.setChecked(label == self.vm.graph_time_period)
            btn.clicked.connect(lambda checked, l=label: self._on_period_clicked(l))
            self._period_buttons[label] = btn
            period_layout.addWidget(btn)

        period_layout.addStretch()

        # "Open Legacy Graphs" button
        self._btn_legacy = QPushButton("📈 Open Legacy Graphs")
        self._btn_legacy.setFixedHeight(24)
        self._btn_legacy.setToolTip("Launch the legacy Plotly/Dash graphs web app")
        self._btn_legacy.setStyleSheet("""
            QPushButton {
                background-color: #1A2A3A;
                color: #88CCFF;
                border: 1px solid #2A4A6A;
                border-radius: 4px;
                font-size: 10px;
                padding: 0 8px;
            }
            QPushButton:hover { background-color: #2A3A4A; }
        """)
        self._btn_legacy.clicked.connect(self._on_open_legacy_graphs)
        period_layout.addWidget(self._btn_legacy)

        layout.addWidget(period_row)

        # ── Line chart ────────────────────────────────────────────────────────
        self._chart = LineChartWidget()
        self._chart.setMinimumHeight(180)
        layout.addWidget(self._chart, 1)

        # ── Stats summary ─────────────────────────────────────────────────────
        self._stats = GraphStatsWidget()
        self._stats.setMaximumHeight(80)
        layout.addWidget(self._stats)

        self._update_period_buttons()

    def _update_period_buttons(self):
        """Highlight the active period button."""
        active = self.vm.graph_time_period
        for label, btn in self._period_buttons.items():
            is_active = (label == active)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4FC3F7;
                        color: #000000;
                        border: none;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1A1A2E;
                        color: #88AACC;
                        border: none;
                        border-radius: 4px;
                        font-size: 10px;
                    }
                    QPushButton:hover { background-color: #2A2A3E; }
                """)
            btn.setChecked(is_active)

    def _on_period_clicked(self, label: str):
        self.vm.set_graph_time_period(label)
        self._update_period_buttons()
        self.refresh()

    def _on_open_legacy_graphs(self):
        """Launch the legacy habitdb_streak_finder.py graphs web app."""
        # Find the script path relative to this file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        legacy_script = os.path.join(script_dir, "habitdb_streak_finder.py")

        if not os.path.exists(legacy_script):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Not Found",
                                f"Legacy graphs script not found:\n{legacy_script}")
            return

        # Launch in a new terminal/process
        try:
            # Try to open in browser via the threaded_dash_app.py if it exists
            threaded_app = os.path.join(script_dir, "threaded_dash_app.py")
            if os.path.exists(threaded_app):
                subprocess.Popen([sys.executable, threaded_app],
                                 cwd=script_dir,
                                 start_new_session=True)
            else:
                subprocess.Popen([sys.executable, legacy_script],
                                 cwd=script_dir,
                                 start_new_session=True)
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Launch Error",
                                f"Could not launch legacy graphs:\n{e}")

    def refresh(self):
        """Rebuild chart and stats from current ViewModel state."""
        selected = self.vm.graph_selected_habits
        if not selected:
            self._chart.set_series([])
            self._stats.update_stats([])
            return

        # Determine date range from time period
        today = date.today()
        period = self.vm.graph_time_period
        period_days = {p: d for p, d in GRAPH_TIME_PERIODS}
        days = period_days.get(period, 30)

        if days is None:
            # "Max" — find earliest date across all selected habits
            start = today
            for name in selected:
                entries = self.vm.cached_db.get(name, {})
                if entries:
                    earliest_str = min(entries.keys())
                    try:
                        earliest = date.fromisoformat(earliest_str)
                        if earliest < start:
                            start = earliest
                    except Exception:
                        pass
        else:
            start = today - timedelta(days=days - 1)

        end = today

        # Build series for each selected habit (in consistent color order)
        series = []
        stats_data = []
        sorted_habits = sorted(selected)  # consistent ordering

        for i, name in enumerate(sorted_habits):
            color = GRAPH_COLORS[i % len(GRAPH_COLORS)]
            data = self.vm.get_graph_data(name, start, end)
            series.append((name, color, data))

            # Compute stats for this habit
            entries = self.vm.cached_db.get(name, {})
            from habit_calculator import (
                calculate_streak_display, get_average_of_last_n_days,
                calculate_all_time_high_day
            )
            streak = calculate_streak_display(entries)
            avg30 = get_average_of_last_n_days(entries, 30)
            ath, _ = calculate_all_time_high_day(entries)
            stats_data.append((name, color, streak, avg30, ath))

        self._chart.set_series(series)
        self._stats.update_stats(stats_data)
        self._update_period_buttons()
