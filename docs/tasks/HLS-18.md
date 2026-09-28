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
# HLS-18 — Make Buffered Look Ahead startup fill percentage configurable

## Objective
Expose the startup reservoir threshold as a user-configurable percentage while preserving the working Appi 0.7.21 buffering algorithm.

The default must remain exactly **50%** so existing 0.7.21 behavior is unchanged unless the user deliberately chooses another startup fill level.

## Current behavior
0.7.21 uses:
- configured buffer capacity = 100% of `buffered_buffer_mb`;
- startup target = 50%;
- high-water = 80%;
- low-water = 60%;
- critical reserve = 15%.

Target-device evidence confirms this policy is working well. The new setting must therefore affect only the startup target calculation.

## Scope
Add a Buffered Look Ahead setting such as **Startup buffer fill %**.

Requirements:
- default value: **50%**;
- the setting replaces the hard-coded startup ratio only when calculating `startup_target_bytes`;
- `max_bytes`, high-water, low-water, critical-water, shared-capacity allocation, refill scheduling, transfer behavior, epoch logic and quality behavior remain unchanged;
- startup target must not exceed the steady-state high-water threshold unless the high-water policy is explicitly redesigned in a separately authorized task;
- invalid/out-of-range stored values fall back safely to 50%;
- HLS-17 startup text should show the chosen startup percentage/target unambiguously.

The exact selectable range may be chosen conservatively during implementation, but it must be bounded so users cannot configure a startup target inconsistent with the unchanged 80% high-water policy.

## Examples with the current 128 MB capacity
- 25% startup -> 32 MB before playback;
- 50% startup -> 64 MB before playback (0.7.21 default/current behavior);
- 75% startup -> 96 MB before playback.

After playback begins, the unchanged 0.7.21 reservoir continues toward its 80% high-water target (~102.4 MB for a 128 MB capacity).

## Acceptance
- A clean install/default configuration behaves identically to 0.7.21: 50% startup fill.
- Existing users with no stored startup-fill setting also get 50%.
- Changing the startup-fill setting changes only `startup_target_bytes`.
- 128 MB + 50% still starts at 64 MB.
- 256 MB + 50% still starts at 128 MB.
- A non-default percentage produces the expected startup target from the configured capacity.
- High-water remains 80%, low-water 60%, critical 15%.
- Continuous refill behavior after playback starts is unchanged.
- Shared video/audio capacity allocation is unchanged.
- Seek/resume epoch behavior is unchanged except that the documented startup-threshold rule is applied where explicitly appropriate.
- Native Kodi and InputStream Adaptive modes remain unchanged.
- Automated regression coverage proves default 50% behavior is byte-for-byte/equivalent to 0.7.21 policy calculations and that changing the setting does not alter other reservoir thresholds.
- Target-device verification confirms both default 50% and at least one non-default startup-fill value.

## Authorization
Requested by the user on 2026-09-28 after confirming that 0.7.21's 50% startup target is intentional and that the buffering algorithm is the first version that has worked reliably for them. This is a ready candidate and is not committed until explicitly included under AGENTS.md.

## Evidence
0.7.21 source hard-codes `STARTUP_WATER_RATIO = 0.50` while calculating high/low/critical water independently as 0.80/0.60/0.15. Target-device observations 126->63 MB, 128->64 MB and 256->128 MB match that 50% startup calculation exactly.

## Outcome and next action
Add a bounded startup-fill percentage setting with a 50% default, wiring it only into startup target calculation and preserving all other 0.7.21 reservoir behavior.
