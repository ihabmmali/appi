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

Use [DIAG-1](DIAG-1.md) as the preferred reusable evidence-collection path once available. HLS-1 owns diagnosis and remedy selection; DIAG-1 owns the debug/export facility.

## Acceptance
- Capture sanitized manifest structure, segment timing and relevant Kodi/inputstream logs.
- Compare a failing and working stream under comparable conditions.
- Correlate stalls with available request timing, retries/errors, selected rendition, player/inputstream state and buffer evidence where observable.
- Recommend a measured remedy and verification criteria.

## Authorization
Migrated from the existing Appi tracker and user reports on 2026-09-24. The current request authorizes lifecycle/tracker setup. This migration does not start product implementation or publish an add-on release; a worker must record applicable task authorization from its assignment or prior explicit request.

## Evidence
Existing KNOWN_ISSUES entry preserved. DIAG-1 was linked on 2026-09-24 after the user requested an exportable debug mode specifically to collect evidence for this investigation. No new experiment, implementation or device verification has been performed in this documentation task.

## Outcome and next action
Collect a reproducible failing case and comparable working case, preferably using DIAG-1 once implemented; preserve the known-good playback behavior during diagnosis.
