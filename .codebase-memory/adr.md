# ADR: PC-widget point config now flows through the bridge config channel

**Date:** 2026-08-19
**Status:** Accepted (deployed)

## Context
The PC bubble widget computes square colours from *effective points* (raw ÷ divider, plus inverted-binary / noPoints subtypes). Until now the PC could only learn dividers/flags by mining the newest parseable phone backup (`~/habitsdb/Auto_backups/`, daily, frequently mid-sync) or the manual `~/.config/pc_bubble_widget/point_overrides.json`. The bridge config channel (`pc_widget/config`, pushed by the phone on settings changes and app startup, polled by the widget every 20 s) only carried `name`/`icon`/`minutes_primary` — and the bridge's POST sanitizer stripped everything else, including `divider`.

## Decision
1. Phone (`HabitViewModel.pushPcWidgetConfig`) now sends `divider` (habitDividers, default 1), `inverted_binary`, and `no_points` per habit.
2. Bridge (`tail_bridge/bridge_server.py pc_widget_set_config`) passes them through its sanitizer: `divider` validated as int ≥ 1 else null; booleans passed as bool else null. **null = "phone hasn't sent the field yet"**, not false.
3. Widget (`pc_widget_sync.load_config`) forwards the three fields (None when absent/null).
4. Stats (`pc_widget_stats.HabitStats`): `set_point_config` stores per-habit flags; `_effective_on` resolves each input with precedence **bridge config field (when non-null) > point_overrides.json (dividers/minutes only) > newest parseable backup > default (30 for minutes-primary, else 1)**. A config `false` deliberately overrides a stale backup `true`.

## Consequences
- Divider tweaks reach the widget in seconds instead of up to a day; backup mining and overrides remain as fallback layers, so the widget keeps working with an old phone build or a down bridge.
- Rollout is order-independent: any hop still on old code yields null/absent fields and the previous behaviour is preserved.
- Smoke test (`pc_widget_smoke_test.py`) covers pass-through validation and config-beats-backup precedence for all three fields.