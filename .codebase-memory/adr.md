# ADR: Auto-detect stop debounce (three-minute grace, retroactive finish)

**Date:** 2026-08-20 (revised same day: grace extended 60 s → 180 s at user request)
**Status:** Accepted

## Context
The PC bubble widget's window auto-detect (`auto_detect.py`) stops a habit timer the instant the mapped window loses focus or the user goes idle 15 s. Brief window switches therefore fragmented one work session into many tiny sessions/taps, each synced to the phone as a separate increment — cluttering the phone's history.

## Decision
Debounce auto-detected stops with a **180-second grace period** (`AUTO_STOP_GRACE_MS = 180_000`), implemented entirely in the widget layer (`pc_bubble_widget.py.BubbleWidget`); `auto_detect.py` is untouched.

- `request_auto_stop(habit)`: records the activity-stop datetime in `pending_auto_stops` and arms a single-shot grace QTimer. The timer stays in `self.timers` (square keeps running, session conceptually alive).
- Return within the grace period: the controller's `is_running` lambda reports a grace-pending timer as NOT running, so `_tick` re-fires `on_start` → `_auto_started` cancels the pending stop → same session continues (same start timestamp, one increment).
- Grace expiry: `_finalize_auto_stop` calls `stop_timer(habit, end=stopped_at)` — finish time is **retroactive** to the moment window activity stopped, not the expiry moment. `append_event` (pc_widget_sync.py) gained an `end` parameter so the bridge payload's `end` field is honest too.
- Manual stop: `stop_timer` cancels any pending grace first → immediate, no debounce (manual always wins).
- Persistence: `pending_stops` in `state.json`; on load, grace re-arms with the remaining time (`start(max(0, remaining))` — never finalize inline during `__init__`, `ack_timer` doesn't exist yet). Quit flushes all pending stops via `finalize_pending_stops()` so no session is swallowed.

## Consequences
- One window-flurry → exactly one phone event, timestamped at the real session bounds.
- Displayed elapsed keeps ticking during grace (cosmetic only; recorded minutes exclude the idle gap).
- Verified by `pc_widget_smoke_test.py` section [2b] (interval check asserts against `AUTO_STOP_GRACE_MS`, so it tracks the constant automatically).