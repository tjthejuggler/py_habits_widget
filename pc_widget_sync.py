"""
pc_widget_sync — HTTP transport between the PC bubble widget and the phone.

Everything flows through the local Tail Bridge server (the same FastAPI
process that serves the Garmin proxy data and the movie cache), so there is
no sync folder to pick and no Syncthing involved:

  GET  /api/v1/pc_widget/config   (phone → PC)   habit squares to show
  POST /api/v1/pc_widget/event    (PC → phone)   queue one habit event
  GET  /api/v1/pc_widget/events   (PC)           events not yet acked
  POST /api/v1/pc_widget/acks     (phone → PC)   phone acks (bridge prunes)

The bridge is the single writer of its state files (~/.config/tail_bridge/),
so there are never same-file conflicts. The phone derives the bridge URL
from its Garmin proxy settings; the widget simply talks to localhost.

Auth: the X-App-Auth shared secret (ANDROID_PROXY_KEY), resolved from the
environment or the bridge's .env file — zero configuration.

This module is Qt-free and side-effect-light so it can be smoke-tested
standalone. All functions swallow transport errors and return None/empty
so a temporarily-down bridge never crashes the widget.
"""

import glob
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional

DEFAULT_BRIDGE_URL = 'http://127.0.0.1:8001'
REQUEST_TIMEOUT = 5.0

# Places the bridge's .env may live (systemd EnvironmentFile). Scanned in
# order; first hit wins. Override everything with PC_WIDGET_TOKEN.
ENV_FILE_CANDIDATES = [
    '~/AndroidStudioProjects/tail/tail_bridge/.env',
    '~/Projects/tail_bridge/.env',
]
ENV_FILE_GLOBS = [
    '~/AndroidStudioProjects/*/tail_bridge/.env',
    '~/Projects/*/tail_bridge/.env',
]
TOKEN_FILE = '~/.config/tail_bridge/token'

_token_cache = None


def bridge_url() -> str:
    """Base URL of the local Tail Bridge (override: PC_WIDGET_BRIDGE_URL)."""
    return os.environ.get('PC_WIDGET_BRIDGE_URL', DEFAULT_BRIDGE_URL).rstrip('/')


def resolve_token() -> str:
    """
    Finds the X-App-Auth shared secret:
      1. PC_WIDGET_TOKEN env var
      2. ANDROID_PROXY_KEY env var (same var the bridge itself reads)
      3. tail_bridge/.env file (ANDROID_PROXY_KEY=... line)
      4. ~/.config/tail_bridge/token file
    """
    global _token_cache
    if _token_cache:
        return _token_cache
    token = (os.environ.get('PC_WIDGET_TOKEN')
             or os.environ.get('ANDROID_PROXY_KEY')
             or '').strip()
    if not token:
        paths = [os.path.expanduser(p) for p in ENV_FILE_CANDIDATES]
        for pattern in ENV_FILE_GLOBS:
            paths.extend(sorted(glob.glob(os.path.expanduser(pattern))))
        for path in paths:
            token = _read_env_file_key(path, 'ANDROID_PROXY_KEY')
            if token:
                break
    if not token:
        try:
            with open(os.path.expanduser(TOKEN_FILE), 'r', encoding='utf-8') as f:
                token = f.read().strip()
        except OSError:
            token = ''
    _token_cache = token
    return token


