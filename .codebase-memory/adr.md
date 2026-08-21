# ADR: Self-healing auto-detect monitors (long-uptime blindness)

Date: 2026-08-20 · Status: accepted · Files: auto_detect.py, pc_widget_smoke_test.py

## Context
After days of uptime the bubble widget's window auto-detect silently died:
focusing the mapped window (VSCode → "Programming sessions") no longer
started the timer. Live diagnosis on a 5-day-old process showed:
- The KWin watcher script was loaded AND still delivering ActiveWindow
  events (forced kdialog probe → 6 DBus calls) — backend healthy.
- The evdev InputActivityMonitor held fds only for event1–20, while the
  keyboard actually in use was event27 (G604) / event29 (BT). The monitor
  opened /dev/input exactly once at startup; BT reconnects, dock replugs
  and suspend/resume re-enumerate devices under NEW event nodes. Result:
  last_activity froze → idle_seconds() grew unbounded → user_active
  permanently False in AutoDetectController._tick → auto-start never
  fired (and auto-stop killed running mapped timers).

## Decision
1. InputActivityMonitor._loop now owns a {fd: path} map and rescans
   /dev/input every 30 s (RESCAN_SECONDS) and every 1 s while it holds no
   devices; _merge_scan adopts new nodes and drops vanished paths; select
   errors rebuild the fd set instead of exiting the thread. Public API
   (idle_seconds/last_press/available/start/stop) unchanged.
2. _KWinBackend got two self-healing paths, because KWin restarts unload
   DBus-loaded scripts and loaded scripts can also be stopped without
   being unloaded (isScriptLoaded stays true): a QDBusServiceWatcher on
   org.kde.KWin reinstalls the watcher script when KWin re-registers, and
   a 60 s watchdog polls isScriptLoaded and reinstalls if missing.
   Reinstalling re-pushes the current active window (script does
   push(workspace.activeWindow) on load), so backend state re-syncs.
3. PyQt5 portability: the combined watch-mode enum
   (WatchForRegistrationAndUnregistration) does not exist as a flat
   attribute in all PyQt5 builds — OR the two base flags instead
   (_WATCH_REG_AND_UNREG). Found the hard way: first launch crashed.

## Consequences
- Device churn (BT keyboards sleeping/reconnecting, docks, resume) can
  blind auto-detect for at most ~30 s instead of forever.
- Regression coverage: smoke test section [9] drives the real monitor
  thread with pipe-backed fake devices through a device replacement.
- Watchdog adds one 2 s-timeout DBus roundtrip per minute on the Qt main
  thread — same class of blocking call the backend already makes.