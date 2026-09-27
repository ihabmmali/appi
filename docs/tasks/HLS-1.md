---
id: HLS-1
role: research
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-1 — Investigate repeated HLS stalls

## Objective
Some specific approximately 6 Mbps streams stall despite larger buffers while higher bitrate streams work.

Fixed resolution/bitrate selection does not itself establish the cause. Playback should be diagnosed with evidence.

## Scope
Triage/research/verification for the stated area; confirm current source before edits. Candidate source areas are described in [ARCHITECTURE.md](../../ARCHITECTURE.md). Product edits and publishing follow the assigned session's scope. Record actual base SHA and paths on assignment.

Use [DIAG-2](DIAG-2.md) as the preferred causal evidence-collection path once available. DIAG-1 provides the released base export facility; DIAG-2 owns the deeper segment/network/buffer/representation timeline. HLS-1 owns diagnosis and remedy selection. Coordinate with [HLS-2](HLS-2.md) because apparent fixed ceiling selection versus actual runtime ABR may materially change stall behavior.

## Acceptance
- Capture sanitized manifest structure, segment timing and relevant Kodi/inputstream logs.
- Compare a failing and working stream under comparable conditions.
- Correlate stalls with request timing, playlist/segment activity, retries/errors, selected rendition, player/inputstream state and buffer/read-ahead evidence where observable.
- Determine whether playable buffer was progressively draining before the stall and distinguish actual buffered duration/depth from configured cache capacity.
- Record whether playback is Kodi-native, manually fixed, ceiling-limited fixed/initial selection, or true ABR.
- If true ABR occurs, record whether any rendition switch coincides with the stall.
- Use the evidence to distinguish server/CDN delay, sustained insufficient throughput, Kodi cache/read-ahead behavior, ABR behavior and Appi playback-engine behavior, or explicitly conclude that evidence is insufficient.
- Recommend a measured remedy and verification criteria.

## Authorization
Migrated from the existing Appi tracker and user reports on 2026-09-24. The current request authorizes lifecycle/tracker setup. This migration does not start product implementation or publish an add-on release; a worker must record applicable task authorization from its assignment or prior explicit request.

## Evidence
Existing KNOWN_ISSUES entry preserved. DIAG-1 established the first bounded diagnostic export in 0.7.13. On 2026-09-26 the user reported that the package detects stalls but lacks the segment/network/representation/buffer history needed to determine their cause; DIAG-2 now tracks that observability expansion. HLS-2 remains relevant because the maximum-bitrate mode may not be true runtime ABR.

## Outcome and next action
Collect a reproducible failing case and comparable working case using DIAG-2 once available; preserve the known-good playback behavior during diagnosis and base any remedy on the correlated segment/network/buffer timeline rather than configured cache size alone.
