"""
pc_widget_stats — today / week / month aggregates for the bubble tooltips.

Reads the Syncthing-synced habitsdb.txt (the same JSON the phone app
writes: {habit: {"YYYY-MM-DD": count, ...}}) and caches the aggregates,
re-reading only when the file's mtime changes or the day rolls over —
so the 1 Hz tooltip refresh stays cheap and numbers update within
seconds of the phone's copy syncing over.

Counts are reported the way the PHONE shows them — "effective points"
(mirroring HabitViewModel.effectivePointsForDate): each habit's raw
count (or its minutes:<habit> slot, for minutes-primary habits) divided
by the habit's divider. Raw minutes are never summed into the totals.

Qt-free and side-effect-light so it stays smoke-testable. All errors
simply yield empty stats (tooltips fall back to bare names).
"""

import glob
import json
import os
from datetime import date, timedelta

DEFAULT_DB_PATH = '~/habitsdb/habitsdb.txt'
WINDOW_DAYS = 30   # day totals kept for the month average

# Effective-points inputs (phone: HabitModels.applyDivider /
# HabitViewModel.effectivePointsForDate). Per-habit config comes from
# the first source that has it:
#   1. the bridge config entry ("divider" / "inverted_binary" /
#      "no_points" — used as soon as the phone starts sending them;
#      load_config passes them through)
#   2. ~/.config/pc_bubble_widget/point_overrides.json
#      {"Habit": {"divider": 30, "minutes_primary": true}, ...}
#   3. the newest parseable tail backup's settings block — the phone
#      auto-backs up to ~/habitsdb/Auto_backups/ (daily; a fresh file
#      can be mid-sync, so unparseable ones are skipped) and manual
#      backups land in ~/habitsdb/Manual_backups/. This is the only
#      PC-visible copy of the phone-local prefs: habitDividers,
#      widgetTimerMinutesPrimary, minutesPrimaryFallbacks,
#      secondaryValue(Fallback)Habits, invertedBinaryHabits.
#   4. MINUTES_DIVIDER_DEFAULT for minutes-primary habits, else 1
MINUTES_DIVIDER_DEFAULT = 30
OVERRIDES_PATH = os.path.expanduser(
    '~/.config/pc_bubble_widget/point_overrides.json')
BACKUP_GLOBS = (
    os.path.expanduser('~/habitsdb/Auto_backups/tail_auto_backup_*.json'),
    os.path.expanduser('~/habitsdb/Manual_backups/tail_backup_*.json'),
)
# auxiliary db slots consumed by their parent habit — never habits
# themselves (minutes:<h>, secondary_value<h>:<h> for any value index)
SLOT_PREFIXES = ('minutes:', 'secondary_value')

# ── Habit-button colour ladder ─────────────────────────────────────────────
# Mirrors the Android app's ui/HabitColors.kt getHabitStyle() exactly:
#   phase 1 (count 0-5)  solid muted backgrounds, no border on the phone
#   phase 2 (count 6)    glass (near-white) background, no border
#   phase 3 (count 7-12) glass + single vivid border cycling Red→Yellow
#   phase 4 (count 13-48, capped) glass + double vivid border
#                        (outer ring | thin black | inner ring), 6×6 combos
HABIT_BG = ['#3D1515',   # 0  muted dark red   (ColorRed)
            '#7A3800',   # 1  orange           (ColorOrange)
            '#1A4020',   # 2  green            (ColorGreen)
            '#102255',   # 3  blue             (ColorBlue)
            '#901060',   # 4  pink             (ColorPink)
            '#B8B000']   # 5  yellow           (ColorYellow)
GLASS_BG = '#D0D0E0'     # 6+ near-white       (ColorGlass)
VIVID = ['#CC3333',      # BorderRed
         '#E07020',      # BorderOrange
         '#33AA55',      # BorderGreen
         '#3366DD',      # BorderBlue
         '#DD44AA',      # BorderPink
         '#DDCC00']      # BorderYellow


