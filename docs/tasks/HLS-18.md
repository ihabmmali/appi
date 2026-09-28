---
id: HLS-18
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-18 — Make Buffered Look Ahead algorithm thresholds configurable

## Objective
Expose Buffered Look Ahead's behavior-affecting tuning thresholds as user-configurable settings while preserving the working Appi 0.7.21 values as defaults.

The installed/default configuration must remain behaviorally equivalent to 0.7.21. Users may deliberately tune the thresholds, but no default may change merely because the constants move from Python into settings.

## Current behavior
0.7.21 uses hard-coded tuning values inside `buffered_hls.py`, including:
- configured buffer capacity = 100% of `buffered_buffer_mb`;
- startup target = 50%;
- high-water = 80%;
- low-water = 60%;
- critical reserve = 15%;
- media inactivity/no-progress timeout = 15 seconds;
- startup preparation timeout = 180 seconds;
- seek reserve target = about 12 seconds with a 4 MiB floor;
- track prefetch lead balancing = 24 seconds;
- other recovery/control timing thresholds where they still affect Buffered Look Ahead behavior.

Target-device evidence says the 0.7.21 algorithm works well. Those current values therefore become the defaults, not values to redesign.

## Scope
Add a clearly grouped **Advanced Buffered Look Ahead tuning** settings section.

At minimum expose:
- **Startup fill %** — default 50;
- **High-water %** — default 80;
- **Low-water %** — default 60;
- **Critical reserve %** — default 15;
- **Media inactivity timeout (s)** — default 15;
- **Startup preparation timeout (s)** — default 180;
- **Seek reserve (s)** — default 12;
- **Minimum seek reserve (MB)** — default 4;
- **Track prefetch lead (s)** — default 24;
- any other existing behavior-affecting Buffered Look Ahead threshold discovered during implementation audit.

Do not expose protocol identifiers, data-structure constants or true non-tunable safety invariants merely for the sake of having a setting. The rule applies to parameters that tune algorithm behavior.

Validation requirements:
- defaults must reproduce 0.7.21 exactly;
- `critical < low < high <= 100`;
- startup fill must be positive and must not exceed high-water unless a future explicitly authorized design changes that relationship;
- invalid/migrated values fall back to the proven 0.7.21 defaults rather than producing an unusable reservoir;
- settings should live under Buffered Look Ahead and may be marked Advanced/Expert to avoid clutter for ordinary users;
- HLS-17 must display the effective startup target/capacity clearly.

Changing a setting may intentionally change the corresponding threshold only. For example, changing high-water must not silently alter low-water, startup fill, quality behavior, epoch semantics or fetch strategy.

## Examples with the current 128 MB capacity
- 25% startup -> 32 MB before playback;
- 50% startup -> 64 MB before playback (0.7.21 default/current behavior);
- 75% startup -> 96 MB before playback.

With default settings, playback then continues toward the unchanged 0.7.21 80% high-water target (~102.4 MB for a 128 MB capacity). If the user deliberately changes the high-water setting, only that threshold changes subject to validation.

## Acceptance
- A clean install/default configuration is behaviorally equivalent to 0.7.21.
- Existing users with no stored tuning values get the 0.7.21 defaults.
- Defaults remain startup/high/low/critical = 50/80/60/15%.
- Default media inactivity timeout remains 15 seconds.
- Default startup preparation timeout remains 180 seconds.
- Default seek reserve remains 12 seconds with a 4 MiB floor.
- Default track prefetch lead remains 24 seconds.
- 128 MB + default 50% still starts at 64 MB.
- 256 MB + default 50% still starts at 128 MB.
- Changing one setting changes only that algorithm parameter unless a documented dependency requires validation.
- Invalid threshold order or impossible combinations are rejected or safely normalized with clear behavior.
- Shared video/audio capacity allocation, epoch ownership, selected-quality behavior and fetch architecture remain the proven 0.7.21 design unless separately authorized.
- Native Kodi and InputStream Adaptive modes remain unchanged.
- Automated regression coverage compares the default settings-backed calculations against the 0.7.21 constants.
- Automated tests cover non-default startup/high/low/critical watermarks, timing thresholds, invalid combinations and migration/default fallback.
- Target-device verification confirms default 0.7.21 behavior plus at least one deliberately modified startup threshold and one deliberately modified during-playback watermark.

## Authorization
Requested by the user on 2026-09-28 after confirming that 0.7.21's buffering algorithm is the first version that has worked reliably for them. The user then broadened the request: all thresholds, including during-playback thresholds, should be configurable while defaulting to the current 0.7.21 values. This remains a ready candidate and is not committed until explicitly included under AGENTS.md.

## Evidence
0.7.21 source hard-codes `STARTUP_WATER_RATIO = 0.50`, `HIGH_WATER_RATIO = 0.80`, `LOW_WATER_RATIO = 0.60`, `CRITICAL_WATER_RATIO = 0.15`, `REQUEST_TIMEOUT = 15`, `STARTUP_TIMEOUT = 180`, `SEEK_RESERVE_SECONDS = 12`, `MIN_SEEK_RESERVE_BYTES = 4 MiB`, and `PREFETCH_LEAD_SECONDS = 24`. Target-device observations 126->63 MB, 128->64 MB and 256->128 MB match the default 50% startup calculation exactly.

## Outcome and next action
Move all behavior-affecting Buffered Look Ahead tuning thresholds into validated settings, preserving the 0.7.21 constants as defaults and keeping the proven algorithmic structure intact.
