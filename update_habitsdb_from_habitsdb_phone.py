"""
update_habitsdb_from_habitsdb_phone.py

Merges habitsdb_phone.txt (rolling 30-day phone data) into habitsdb.txt
(full unified history) using a CRDT-safe max() merge.

IMPORTANT: This script NEVER removes data from habitsdb.txt.
It only adds or updates entries where the phone has a higher value.
This is safe to run repeatedly — it is idempotent.

Called by habits_kde_theme_watchdog_phone.sh whenever habitsdb_phone.txt changes.
"""

import json
import os
from datetime import date, timedelta

OBSIDIAN_DIR = os.path.expanduser('~/noteVault/')
HABITSDB_PATH = OBSIDIAN_DIR + 'habitsdb.txt'
PHONE_PATH    = OBSIDIAN_DIR + 'habitsdb_phone.txt'

TODAY = date.today()
today_str = str(TODAY)


def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"WARNING: Could not load {path}: {e}")
        return {}


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)


def merge_max(db_data, phone_data):
    """
    Merge phone_data into db_data using max() per date entry.
    Never removes any data — only adds or increases values.
    Returns the merged result.
    """
    all_habits = set(db_data.keys()) | set(phone_data.keys())
    merged = {}
    changes = 0

    for habit in sorted(all_habits):
        d_entries = db_data.get(habit, {})
        p_entries = phone_data.get(habit, {})
        all_dates = set(d_entries.keys()) | set(p_entries.keys())

        merged_entries = {}
        for ds in all_dates:
            dv = d_entries.get(ds, 0)
            pv = p_entries.get(ds, 0)
            merged_val = max(dv, pv)
            merged_entries[ds] = merged_val
            if pv > dv:
                changes += 1

        merged[habit] = dict(sorted(merged_entries.items()))

    print(f"  Phone entries that updated habitsdb: {changes}")
    return merged


def fill_missing_days(merged):
    """Fill any gaps up to today with 0 for all habits."""
    fill_count = 0
    for habit, entries in merged.items():
        if not entries:
            entries[today_str] = 0
            fill_count += 1
            continue
        latest_str = max(entries.keys())
        if latest_str < today_str:
            cursor = date.fromisoformat(latest_str) + timedelta(days=1)
            while cursor <= TODAY:
                ds = str(cursor)
                if ds not in entries:
                    entries[ds] = 0
                    fill_count += 1
                cursor += timedelta(days=1)
        merged[habit] = dict(sorted(entries.items()))
    if fill_count:
        print(f"  Filled {fill_count} missing day entries up to today")
    return merged


def main():
    print(f"[update_habitsdb_from_habitsdb_phone] Running at {TODAY}")

    db_data    = load_json(HABITSDB_PATH)
    phone_data = load_json(PHONE_PATH)

    if not db_data:
        print("ERROR: habitsdb.txt is empty or missing — aborting to prevent data loss!")
        return

    if not phone_data:
        print("WARNING: habitsdb_phone.txt is empty or missing — nothing to merge.")
        return

    print(f"  habitsdb.txt:    {len(db_data)} habits")
    print(f"  habitsdb_phone:  {len(phone_data)} habits")

    # Sanity check: if habitsdb.txt is suspiciously small, abort
    db_total_entries = sum(len(v) for v in db_data.values())
    if db_total_entries < 1000:
        print(f"WARNING: habitsdb.txt has only {db_total_entries} total entries — looks truncated!")
        print("  Proceeding with merge anyway (phone data will be added, not lost).")

    merged = merge_max(db_data, phone_data)
    merged = fill_missing_days(merged)

    print(f"  Total merged habits: {len(merged)}")

    # Verify we didn't lose data
    merged_total = sum(len(v) for v in merged.values())
    db_total = sum(len(v) for v in db_data.values())
    if merged_total < db_total:
        print(f"ERROR: Merge would reduce entries from {db_total} to {merged_total} — aborting!")
        return

    save_json(HABITSDB_PATH, merged)
    print(f"  Saved merged DB to {HABITSDB_PATH}")

    # Verify key habits after save
    for h in ['Apnea spb', 'Chess', 'AI tool']:
        entries = merged.get(h, {})
        nonzero = {k: v for k, v in entries.items() if v > 0}
        if nonzero:
            last = max(nonzero.keys())
            print(f"  {h}: last_nonzero={last}")

    print("[update_habitsdb_from_habitsdb_phone] Done.")


if __name__ == '__main__':
    main()
