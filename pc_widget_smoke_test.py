#!/usr/bin/env python3
"""
pc_widget_smoke_test — end-to-end check of the PC bubble widget against an
in-process fake Tail Bridge (same endpoints/auth/pruning semantics as
tail_bridge/bridge_server.py). Qt runs offscreen, so this works headless.

Run with the project venv:
  ./py_habits_widget/bin/python pc_widget_smoke_test.py
"""

import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TOKEN = 'smoke-test-token'
STATE = {
    'config': {'version': 1, 'habits': []},
    'events': [],
}


class FakeBridge(BaseHTTPRequestHandler):
    """Mirrors the /api/v1/pc_widget/* endpoints of bridge_server.py."""

    def log_message(self, *args):
        pass

    def _authed(self) -> bool:
        return self.headers.get('X-App-Auth') == TOKEN

    def _send(self, code: int, body: dict):
        data = json.dumps(body).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._authed():
            return self._send(403, {'detail': 'Forbidden'})
        if self.path == '/api/v1/pc_widget/config':
            return self._send(200, STATE['config'])
        if self.path == '/api/v1/pc_widget/events':
            return self._send(200, {'version': 1, 'events': STATE['events']})
        self._send(404, {'detail': 'not found'})

    def do_POST(self):
        if not self._authed():
            return self._send(403, {'detail': 'Forbidden'})
        length = int(self.headers.get('Content-Length') or 0)
        try:
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
        except ValueError:
            return self._send(400, {'detail': 'bad json'})
        if self.path == '/api/v1/pc_widget/config':
            STATE['config'] = payload
            return self._send(200, {'status': 'ok'})
        if self.path == '/api/v1/pc_widget/event':
            event_id = 'pc-{}-fake01'.format(int(time.time() * 1000))
            payload['id'] = event_id
            STATE['events'].append(payload)
            return self._send(200, {'status': 'queued', 'id': event_id})
        if self.path == '/api/v1/pc_widget/acks':
            done = set(payload.get('processed') or [])
            STATE['events'] = [e for e in STATE['events']
                               if e.get('id') not in done]
            return self._send(200, {'status': 'ok', 'remaining': len(STATE['events'])})
        self._send(404, {'detail': 'not found'})


def start_fake_bridge():
    server = ThreadingHTTPServer(('127.0.0.1', 0), FakeBridge)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, 'http://127.0.0.1:{}'.format(server.server_address[1])


def post_acks_like_phone(ids):
    """Phone-side ack call (what PcEventQueueProcessor does)."""
    req = urllib.request.Request(
        'http://127.0.0.1:{}/api/v1/pc_widget/acks'.format(BRIDGE_PORT),
        data=json.dumps({'processed': ids}).encode('utf-8'),
        headers={'X-App-Auth': TOKEN, 'Content-Type': 'application/json'},
        method='POST')
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode('utf-8'))


BRIDGE_PORT = None