def _read_env_file_key(path: str, key: str) -> str:
    """Parses KEY=value lines from a .env file; '' when missing/unreadable."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return ''


def _request(method: str, path: str, payload: Optional[dict] = None) -> Optional[dict]:
    """
    One authenticated JSON call against the bridge. Returns the parsed body,
    or None on any transport/HTTP error (never raises).
    """
    token = resolve_token()
    if not token:
        return None
    url = '{}/api/v1/{}'.format(bridge_url(), path)
    data = None
    headers = {'X-App-Auth': token}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode('utf-8')
            return json.loads(body) if body else {}
    except (urllib.error.URLError, OSError, ValueError):
        return None


def bridge_available() -> bool:
    """True when the bridge answers an authenticated call."""
    return _request('GET', 'pc_widget/config') is not None


def load_config() -> Optional[List[Dict]]:
    """
    Fetches the habit-square config pushed by the phone:
    [{"name": str, "icon": str|None, "minutes_primary": bool,
      "divider": int|None, "inverted_binary": bool|None,
      "no_points": bool|None}, ...]
    The effective-points inputs (phone-side habitDividers /
    invertedBinaryHabits / noPointsHabits) are passed through when the
    phone sends them; None means the field hasn't arrived yet, so the
    stats layer falls back to its overrides/backup sources.
    Returns None when the bridge is unreachable (caller keeps its last
    known config); [] when the phone has toggled nothing on yet.
    Malformed entries are dropped individually.
    """
    root = _request('GET', 'pc_widget/config')
    if root is None:
        return None
    habits: List[Dict] = []
    for raw in root.get('habits') or []:
        if not isinstance(raw, dict):
            continue
        name = raw.get('name')
        if not isinstance(name, str) or not name.strip():
            continue
        icon = raw.get('icon')
        div = raw.get('divider')
        inv = raw.get('inverted_binary')
        nop = raw.get('no_points')
        habits.append({
            'name': name,
            'icon': icon if isinstance(icon, str) and icon else None,
            'minutes_primary': bool(raw.get('minutes_primary', False)),
            'divider': div if (isinstance(div, int) and not isinstance(div, bool)
                               and div >= 1) else None,
            'inverted_binary': inv if isinstance(inv, bool) else None,
            'no_points': nop if isinstance(nop, bool) else None,
        })
    return habits


def append_event(
    habit: str,
    kind: str = 'session',
    start: Optional[datetime] = None,
    minutes: int = 0,
    end: Optional[datetime] = None,
) -> Optional[str]:
    """
    Queues one event on the bridge and returns its ID (None on failure —
    the bridge assigns the ID, keeping it the single writer).

    kind: 'session' (timer with minutes) or 'tap' (quick +1).
    start: when the habit actually happened (session start / tap time) —
           the phone records its timestamp at THIS time, not at delivery.
    end:   when the habit actually stopped (defaults to now). Auto-detect
           finalizes retroactively after its grace minute, at the moment
           window activity stopped — not at delivery time.
    """
    now = datetime.now()
    start = start or now
    finish = end or now
    payload = {
        'habit': habit,
        'kind': kind,
        'date': start.strftime('%Y-%m-%d'),
        'start': start.strftime('%H:%M:%S'),
        'end': finish.strftime('%H:%M:%S'),
        'minutes': max(0, int(minutes)),
    }
    root = _request('POST', 'pc_widget/event', payload)
    if root is None:
        return None
    event_id = root.get('id')
    return event_id if isinstance(event_id, str) and event_id else None


def load_config_full() -> Optional[dict]:
    """
    The whole phone-pushed config body: {"version", "updated_at",
    "habits": [...], "all_habits": [name, ...]}. "all_habits" is the
    phone's FULL habit catalog — the settings screen's habit-picker
    source; it is absent until the phone app pushes the newer format
    (the picker then falls back to the currently-enabled habits).
    Returns None when the bridge is unreachable.
    """
    return _request('GET', 'pc_widget/config')


def append_toggle_event(habit: str, enabled: bool) -> Optional[str]:
    """
    Queues a PC→phone habit-toggle request on the bridge (the settings
    screen's habit picker): the phone's event poller applies it to its
    "PC widget" toggles — exactly as if the switch had been flipped in
    the Android app — and pushes the updated widget config back, which
    the bubble picks up on its config poll. Carries the ABSOLUTE
    desired state, so at-least-once redelivery stays idempotent.
    """
    payload = {
        'habit': habit,
        'kind': 'toggle_pc_widget_habit',
        'enabled': bool(enabled),
    }
    root = _request('POST', 'pc_widget/event', payload)
    if root is None:
        return None
    event_id = root.get('id')
    return event_id if isinstance(event_id, str) and event_id else None


def pending_events() -> Optional[List[dict]]:
    """
    Events queued on the bridge that the phone has not acked yet.
    Returns None when the bridge is unreachable (caller keeps its badges).
    """
    root = _request('GET', 'pc_widget/events')
    if root is None:
        return None
    events = root.get('events')
    if not isinstance(events, list):
        return []
    return [e for e in events if isinstance(e, dict)]


def pending_event_ids() -> set:
    """IDs of un-acked events (empty set when the bridge is unreachable)."""
    events = pending_events()
    return {e['id'] for e in (events or []) if isinstance(e.get('id'), str)}
