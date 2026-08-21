# ADR: PC bubble widget — visible idle countdown & PC→phone habit-toggle channel

Date: 2026-08-21
Status: accepted

## Context
The PC floating bubble widget (pc_bubble_widget.py) debounced auto-detected
stops with an invisible 180 s grace period (AUTO_STOP_GRACE_MS), and habit
membership on the widget could only be changed from the Android app
(phone→PC config push; no PC→phone request path existed).

## Decision
1. **Visible countdown replaces the grace period.** `request_auto_stop()`
   now arms a per-habit countdown (default 30 s, from
   auto_detect.json `countdown_seconds`; idle threshold default lowered
   15 s → 5 s). The square renders a black/red countdown box
   (HabitSquare.countdown_left, refreshed by the 1 Hz tick). At zero,
   `_finalize_auto_stop()` calls `stop_timer(end=now − (idle+countdown))`.
   Input resumption cancels silently via the existing
   `cancel_pending_stop()` path. `pending_auto_stops` values changed from
   datetime → {stopped_at, deadline, deduct}; state.json persists the dict
   (old plain-datetime entries still load, migrated with 30 s/35 s defaults).
2. **PC→phone toggle requests ride the existing event queue.** New event
   kind `toggle_pc_widget_habit` with an ABSOLUTE `enabled` flag (idempotent
   under at-least-once redelivery — unlike additive increments, toggles are
   not naturally idempotent). Bridge (tail_bridge/bridge_server.py) accepts
   the kind and passes `enabled` through; phone-side PcEventQueueProcessor
   .applyEvent routes it to applyPcWidgetToggle() which writes DataStore
   (pcWidgetHabits ± habit, minutes forced ON when enabling — mirroring
   HabitViewModel.togglePcWidgetHabit) and re-POSTs the widget config.
3. **Full habit catalog travels with the config.** Phone pushes
   `all_habits` (HabitViewModel.pushPcWidgetConfig via getAllHabitNames();
   processor uses habits-db keys) so the new PC settings dialog
   (pc_settings_dialog.py, opened from the bubble menu "Settings…") can
   list every habit. The dialog holds its checklist steady ~20 s after a
   toggle request so the 3 s config re-poll can't visually revert it
   before the phone round-trips.
4. **Square UX additions.** Running squares scale 46→60 px (square_d());
  ✕ cancel button top-right (hit-rect set during _render_body, checked
  first in HabitSquare.mousePressEvent → cancel_timer); sync dot shifts
  left of the ✕ while running; center-circle left-click with ≥1 running
  timer stops all (BubbleWidget.stop_all_timers), else drags as before.

## Consequences
- AUTO_STOP_GRACE_MS is gone; smoke test section [2b] rewritten.
- The bridge server process must be restarted to pick up the new event
  kind + all_habits passthrough; the phone app needs the new APK
  (installed 2026-08-21) for the picker's full catalog and toggle handling.
- Window/ring geometry uses SQUARE_D_RUN (60 px) for spread radius, window
  bounds and proximity zone; _place_square centers on each square's own
  width so mixed idle/running sizes coexist.