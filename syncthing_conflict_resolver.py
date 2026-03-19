#!/usr/bin/env python3
"""
Syncthing conflict resolver for habitsdb.txt
=============================================
Watches the noteVault directory for Syncthing conflict files matching:
    habitsdb.sync-conflict-*.txt

When found, merges the conflict file into habitsdb.txt using max() per date
entry (CRDT G-Counter: habit counts only ever increase, so max() is always
the correct conflict-free merge), then deletes the conflict file.

Also handles screens_layout.json conflicts using last-writer-wins (keep the
conflict file with the most recent mtime, discard the other).

Usage:
    python3 syncthing_conflict_resolver.py [--watch] [--once]

    --watch  Run continuously, polling every 10 seconds (default)
    --once   Run once and exit (useful for cron / systemd timer)

Install as a systemd user service or add to your startup scripts.
"""

import json
import os
import sys
import time
import glob
import shutil
import argparse
from datetime import date, timedelta

NOTEVAULT = '/home/twain/noteVault'
HABITSDB  = os.path.join(NOTEVAULT, 'habitsdb.txt')
SCREENS   = os.path.join(NOTEVAULT, 'tail', 'screens_layout.json')

POLL_INTERVAL = 10  # seconds between scans


# ── Merge helpers ─────────────────────────────────────────────────────────────

def merge_habitsdb(base_path: str, conflict_path: str) -> bool:
    """
    Merge conflict_path into base_path using max() per date entry.
    Returns True if the merge was applied and the conflict file deleted.
    """
    try:
        with open(base_path, 'r') as f:
            base: dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[conflict-resolver] ERROR reading base {base_path}: {e}")
        return False

    try:
        with open(conflict_path, 'r') as f:
            conflict: dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[conflict-resolver] ERROR reading conflict {conflict_path}: {e}")
        return False

    all_habits = set(base.keys()) | set(conflict.keys())
    merged = {}
    changes = 0

    for habit in sorted(all_habits):
        b_entries = base.get(habit, {})
        c_entries = conflict.get(habit, {})
        all_dates = set(b_entries.keys()) | set(c_entries.keys())
        merged_entries = {}
        for ds in all_dates:
            bv = b_entries.get(ds, 0)
            cv = c_entries.get(ds, 0)
            merged_entries[ds] = max(bv, cv)
            if cv > bv:
                changes += 1
        merged[habit] = dict(sorted(merged_entries.items()))

    # Fill missing days up to today
    today_str = str(date.today())
    for habit, entries in merged.items():
        if not entries:
            entries[today_str] = 0
            continue
        latest_str = max(entries.keys())
        if latest_str < today_str:
            cursor = date.fromisoformat(latest_str) + timedelta(days=1)
            while cursor <= date.today():
                ds = str(cursor)
                if ds not in entries:
                    entries[ds] = 0
                cursor = cursor + timedelta(days=1)
        merged[habit] = dict(sorted(entries.items()))

    # Write merged result back to base
    try:
        with open(base_path, 'w') as f:
            json.dump(merged, f, indent=4)
    except OSError as e:
        print(f"[conflict-resolver] ERROR writing merged DB: {e}")
        return False

    os.remove(conflict_path)
    print(f"[conflict-resolver] Merged habitsdb conflict: {os.path.basename(conflict_path)}"
          f" ({changes} entries from conflict took precedence)")
    return True


def resolve_screens_conflict(base_path: str, conflict_path: str) -> bool:
    """
    Resolve a screens_layout.json conflict using last-writer-wins:
    keep whichever file has the newer mtime, delete the other.
    Returns True if resolved.
    """
    try:
        base_mtime    = os.path.getmtime(base_path)
        conflict_mtime = os.path.getmtime(conflict_path)
    except OSError as e:
        print(f"[conflict-resolver] ERROR stat-ing screens files: {e}")
        return False

    if conflict_mtime > base_mtime:
        # Conflict file is newer — replace base with it
        shutil.copy2(conflict_path, base_path)
        os.remove(conflict_path)
        print(f"[conflict-resolver] screens_layout conflict resolved: kept conflict (newer)")
    else:
        # Base is newer (or same) — just delete the conflict file
        os.remove(conflict_path)
        print(f"[conflict-resolver] screens_layout conflict resolved: kept base (newer)")
    return True


# ── Scanner ───────────────────────────────────────────────────────────────────

def scan_and_resolve():
    """Scan for conflict files and resolve them."""
    resolved = 0

    # habitsdb.txt conflicts:  habitsdb.sync-conflict-YYYYMMDD-HHMMSS-XXXXXXX.txt
    pattern_habitsdb = os.path.join(NOTEVAULT, 'habitsdb.sync-conflict-*.txt')
    for conflict_path in sorted(glob.glob(pattern_habitsdb)):
        if merge_habitsdb(HABITSDB, conflict_path):
            resolved += 1

    # screens_layout.json conflicts
    screens_dir = os.path.join(NOTEVAULT, 'tail')
    pattern_screens = os.path.join(screens_dir, 'screens_layout.sync-conflict-*.json')
    for conflict_path in sorted(glob.glob(pattern_screens)):
        if resolve_screens_conflict(SCREENS, conflict_path):
            resolved += 1

    return resolved


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Syncthing conflict resolver for habitsdb.txt')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--watch', action='store_true', default=True,
                       help='Run continuously (default)')
    group.add_argument('--once', action='store_true',
                       help='Run once and exit')
    args = parser.parse_args()

    if args.once:
        n = scan_and_resolve()
        print(f"[conflict-resolver] Done. Resolved {n} conflict(s).")
        return

    print(f"[conflict-resolver] Watching {NOTEVAULT} every {POLL_INTERVAL}s ...")
    while True:
        try:
            scan_and_resolve()
        except Exception as e:
            print(f"[conflict-resolver] Unexpected error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
