---
id: HLS-17
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-17 — Clarify startup target versus configured buffer capacity

## Objective
Make the Buffered Look Ahead startup UI clearly distinguish the amount required before playback starts from the user's configured total buffer capacity.

## Current behavior
On 0.7.21 target-device testing:
- 126 MB configured shows a 63 MB startup target;
- 128 MB configured shows a 64 MB startup target;
- 256 MB configured shows a 128 MB startup target.

This is intentional. The working 0.7.21 reservoir uses:
- 50% startup target;
- 80% high-water;
- 60% low-water;
- 15% critical reserve;
while `buffer_mb` remains the full session capacity.

The UI currently makes the startup target easy to misread as the configured buffer size.

## Scope
UI/telemetry wording only. Preserve HLS-13's working 0.7.21 reservoir algorithm exactly unless separately authorized.

During initial preparation, show:
- actual currently buffered playable bytes;
- startup target bytes;
- configured total capacity.

Example:
`Buffered 42.6 MB / 64 MB startup target — capacity 128 MB`

Equivalent concise wording is acceptable if all three concepts are unambiguous.

Where useful after playback begins, the detailed overlay may additionally expose the 80% high-water target, but HLS-16 owns the renderer itself.

## Acceptance
- 128 MB configured still produces the same 64 MB startup target and 102.4 MB high-water behavior as 0.7.21.
- 126 MB configured still produces the same 63 MB startup target.
- 256 MB configured still produces the same 128 MB startup target.
- Startup UI explicitly labels the displayed target as the startup target rather than total configured capacity.
- Configured capacity is visible in the startup text.
- Current buffered amount remains a truthful active-epoch contiguous playable reserve.
- No changes to reservoir ratios, refill algorithm, fetch scheduling, quality choice, epoch behavior or playback readiness logic.
- Automated regression test locks the 0.7.21 50/80/60/15 policy while testing only presentation semantics.

## Authorization
Raised by the user on 2026-09-28 after observing exact half-capacity startup targets across 126, 128 and 256 MB settings. Source review confirms this is UI ambiguity around the intentional 50% startup target, not the buffer setting being ignored. On 2026-09-28 the user explicitly instructed that all current candidates be committed for the next release. HLS-17 is committed next-release scope.

## Evidence
`BufferedHlsSession.__init__` sets `max_bytes = buffer_mb * MiB`, `startup_target_bytes = max_bytes * 0.50`, and `high_water_bytes = max_bytes * 0.80`. Startup waits for `startup_target_bytes` and reports that value as `buffer_target_bytes`.

## Outcome and next action
Clarify the UI only. Preserve the proven 0.7.21 reservoir algorithm unchanged.