def habit_style(count: int):
    """
    (background, border, outer, inner) hex colours for a habit's count
    today — the same style the phone's habit button gets from
    getHabitStyle(). border/outer/inner are None when that phase has no
    such ring. For counts 0-5 a vivid ring in the same hue is returned so
    the muted phase-1 backgrounds stay visible on the widget's dark theme.
    """
    if count <= 5:
        return (HABIT_BG[count], VIVID[count], None, None)
    if count == 6:
        return (GLASS_BG, None, None, None)
    if count <= 12:
        return (GLASS_BG, VIVID[count - 7], None, None)
    d = min(count - 13, 35)
    return (GLASS_BG, None, VIVID[d // 6], VIVID[d % 6])


def apply_divider(raw_count: int, divider: int) -> int:
    """
    The phone's HabitModels.applyDivider (ported in habit_models.py):
    divider <= 1 → the raw count stands; otherwise round(raw/divider),
    but any positive raw count always scores at least 1 point.
    """
    if divider <= 1:
        return raw_count
    if raw_count <= 0:
        return 0
    return max(round(raw_count / divider), 1)


class HabitStats:
    """mtime-cached view of habitsdb.txt for tooltip numbers."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._path = os.path.expanduser(db_path)
        self._mtime = None
        self._today_key = None
        self._habit_today = {}   # slot name -> raw count today (incl. minutes:*)
        self._day_totals = {}    # 'YYYY-MM-DD' -> effective points, all habits
        self._slot_days = {}     # slot name -> {'YYYY-MM-DD': raw count}
        # effective-points inputs (see set_point_config / _point_sources)
        self._cfg_dividers = {}  # habit -> divider from the bridge config
        self._cfg_minutes = set()  # habits flagged minutes_primary in config
        self._cfg_flags = {}     # habit -> {'inverted','nopoints'} bool|None
        self._src_sig = None      # (overrides, backup) change signature
        self._src = {}            # merged backup/override point config

    # ── loading ─────────────────────────────────────────────────────────

    def refresh(self):
        """Re-reads the db only if its mtime changed or the day rolled."""
        try:
            mtime = os.path.getmtime(self._path)
        except OSError:
            self._mtime = None
            self._today_key = None
            self._habit_today = {}
            self._day_totals = {}
            self._slot_days = {}
            return
        today_key = date.today().isoformat()
        if mtime == self._mtime and today_key == self._today_key:
            return
        self._mtime = mtime
        self._today_key = today_key
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                db = json.load(f)
        except (OSError, ValueError):
            db = None
        if not isinstance(db, dict):
            db = {}
        window = {(date.today() - timedelta(days=i)).isoformat()
                  for i in range(WINDOW_DAYS)}
        slot_days = {}
        for name, entries in db.items():
            if not isinstance(entries, dict):
                continue
            days = {}
            for dkey, val in entries.items():
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    continue
                if dkey in window or dkey == today_key:
                    days[dkey] = days.get(dkey, 0) + int(val)
            if days:
                slot_days[name] = days
        self._slot_days = slot_days
        self._habit_today = {n: d.get(today_key, 0)
                             for n, d in slot_days.items()}
        # Effective points per day — the number the phone's stats show.
        # Every habit scores its raw (or minutes) value through its
        # divider; auxiliary minutes:/secondary_value* slots are consumed
        # by their parent habit and never summed directly (raw minutes
        # were inflating the totals by ~10x).
        src = self._point_sources()
        all_days = set(window)
        all_days.add(today_key)
        day_totals = {}
        for name in slot_days:
            if name.startswith(SLOT_PREFIXES):
                continue
            for dkey in all_days:
                pts = self._effective_on(name, dkey, src)
                day_totals[dkey] = day_totals.get(dkey, 0) + pts
        self._day_totals = day_totals

    # ── queries ─────────────────────────────────────────────────────────

    def habit_today(self, name: str) -> int:
        """A habit's RAW count for today (0 when unknown/missing)."""
        return self._habit_today.get(name, 0)

    def habit_effective(self, name: str) -> int:
        """
        The points the phone would show for this habit today: the raw
        count (or the minutes:<habit> slot for minutes-primary habits,
        with the raw session count standing in on 0-minute days) through
        the habit's divider.
        """
        src = self._point_sources()
        return self._effective_on(name, self._today_key or
                                  date.today().isoformat(), src)

    # ── effective-points helpers ─────────────────────────────────────────

    def set_point_config(self, habits):
        """
        Feeds the phone-pushed widget config (load_config() output) so
        effective points match the phone: the minutes_primary flags now,
        the dividers and the inverted_binary / no_points subtype flags
        as soon as the phone starts sending them (None = field not sent
        yet → keep the overrides/backup answer for it).
        """
        dividers, minutes, flags = {}, set(), {}
        for h in habits or []:
            name = h.get('name') if isinstance(h, dict) else None
            if not isinstance(name, str) or not name:
                continue
            if h.get('minutes_primary'):
                minutes.add(name)
            d = h.get('divider')
            if isinstance(d, int) and not isinstance(d, bool) and d >= 1:
                dividers[name] = d
            inv = h.get('inverted_binary')
            nop = h.get('no_points')
            flags[name] = {
                'inverted': inv if isinstance(inv, bool) else None,
                'nopoints': nop if isinstance(nop, bool) else None,
            }
        self._cfg_dividers = dividers
        self._cfg_minutes = minutes
        self._cfg_flags = flags
        self._mtime = None   # force a re-read so totals recompute

    def _point_sources(self):
        """
        Point config from the newest parseable tail backup, overlaid
        with the user's overrides file. Cached until either source
        changes on disk.
        """
        globs = BACKUP_GLOBS if isinstance(BACKUP_GLOBS, (tuple, list)) \
            else (BACKUP_GLOBS,)
        candidates = []
        for pattern in globs:
            candidates.extend(glob.glob(pattern))
        candidates.sort(key=os.path.getmtime, reverse=True)
        try:
            ov_mtime = os.path.getmtime(OVERRIDES_PATH)
        except OSError:
            ov_mtime = None
        newest = candidates[0] if candidates else None
        try:
            bk_mtime = os.path.getmtime(newest) if newest else None
        except OSError:
            bk_mtime = None
        sig = (ov_mtime, newest, bk_mtime)
        if sig == self._src_sig:
            return self._src

        src = {'dividers': {}, 'minutes': set(), 'mp_fallbacks': {},
               'sec_fallback': set(), 'sec_habits': set(), 'inverted': set(),
               'nopoints': set(), 'disabled': set()}
        for path in candidates:            # newest first; skip mid-sync
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    settings = json.load(f).get('settings', {})
                if isinstance(settings, dict) and settings:
                    break
            except (OSError, ValueError, AttributeError):
                continue
        else:
            settings = {}

        def _ints(target, raw):
            if isinstance(raw, dict):
                for name, d in raw.items():
                    if isinstance(d, int) and not isinstance(d, bool) and d >= 1:
                        target[name] = d

        def _names(target, raw):
            if isinstance(raw, list):
                target.update(n for n in raw if isinstance(n, str))

        _ints(src['dividers'], settings.get('habitDividers'))
        _names(src['minutes'], settings.get('widgetTimerMinutesPrimary'))
        _names(src['sec_fallback'],
               settings.get('secondaryValueFallbackHabits'))
        _names(src['sec_habits'], settings.get('secondaryValueHabits'))
        _names(src['inverted'], settings.get('invertedBinaryHabits'))
        _names(src['nopoints'], settings.get('noPointsHabits'))
        _names(src['disabled'], settings.get('disabledHabits'))
        if isinstance(settings.get('minutesPrimaryFallbacks'), dict):
            for name, fb in settings['minutesPrimaryFallbacks'].items():
                if isinstance(fb, str):
                    src['mp_fallbacks'][name] = fb

        if ov_mtime is not None:           # user overrides win over backup
            try:
                with open(OVERRIDES_PATH, 'r', encoding='utf-8') as f:
                    over = json.load(f)
                if isinstance(over, dict):
                    for name, cfg in over.items():
                        if not isinstance(cfg, dict):
                            continue
                        d = cfg.get('divider')
                        if (isinstance(d, int) and not isinstance(d, bool)
                                and d >= 1):
                            src['dividers'][name] = d
                        if cfg.get('minutes_primary'):
                            src['minutes'].add(name)
            except (OSError, ValueError):
                pass
        self._src_sig = sig
        self._src = src
        return src

    @staticmethod
    def _with_fallback(value, divider, secondary):
        # HabitCalculator.effectivePointsWithFallback: a zero primary
        # value with a positive secondary stands undivided, else divide.
        if value <= 0 and secondary > 0:
            return secondary
        return apply_divider(value, divider)

    def _effective_on(self, name, dkey, src):
        """
        The phone's effectivePointsForDate for one habit on one day:
        inverted-binary → 1 unless done; minutes-primary → minutes
        through the divider (session count / second value standing in on
        zero-minute days per the habit's fallback mode); otherwise the
        raw count through the divider, with the legacy secondary slot
        (or minutes) standing in when enabled.
        """
        raw = self._slot_days.get(name, {}).get(dkey, 0)
        # bridge-config flags win over the (possibly stale) backup copy;
        # None means the phone hasn't sent the field yet
        cfg = self._cfg_flags.get(name) or {}
        nopoints = cfg.get('nopoints')
        if nopoints is None:
            nopoints = name in src['nopoints']
        if nopoints or name in src['disabled']:
            return 0   # tracked, but never part of the point totals
        inverted = cfg.get('inverted')
        if inverted is None:
            inverted = name in src['inverted']
        if inverted:
            return 1 if raw <= 0 else 0
        mp = name in self._cfg_minutes or name in src['minutes']
        divider = self._cfg_dividers.get(name)
        if divider is None:
            divider = src['dividers'].get(
                name, MINUTES_DIVIDER_DEFAULT if mp else 1)

        def slot(prefix):
            return self._slot_days.get(prefix + name, {}).get(dkey, 0)

        if mp:
            minutes = slot('minutes:')
            fb = src['mp_fallbacks'].get(name, 'sessions')
            if fb == 'none':
                return apply_divider(minutes, divider)
            if fb == 'value2':
                return self._with_fallback(minutes, divider,
                                           slot('secondary_value2:'))
            return self._with_fallback(minutes, divider, raw)  # sessions
        if name in src['sec_fallback']:
            # legacy generic secondary slot when the habit uses it or has
            # data there, otherwise the first-class minutes slot
            key = 'secondary_value:'
            if (name not in src['sec_habits']
                    and not self._slot_days.get(key + name)):
                key = 'minutes:'
            return self._with_fallback(raw, divider, slot(key))
        return apply_divider(raw, divider)

    def _avg(self, days: int) -> float:
        if not self._day_totals:
            return 0.0
        today = date.today()
        total = sum(self._day_totals.get(
            (today - timedelta(days=i)).isoformat(), 0) for i in range(days))
        return total / days

    def summary_lines(self):
        """
        Tooltip body for the center bubble: today's point total plus the
        7-day and 30-day daily averages. Empty when no data is available.
        """
        if not self._day_totals and not self._habit_today:
            return []
        return [
            'today: {} pts'.format(self._day_totals.get(self._today_key, 0)),
            'week avg: {}/day'.format(self._fmt(self._avg(7))),
            'month avg: {}/day'.format(self._fmt(self._avg(30))),
        ]

    @staticmethod
    def _fmt(v: float) -> str:
        return '{:.1f}'.format(v) if v < 10 else '{:.0f}'.format(v)
