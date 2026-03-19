"""
A single habit cell in the 8×10 grid, matching the Android app's HabitButton.kt.

Layout:
  Top-left:     all-time high day count
  Top-right:    "+" badge if custom input mode / "ℹ" in info mode / "⠿" in edit mode
  Center:       icon image (white-tinted)
  Bottom-left:  current streak (positive) or antistreak (negative)
  Bottom-right: longest streak

Android reference:
  - Grid: GridCells.Fixed(8) with 4.dp padding, each cell has 2.dp padding
  - Cell: aspectRatio(1f) with RoundedCornerShape(6.dp)
  - Icon: 20.dp with ColorFilter.tint(Color.White)
  - Font: 9.sp for numbers
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import (QPainter, QFont, QColor, QPixmap, QIcon, QPen,
                          QPainterPath, QImage)
from PyQt5.QtCore import Qt, QSize, QRect, QRectF, pyqtSignal
from typing import Optional, Dict

from habit_models import Habit
from habit_colors import get_habit_color, get_habit_icon_path

# Cell size: Android uses aspectRatio(1f) in an 8-column grid.
# On a typical phone (~360dp wide), each cell is ~43dp.
# On desktop we use 60px so the full 8×10 grid fits without scrolling.
CELL_SIZE = 60
ICON_SIZE = 24  # Android uses 20.dp; scaled proportionally for 60px cells

# Global cache for white-tinted icon pixmaps (shared across all HabitButton instances)
_white_icon_cache: Dict[str, QPixmap] = {}


def _tint_pixmap_white(pixmap: QPixmap) -> QPixmap:
    """
    Apply a white color tint to a pixmap, matching Android's ColorFilter.tint(Color.White).
    This replaces all visible pixels with white while preserving the alpha channel.
    """
    # Convert to QImage for pixel manipulation
    img = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    # Create a white image of the same size
    white_img = QImage(img.size(), QImage.Format_ARGB32)
    white_img.fill(Qt.white)
    # Paint white using SourceIn composition: keeps alpha from destination, color from source
    painter = QPainter(img)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.drawImage(0, 0, white_img)
    painter.end()
    return QPixmap.fromImage(img)


class HabitButton(QWidget):
    """
    A single habit cell widget matching the Android HabitButton composable.
    """
    clicked = pyqtSignal()
    long_clicked = pyqtSignal()

    def __init__(self, habit: Habit, parent=None):
        super().__init__(parent)
        self.habit = habit
        self.info_mode = False
        self.edit_mode = False
        self.graph_mode = False
        self.is_selected = False
        self.is_graph_selected = False
        self.is_move_pending_source = False
        self.is_move_pending_target = False
        self.custom_icon_overrides: Dict[str, str] = {}
        self._cached_pixmap: Optional[QPixmap] = None
        self._last_icon_path: Optional[str] = None
        self.setFixedSize(CELL_SIZE, CELL_SIZE)
        self.setCursor(Qt.PointingHandCursor)

    def update_habit(self, habit: Habit):
        """Update the habit data and repaint."""
        self.habit = habit
        self._cached_pixmap = None  # invalidate icon cache
        self.update()

    def set_modes(self, info_mode: bool = False, edit_mode: bool = False,
                  graph_mode: bool = False,
                  is_selected: bool = False, is_graph_selected: bool = False,
                  is_move_pending_source: bool = False,
                  is_move_pending_target: bool = False):
        self.info_mode = info_mode
        self.edit_mode = edit_mode
        self.graph_mode = graph_mode
        self.is_selected = is_selected
        self.is_graph_selected = is_graph_selected
        self.is_move_pending_source = is_move_pending_source
        self.is_move_pending_target = is_move_pending_target
        self.update()

    def set_custom_icon_overrides(self, overrides: Dict[str, str]):
        self.custom_icon_overrides = overrides
        self._cached_pixmap = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.long_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def _load_icon_pixmap(self) -> Optional[QPixmap]:
        """Load, white-tint, and cache the icon pixmap."""
        icon_path = get_habit_icon_path(self.habit.name, self.custom_icon_overrides)
        if icon_path == self._last_icon_path and self._cached_pixmap is not None:
            return self._cached_pixmap
        self._last_icon_path = icon_path
        if icon_path is None:
            self._cached_pixmap = None
            return None

        # Check global white-tinted cache first
        if icon_path in _white_icon_cache:
            self._cached_pixmap = _white_icon_cache[icon_path]
            return self._cached_pixmap

        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            self._cached_pixmap = None
            return None

        # Scale to ICON_SIZE, then tint white (like Android's ColorFilter.tint(Color.White))
        scaled = pixmap.scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        white_pixmap = _tint_pixmap_white(scaled)

        # Cache globally so other HabitButton instances reuse it
        _white_icon_cache[icon_path] = white_pixmap
        self._cached_pixmap = white_pixmap
        return self._cached_pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        habit = self.habit

        # Background color based on today's count
        bg_color = get_habit_color(habit.name, habit.today_count)

        # Adjust alpha for move states
        if self.is_move_pending_source:
            bg_color = QColor(bg_color.red(), bg_color.green(), bg_color.blue(), 128)
        elif self.is_move_pending_target:
            bg_color = QColor(bg_color.red(), bg_color.green(), bg_color.blue(), 178)

        # Draw rounded rect background
        radius = 6  # matching Android's RoundedCornerShape(6.dp)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        painter.fillPath(path, bg_color)

        # Draw border based on mode
        if self.is_move_pending_source:
            painter.setPen(QPen(QColor(0x44, 0xFF, 0xFF), 2))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)
        elif self.is_selected and self.edit_mode:
            painter.setPen(QPen(QColor(0xFF, 0xAA, 0x00), 2))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)
        elif self.is_move_pending_target:
            painter.setPen(QPen(QColor(0x44, 0xFF, 0xFF), 1))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)
        elif self.is_selected:
            painter.setPen(QPen(QColor(0xFF, 0xD7, 0x00), 2))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)
        elif self.is_graph_selected:
            # Light blue border matching Android's Color(0xFF4FC3F7)
            painter.setPen(QPen(QColor(0x4F, 0xC3, 0xF7), 2))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)
        elif self.graph_mode:
            # Dim blue border matching Android's Color(0xFF2A4A6A)
            painter.setPen(QPen(QColor(0x2A, 0x4A, 0x6A), 1))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)
        elif self.info_mode:
            painter.setPen(QPen(QColor(0x88, 0xCC, 0xFF), 1))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)
        elif self.edit_mode:
            painter.setPen(QPen(QColor(0xFF, 0x8C, 0x00), 1))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius, radius)

        # Font for numbers — Android uses 9.sp; 7pt fits well in 60px cells
        small_font = QFont("Arial", 7)
        small_font.setBold(True)
        painter.setFont(small_font)

        text_margin = 2
        text_h = 11  # height for text rows

        # Top-left: all-time high day
        painter.setPen(QColor(Qt.white))
        painter.drawText(QRect(text_margin, 0, w - text_margin * 2, text_h),
                         Qt.AlignLeft | Qt.AlignTop,
                         str(habit.all_time_high_day))

        # Top-right: mode indicator or custom input badge
        if self.is_move_pending_source:
            painter.setPen(QColor(0x44, 0xFF, 0xFF))
            painter.drawText(QRect(text_margin, 0, w - text_margin * 2, text_h),
                             Qt.AlignRight | Qt.AlignTop, "↕")
        elif self.edit_mode:
            painter.setPen(QColor(0xFF, 0x8C, 0x00))
            painter.drawText(QRect(text_margin, 0, w - text_margin * 2, text_h),
                             Qt.AlignRight | Qt.AlignTop, "⠿")
        elif self.info_mode:
            painter.setPen(QColor(0x88, 0xCC, 0xFF))
            painter.drawText(QRect(text_margin, 0, w - text_margin * 2, text_h),
                             Qt.AlignRight | Qt.AlignTop, "ℹ")
        elif self.is_graph_selected:
            # 📊 badge in top-right when selected for graphing
            painter.setPen(QColor(0x4F, 0xC3, 0xF7))
            painter.drawText(QRect(text_margin, 0, w - text_margin * 2, text_h),
                             Qt.AlignRight | Qt.AlignTop, "📊")
        elif habit.use_custom_input:
            painter.setPen(QColor(Qt.yellow))
            painter.drawText(QRect(text_margin, 0, w - text_margin * 2, text_h),
                             Qt.AlignRight | Qt.AlignTop, "+")

        # Center: white-tinted icon
        pixmap = self._load_icon_pixmap()
        if pixmap is not None:
            x = (w - pixmap.width()) // 2
            y = (h - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)

        # Bottom-left: streak/antistreak
        streak_text = f"+{habit.current_streak}" if habit.current_streak >= 0 else str(habit.current_streak)
        streak_color = QColor(0x80, 0xFF, 0x80) if habit.current_streak >= 0 else QColor(0xFF, 0x80, 0x80)
        painter.setPen(streak_color)
        painter.drawText(QRect(text_margin, h - text_h, w - text_margin * 2, text_h),
                         Qt.AlignLeft | Qt.AlignBottom, streak_text)

        # Bottom-right: longest streak
        painter.setPen(QColor(0xAD, 0xD8, 0xE6))  # light blue
        painter.drawText(QRect(text_margin, h - text_h, w - text_margin * 2, text_h),
                         Qt.AlignRight | Qt.AlignBottom,
                         str(habit.longest_streak))

        painter.end()

    def sizeHint(self):
        return QSize(CELL_SIZE, CELL_SIZE)


class PlaceholderCell(QWidget):
    """
    A placeholder cell shown in edit mode. Matches Android's PlaceholderCell composable.
    """
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_selected = False
        self.is_move_pending_target = False
        self.setFixedSize(CELL_SIZE, CELL_SIZE)
        self.setCursor(Qt.PointingHandCursor)

    def set_state(self, is_selected: bool = False, is_move_pending_target: bool = False):
        self.is_selected = is_selected
        self.is_move_pending_target = is_move_pending_target
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        if self.is_selected:
            bg = QColor(0x3A, 0x20, 0x00)
            text_color = QColor(0xFF, 0xAA, 0x00)
            text = "+"
        elif self.is_move_pending_target:
            bg = QColor(0x00, 0x3A, 0x3A)
            text_color = QColor(0x44, 0xFF, 0xFF)
            text = "→"
        else:
            bg = QColor(0x0D, 0x0D, 0x0D)
            text_color = QColor(0x2A, 0x2A, 0x2A)
            text = "·"

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 4, 4)
        painter.fillPath(path, bg)

        if self.is_move_pending_target:
            painter.setPen(QPen(QColor(0x44, 0xFF, 0xFF), 1))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 4, 4)

        font = QFont("Arial", 14 if (self.is_selected or self.is_move_pending_target) else 10)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(QRect(0, 0, w, h), Qt.AlignCenter, text)

        painter.end()

    def sizeHint(self):
        return QSize(CELL_SIZE, CELL_SIZE)
