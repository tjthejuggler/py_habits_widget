# py_habits_widget

A PyQt5 desktop widget for the **Tail Habit Tracker**, mirroring the Android app's `HabitGridScreen` layout.

## Layout

```
┌─────────────────────────────────────────────────────┐
│  ◀  Today / date  ▶          [📊] [✏] [ℹ] [⚙]     │  ← Top bar
├─────────────────────────────────────────────────────┤
│  [general]  [screen2]  [screen3]                    │  ← Screen tabs
├─────────────────────────────────────────────────────┤
│                                                     │
│   8-column × 10-row grid of HabitButton cells       │  ← Main grid
│                                                     │
├─────────────────────────────────────────────────────┤
│  Info panel  /  Edit control bar  (conditional)     │  ← Bottom panel
└─────────────────────────────────────────────────────┘
```

## Running

```bash
source py_habits_widget/bin/activate
python py_widget.py
# or use the launch script:
bash start_py_widget.sh
```

## Key Files

| File | Purpose |
|------|---------|
| `py_widget.py` | Main app entry point, window assembly |
| `habit_button.py` | Individual habit cell widget (dynamic sizing) |
| `habit_view_model.py` | State management / ViewModel |
| `habit_models.py` | Data models (`Habit`, `HabitScreen`, `AppSettings`) |
| `habits_repository.py` | Reads/writes the habits SQLite database |
| `settings_repository.py` | Persists app settings to `~/.config/py_habits_widget/settings.json` |
| `habit_colors.py` | Color and icon mapping per habit |
| `habit_calculator.py` | Streak and stat calculations |
| `info_panel.py` | Bottom info panel (info mode) |
| `edit_control_bar.py` | Bottom edit control bar (edit mode) |
| `graphs_panel.py` | Bottom graphs panel (graph mode) |
| `dialogs.py` | All modal dialogs |

## Persistent Files

| Path | Contents |
|------|---------|
| `~/.config/py_habits_widget/settings.json` | Habit screens, icons, input modes, etc. |
| `~/.config/py_habits_widget/window_geometry.json` | Saved window size and position |

## Dynamic Resizing

*(Added 2026-03-29)*

The window is fully resizable. All grid cells, icons, and text scale proportionally as the window is resized:

- **`HabitButton`** and **`PlaceholderCell`** accept a `cell_size` parameter instead of using a fixed constant.
- Font size, icon size, corner radius, and text margins all scale relative to the cell size.
- `HabitGridWidget.resizeEvent` debounces resize events (80 ms) and recomputes `cell_size` from the window width using:
  ```
  cell_size = (window_width - 2×margin - 7×spacing) / 8
  ```
- Minimum cell size is **40 px** to keep the widget usable when shrunk.

## Window Geometry Persistence

*(Added 2026-03-29)*

Window size and position are saved to `~/.config/py_habits_widget/window_geometry.json` on close and restored on next launch. The position is clamped to the available screen area so the window is never off-screen.
