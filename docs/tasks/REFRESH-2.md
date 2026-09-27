---
id: REFRESH-2
role: review
status: review
delivery: released
verification: partial
owner: ChatGPT build session 2026-09-26
base_commit: 8a9b1ad21b3944d8045e1d1abff2a2556c3035cc
artifact: https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.13.zip
---
# REFRESH-2 — Optional automatic catalogue refresh

## Objective
Add optional scheduled/startup refresh with user controls.

Scheduling and failure behavior need definition; coordinate with REFRESH-1 if using fast refresh.

## Scope
Triage/research/verification for the stated area; confirm current source before edits. Candidate source areas are described in [ARCHITECTURE.md](../../ARCHITECTURE.md). Product edits and publishing follow the assigned session's scope. Record actual base SHA and paths on assignment.

## Acceptance
- Define interval, startup trigger, fast/full selection and disabled behavior.
- Define playback interaction, retry/backoff and avoidance of overlapping refreshes.
- Preserve cache on network failure.

## Authorization
Migrated from the existing Appi tracker and user reports on 2026-09-24. The current request authorizes lifecycle/tracker setup. This migration does not start product implementation or publish an add-on release; a worker must record applicable task authorization from its assignment or prior explicit request.

## Evidence
Existing KNOWN_ISSUES entry preserved. No new experiment, implementation or device verification has been performed in this documentation task.

## Build session — 2026-09-26
- User authorization: all candidates committed to the next release; implementation, integration and publication explicitly authorized.
- Release branch: `release/0.7.13`; base: `8a9b1ad21b3944d8045e1d1abff2a2556c3035cc`.
- Planned paths: plugin.video.appi/resources/lib/subtitle_service.py; app.py; settings/tests.
- This worker owns the committed release sequence; review will be recorded as self-review unless independent evidence is added.

## Review evidence — 2026-09-26
- Added optional startup/scheduled refresh in the background service, gated on idle video playback.
- A shared profile lock serializes manual and automatic refreshes; failure state drives bounded retry backoff and a successful refresh resets failures.
- Direct lock/state regression coverage was added for the final candidate; refresh functions retain prior cache on failures.
- Verification is partial pending long-running target-device scheduling, playback-interaction and restart observations.

## Outcome and next action
Set actionable requirements and dependency on REFRESH-1.


## Publication — 0.7.13
- Published to `main` in merge commit `0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a` on 2026-09-26/27.
- Post-merge release verification: GitHub Actions run 36287058096 passed the full automated gate.
- Artifact: `plugin.video.appi-0.7.13.zip`; 0.7.8 remains the known-good fallback.
- Delivery is released; verification remains partial until the task's documented target-device checks are completed.
