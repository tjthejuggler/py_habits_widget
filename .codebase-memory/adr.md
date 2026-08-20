# ADR: Auto-detect start requires a real press INSIDE the window (revised)

**Date:** 2026-08-20 (revision 2 — first timestamp-based fix proved insufficient in practice)
**Status:** Accepted

## Context
Rev1 compared "any input after the focus change". Two real-world holes, found by user testing:
1. **Same-class cycling**: clicking a taskbar icon to cycle multiple windows of one app (several VSCode windows) never changed the `(class, minimized)` tuple, so the focus timestamp went stale and the recent taskbar click counted as "input after focus".
2. **Input noise**: the button RELEASE following the raising click, and any mouse movement after the window appeared, both satisfied "input after focus".

## Decision (rev2)
- **Press-only interaction**: `InputActivityMonitor` now parses the evdev stream (`struct '<QQHHi'`, 24-byte input_event on x86_64) and tracks `last_press` — only EV_KEY events with value 1 (key/button DOWN). Movement (EV_REL), releases (0) and autorepeat (2) update `last_activity` (idle rule) but never `last_press`. Pure helper `_buffer_has_press(data)` is unit-tested.
- **Identity-based focus tracking**: `_FocusTracker.update(cls, minimized, caption)` keys on (class, minimized, caption) — KWin pushes caption per window, so cycling same-class windows re-arms the rule. The X11 backend keys on the xdotool window id (`getactivewindow` → id, then `getwindowclassname`).
- `AutoDetectController._tick`: `interacted = input.last_press > backend.focus.changed_at` (degraded mode without evdev keeps focus-only semantics). `user_active` stays in the start condition so a stale `interacted` can't fight the idle-stop rule.

## Consequences
- Taskbar clicks, icon cycling, alt-tab, maximize, mouse movement over the window: never auto-start.
- First real click/keystroke inside the window starts the timer; continuous typing keeps it running (title/caption changes re-arm the rule but the next keystroke re-satisfies it within ~1 s).
- Widget process must be restarted to pick up changes (user's first test hit the pre-fix process; restarted via start_pc_bubble.sh).
- Verified by smoke test section [8] (8 checks incl. same-class cycling and evdev parsing): 101/101 pass.