def main() -> int:
    global BRIDGE_PORT
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    server, base_url = start_fake_bridge()
    BRIDGE_PORT = server.server_address[1]
    os.environ['PC_WIDGET_BRIDGE_URL'] = base_url
    os.environ['PC_WIDGET_TOKEN'] = TOKEN

    import pc_widget_sync as sync
    import pc_widget_stats as stats_mod

    # keep effective-points sources deterministic: never read the real
    # ~/.config overrides or ~/habitsdb/Manual_backups during the test
    stats_mod.OVERRIDES_PATH = os.path.join(tempfile.gettempdir(),
                                            'pc_widget_smoke_no_ovr.json')
    stats_mod.BACKUP_GLOBS = os.path.join(tempfile.gettempdir(),
                                          'pc_widget_smoke_no_bk_*.json')
    failures = []

    def check(label, ok):
        print('  {} {}'.format('PASS' if ok else 'FAIL', label))
        if not ok:
            failures.append(label)

    # ── sync layer ──────────────────────────────────────────────────────
    print('[1] sync layer against fake bridge')
    check('token resolved from env', sync.resolve_token() == TOKEN)
    check('bridge_available', sync.bridge_available())

    habits = sync.load_config()
    check('empty config → []', habits == [])

    STATE['config'] = {'version': 1, 'habits': [
        {'name': 'Meditation', 'icon': 'lotus', 'minutes_primary': True,
         'divider': 30, 'inverted_binary': False, 'no_points': False},
        {'name': 'Reading', 'icon': None, 'minutes_primary': False,
         'inverted_binary': False, 'no_points': False},
        {'name': '', 'icon': None},          # malformed → dropped
        'garbage',                            # malformed → dropped
    ]}
    habits = sync.load_config()
    check('config parsed + validated', habits == [
        {'name': 'Meditation', 'icon': 'lotus', 'minutes_primary': True,
         'divider': 30, 'inverted_binary': False, 'no_points': False},
        {'name': 'Reading', 'icon': None, 'minutes_primary': False,
         'divider': None, 'inverted_binary': False, 'no_points': False},
    ])
    # True flags pass through untouched — probed here so the live widget
    # fixture stays scoring-neutral (Reading keeps earning its 2 pts)
    STATE['config']['habits'][1].update(inverted_binary=True, no_points=True)
    probe = sync.load_config()
    check('config True flags pass through',
          probe[1]['inverted_binary'] is True and probe[1]['no_points'] is True)
    STATE['config']['habits'][1].update(inverted_binary=False, no_points=False)

    start = datetime.now() - timedelta(minutes=25)
    event_id = sync.append_event('Meditation', kind='session',
                                 start=start, minutes=25)
    check('event queued, server-assigned id', bool(event_id))
    pending = sync.pending_events()
    check('pending shows 1 event for Meditation',
          pending is not None and len(pending) == 1
          and pending[0]['habit'] == 'Meditation')
    check('event carries real start time',
          pending and pending[0]['start'] == start.strftime('%H:%M:%S')
          and pending[0]['minutes'] == 25)
    check('pending_event_ids compat', sync.pending_event_ids() == {event_id})

    result = post_acks_like_phone([event_id])
    check('phone ack prunes server queue',
          result.get('remaining') == 0 and sync.pending_events() == [])

    # ── widget layer (offscreen Qt) ─────────────────────────────────────
    print('[2] offscreen widget')
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer, QEventLoop
    from pc_bubble_widget import BubbleWidget
    import pc_bubble_widget as widget_mod

    # never touch the real ~/.config state file while testing
    widget_mod.STATE_FILE = os.path.join(
        tempfile.gettempdir(), 'pc_widget_smoke_state.json')

    # deterministic tooltip stats: temp habitsdb with known today counts
    tmp_db = os.path.join(tempfile.gettempdir(),
                          'pc_widget_smoke_habitsdb.json')
    with open(tmp_db, 'w') as f:
        json.dump({'Meditation': {date.today().isoformat(): 5},
                   'Reading': {date.today().isoformat(): 2}}, f)

    app = QApplication([])
    bubble = BubbleWidget()
    bubble.stats = widget_mod.HabitStats(tmp_db)
    check('squares built from bridge config',
          [s.habit_name for s in bubble.squares] == ['Meditation', 'Reading'])

    # config change propagates on poll
    STATE['config']['habits'].append(
        {'name': 'Stretch', 'icon': None, 'minutes_primary': False})
    bubble._poll_config()
    check('config poll adds new square',
          [s.habit_name for s in bubble.squares] ==
          ['Meditation', 'Reading', 'Stretch'])

    # tap flow: start timer, stop with backdated session
    sq = bubble.squares[0]
    bubble.on_square_clicked(sq)                       # start
    check('timer started', bubble.any_running())
    bubble.timers['Meditation'] = datetime.now() - timedelta(minutes=12)
    bubble.on_square_clicked(sq)                       # stop → event
    check('timer stopped', not bubble.any_running())
    check('pending badge = 1',
          bubble.pending_by_habit.get('Meditation') == 1)
    check('pending tooltip explains the dot',
          'waiting for the phone'
          in '\n'.join(bubble.squares[0].tooltip_lines()))
    check('square tooltip shows today count + unit',
          bubble.squares[0].tooltip_lines()[:2] ==
          ['Meditation', 'today: 5 min'])

    # phone acks → badge clears on poll
    evs = sync.pending_events()
    post_acks_like_phone([e['id'] for e in evs])
    bubble._poll_acks()
    check('ack poll clears badge',
          bubble.pending_by_habit.get('Meditation', 0) == 0)
    check('ack tooltip explains the flash',
          'phone confirmed'
          in '\n'.join(bubble.squares[0].tooltip_lines()))
    bubble.squares[0].acked_flash_until = 0.0
    check('tooltip reverts to name + today line',
          bubble.squares[0].tooltip_lines() ==
          ['Meditation', 'today: 5 min'])

    # ── ring layout + backdate (right-click menu) ──────────────────────
    print('[3] ring layout + backdate')
    from pc_bubble_widget import REST_R, TUCK_R, SQUARE_D

    bubble._near = False
    bubble._apply_layout_now()
    check('idle squares tuck in when mouse away',
          all(abs(s._radius - TUCK_R) < 0.5 for s in bubble.squares))
    check('window sized to spread ring',
          bubble.width() == 2 * (bubble._spread_r + SQUARE_D // 2) + 8)

    bubble.on_square_clicked(bubble.squares[0])       # start Meditation
    bubble._apply_layout_now()
    check('running square stays prominent at rest radius',
          abs(bubble.squares[0]._radius - REST_R) < 0.5)
    check('idle squares stay tucked',
          all(abs(s._radius - TUCK_R) < 0.5 for s in bubble.squares[1:]))

    bubble._near = True
    bubble._apply_layout_now()
    check('mouse near spreads every square out',
          all(abs(s._radius - bubble._spread_r) < 0.5 for s in bubble.squares))
    bubble._near = False

    before = bubble.elapsed_for('Meditation')
    check('backdate_timer pulls the start 1 min back',
          bubble.backdate_timer('Meditation', 1))
    check('backdate adds ~60 s to elapsed',
          55 <= bubble.elapsed_for('Meditation') - before <= 65)
    check('backdate refuses idle habit',
          not bubble.backdate_timer('Reading', 1))
    bubble.on_square_clicked(bubble.squares[0])       # stop → event queued

    # ── hover enter/leave drives the spread (Wayland-safe) ─────────────
    print('[4] hover enter/leave spread')
    bubble.show()                                    # visible → proximity live
    bubble._near = False
    bubble._apply_layout_now()
    bubble._hover_entered(bubble.squares[1])
    check('entering a square spreads the ring', bubble._near)
    bubble._apply_layout_now()
    check('spread radius applied on hover',
          all(abs(s._radius - bubble._spread_r) < 0.5 for s in bubble.squares))

    bubble._pin_spread = True
    bubble._hover_left(bubble.squares[1])
    check('pinned (menu open) keeps the ring spread', bubble._near)
    bubble._pin_spread = False
    bubble._hover_left(bubble.squares[1])            # nothing hovered → debounce
    loop = QEventLoop()
    QTimer.singleShot(400, loop.quit)
    loop.exec_()
    check('leaving the widget contracts the ring (Wayland path)',
          not bubble._near)
    bubble._apply_layout_now()
    check('idle squares tucked again',
          all(abs(s._radius - TUCK_R) < 0.5 for s in bubble.squares))

    # ── square click vs drag ───────────────────────────────────────────
    print('[5] square click vs drag')
    from PyQt5.QtGui import QMouseEvent
    from PyQt5.QtCore import QEvent, QPointF, Qt

    sq = bubble.squares[2]                          # Stretch (idle)

    def mouse_ev(ev_type, button, buttons, gpos):
        return QMouseEvent(ev_type, QPointF(23, 23), gpos,
                           button, buttons, Qt.NoModifier)

    gp = QPointF(500, 500)
    sq.mousePressEvent(mouse_ev(QEvent.MouseButtonPress, Qt.LeftButton,
                                Qt.LeftButton, gp))
    sq.mouseReleaseEvent(mouse_ev(QEvent.MouseButtonRelease, Qt.LeftButton,
                                  Qt.NoButton, gp))
    check('plain square click toggles its timer', 'Stretch' in bubble.timers)
    bubble.on_square_clicked(sq)                    # stop → tap event queued

    sq.mousePressEvent(mouse_ev(QEvent.MouseButtonPress, Qt.LeftButton,
                                Qt.LeftButton, gp))
    sq.mouseMoveEvent(mouse_ev(QEvent.MouseMove, Qt.NoButton,
                               Qt.LeftButton, QPointF(700, 700)))
    check('drag past threshold starts a widget drag',
          bubble._drag_offset is not None)
    sq.mouseReleaseEvent(mouse_ev(QEvent.MouseButtonRelease, Qt.LeftButton,
                                  Qt.NoButton, QPointF(700, 700)))
    check('release ends the drag', bubble._drag_offset is None)
    check('drag does not toggle the timer', 'Stretch' not in bubble.timers)

    # ── stats module + center-bubble tooltip ───────────────────────────
    print('[6] stats + bubble tooltip')
    from pc_widget_stats import HabitStats as Stats

    s = Stats(tmp_db)
    s.refresh()
    check('habit_today reads the db',
          s.habit_today('Meditation') == 5 and s.habit_today('Reading') == 2)
    check('unknown habit → 0', s.habit_today('Nope') == 0)
    check('summary shows today total', s.summary_lines()[0] == 'today: 7 pts')
    check('missing db → empty summary',
          Stats('/nonexistent/habitsdb.json').summary_lines() == [])

    lines = bubble.tooltip_lines()
    check('bubble tooltip shows today total',
          'today: 7 pts' in lines)
    check('bubble tooltip shows averages',
          any('week avg:' in l for l in lines)
          and any('month avg:' in l for l in lines))

    # custom per-widget tooltips: each square its own message, center bubble
    # the summary — QToolTip popups shown at the cursor (platform-placed,
    # Wayland-safe). The display seam records (target, text) calls.
    def wait(ms=700):
        l = QEventLoop()
        QTimer.singleShot(ms, l.quit)
        l.exec_()

    shown = []
    orig_show, orig_hide = (widget_mod.show_tip_text,
                            widget_mod.hide_tip_text)
    widget_mod.show_tip_text = lambda pos, text, target: shown.append(
        (target, text))
    widget_mod.hide_tip_text = lambda: shown.clear()

    bubble._hover_entered(bubble.squares[0])
    bubble.request_tooltip(bubble.squares[0])
    check('tooltip request arms the show timer', bubble._tip_timer.isActive())
    wait()
    check('square hover shows its own message at the cursor',
          bool(shown) and shown[-1][0] is bubble.squares[0]
          and 'Meditation' in shown[-1][1]
          and 'today: 5 min' in shown[-1][1])
    bubble._hover_left(bubble.squares[0])
    check('leaving the square hides the tooltip', not shown)

    bubble._hover_entered(bubble)
    bubble.request_tooltip(bubble)
    wait()
    check('center bubble shows the summary message',
          bool(shown) and shown[-1][0] is bubble
          and 'Tail' in shown[-1][1]
          and 'today: 7 pts' in shown[-1][1])
    bubble._hover_left(bubble)
    check('leaving the bubble hides the tooltip', not shown)
    widget_mod.show_tip_text, widget_mod.hide_tip_text = orig_show, orig_hide

    # ── black-hole collapse + Android tier colours ──────────────────────
    print('[7] black-hole collapse + habit colours')
    from pc_bubble_widget import BUBBLE_D
    from pc_widget_stats import habit_style as hstyle

    check('style ladder matches the phone app (0-5 solid)',
          hstyle(0)[0] == '#3D1515' and hstyle(1)[0] == '#7A3800'
          and hstyle(2)[0] == '#1A4020' and hstyle(5)[0] == '#B8B000')
    check('style ladder matches the phone app (6+ glass + borders)',
          hstyle(6) == ('#D0D0E0', None, None, None)
          and hstyle(7)[1] == '#CC3333' and hstyle(12)[1] == '#DDCC00'
          and hstyle(13) == ('#D0D0E0', None, '#CC3333', '#CC3333')
          and hstyle(49) == ('#D0D0E0', None, '#DDCC00', '#DDCC00'))
    check('squares pick up their habit style (Meditation today=5)',
          bubble.squares[0]._today_style()[0] == '#B8B000')

    # ── effective points (what the phone's buttons/stats actually show) ─
    from pc_widget_stats import apply_divider

    check('apply_divider mirrors the phone (round, min 1)',
          apply_divider(28, 30) == 1 and apply_divider(0, 30) == 0
          and apply_divider(1, 30) == 1 and apply_divider(45, 30) == 2
          and apply_divider(7, 1) == 7)

    # minutes-primary habit: minutes/30 → 2 pts; plain habits keep raw
    tmp_db2 = os.path.join(tempfile.gettempdir(),
                           'pc_widget_smoke_habitsdb2.json')
    with open(tmp_db2, 'w') as f:
        json.dump({'Stretch': {date.today().isoformat(): 3},
                   'minutes:Stretch': {date.today().isoformat(): 70},
                   'Drew': {date.today().isoformat(): 1},
                   'Writing': {date.today().isoformat(): 0}}, f)
    s2 = Stats(tmp_db2)
    s2.set_point_config([{'name': 'Stretch', 'minutes_primary': True,
                          'divider': 30}])
    s2.refresh()
    check('minutes-primary habit scores minutes/divider (70/30 → 2)',
          s2.habit_effective('Stretch') == 2)
    check('plain habits keep their raw count (1 → 1, 0 → 0)',
          s2.habit_effective('Drew') == 1 and s2.habit_effective('Writing') == 0)
    check('day totals sum effective points, not raw minutes',
          s2.summary_lines()[0] == 'today: 3 pts')

    # minutes-primary with zero minutes falls back to the session count
    check('widget Meditation (5 sessions, no minutes) → 5 via fallback',
          bubble.stats.habit_effective('Meditation') == 5)

    # point config also comes from a tail backup's settings block:
    # dividers, minutes-primary flags, inverted-binary habits
    tmp_bk = os.path.join(tempfile.gettempdir(),
                          'pc_widget_smoke_backup.json')
    with open(tmp_bk, 'w') as f:
        json.dump({'settings': {
            'habitDividers': {'Pushups': 30},
            'widgetTimerMinutesPrimary': ['Stretch2'],
            'invertedBinaryHabits': ['Coffee'],
            'noPointsHabits': ['Chess'],
        }}, f)
    stats_mod.BACKUP_GLOBS = tmp_bk
    tmp_db3 = os.path.join(tempfile.gettempdir(),
                           'pc_widget_smoke_habitsdb3.json')
    with open(tmp_db3, 'w') as f:
        json.dump({'Pushups': {date.today().isoformat(): 60},
                   'Stretch2': {date.today().isoformat(): 2},
                   'minutes:Stretch2': {date.today().isoformat(): 45},
                   'Coffee': {date.today().isoformat(): 0},
                   'Chess': {date.today().isoformat(): 7}}, f)
    s3 = Stats(tmp_db3)
    s3.refresh()
    check('backup habitDividers divide raw counts (60/30 → 2)',
          s3.habit_effective('Pushups') == 2)
    check('backup minutes-primary flags drive minutes scoring (45/30 → 2)',
          s3.habit_effective('Stretch2') == 2)
    check('inverted-binary habits score 1 when not done',
          s3.habit_effective('Coffee') == 1)
    check('noPointsHabits score nothing (Chess raw 7 → 0)',
          s3.habit_effective('Chess') == 0)
    check('day totals use the backup point config (2+2+1 → 5)',
          s3.summary_lines()[0] == 'today: 5 pts')

    # the same inputs from the bridge config override the (stale) backup
    s3.set_point_config([
        {'name': 'Pushups', 'divider': 20},             # backup said 30
        {'name': 'Coffee', 'inverted_binary': False},   # backup said inverted
        {'name': 'Chess', 'no_points': False},          # backup said noPoints
    ])
    s3.refresh()
    check('config divider beats the backup (60/20 → 3)',
          s3.habit_effective('Pushups') == 3)
    check('config un-inverts a backup habit (Coffee raw 0 → 0)',
          s3.habit_effective('Coffee') == 0)
    check('config re-points a noPoints habit (Chess raw 7 → 7)',
          s3.habit_effective('Chess') == 7)
    check('absent config fields keep the backup answer (Stretch2 45/30 → 2)',
          s3.habit_effective('Stretch2') == 2)
    stats_mod.BACKUP_GLOBS = os.path.join(tempfile.gettempdir(),
                                          'pc_widget_smoke_no_bk_*.json')

    check('center circle is a child above the squares',
          bubble.core.parent() is bubble
          and bubble.children().index(bubble.core)
          > max(bubble.children().index(s) for s in bubble.squares))
    check('core is transparent for mouse events',
          bubble.core.testAttribute(Qt.WA_TransparentForMouseEvents))
    check('tail icon fills the circle to its inner edge',
          bubble.core.tail_pm.width() == BUBBLE_D - 4
          and bubble.core.tail_pm.height() == BUBBLE_D - 4)

    bubble._near = False
    bubble._apply_layout_now()
    check('idle squares collapse fully behind the bubble',
          all(s._tuck_progress() > 0.99 for s in bubble.squares))
    check('tucked squares reach well behind the circle',
          TUCK_R + SQUARE_D // 2 - BUBBLE_D // 2 > SQUARE_D // 3)
    body = bubble.squares[0]._render_body()
    check('square body renders offscreen for the warp',
          body.width() == SQUARE_D and body.height() == SQUARE_D)

    bubble._near = True
    bubble._apply_layout_now()
    check('spread squares lose the pinch entirely',
          all(s._tuck_progress() == 0.0 for s in bubble.squares))
    bubble._near = False
    bubble._apply_layout_now()

    # bridge down → widget keeps state instead of clearing
    server.shutdown()
    time.sleep(0.2)
    check('bridge down: load_config → None (keep squares)',
          sync.load_config() is None and len(bubble.squares) == 3)
    check('bridge down: pending_events → None (keep badges)',
          sync.pending_events() is None)
    check('bridge down: append_event → None (flash shows failure)',
          sync.append_event('Reading', kind='tap') is None)

    bubble.close()
    app.quit()
    print()
    if failures:
        print('FAILED: {}'.format(', '.join(failures)))
        return 1
    print('ALL CHECKS PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
