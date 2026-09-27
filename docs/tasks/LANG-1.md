---
id: LANG-1
role: review
status: review
delivery: released
verification: partial
owner: ChatGPT build session 2026-09-26
base_commit: 8a9b1ad21b3944d8045e1d1abff2a2556c3035cc
artifact: https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.13.zip
---
# LANG-1 — Default audio and subtitle languages

## Objective
Select preferred languages using normalized stream codes/labels, including eng, en and English.

Audio and subtitle preferences are separate; saved external subtitle behavior already exists.

## Scope
Triage/research/verification for the stated area; confirm current source before edits. Candidate source areas are described in [ARCHITECTURE.md](../../ARCHITECTURE.md). Product edits and publishing follow the assigned session's scope. Record actual base SHA and paths on assignment.

## Acceptance
- Define alias handling, priority and behavior for missing/ambiguous labels.
- Verify manual overrides remain usable.
- Verify sample HLS/Kodi tracks and external subtitle interaction.

## Authorization
Migrated from the existing Appi tracker and user reports on 2026-09-24. The current request authorizes lifecycle/tracker setup. This migration does not start product implementation or publish an add-on release; a worker must record applicable task authorization from its assignment or prior explicit request.

## Evidence
Existing KNOWN_ISSUES entry preserved. No new experiment, implementation or device verification has been performed in this documentation task.

## Build session — 2026-09-26
- User authorization: all candidates committed to the next release; implementation, integration and publication explicitly authorized.
- Release branch: `release/0.7.13`; base: `8a9b1ad21b3944d8045e1d1abff2a2556c3035cc`.
- Planned paths: plugin.video.appi/resources/lib/languages.py; subtitle_service.py; settings/tests.
- This worker owns the committed release sequence; review will be recorded as self-review unless independent evidence is added.

## Review evidence — 2026-09-26
- Added normalized preferred audio and internal-subtitle selection at AV start, using Kodi language conversion when available and fallback aliases such as English/eng/en.
- Per-title subtitle modes remain authoritative: global internal-language selection is skipped for saved/off/search overrides, and saved external subtitles can still be attached afterward.
- Unit/service smoke coverage verifies alias matching plus matching stream indexes.
- Verification is partial pending provider-specific audio/subtitle labels and manual override behavior on the target Kodi device.

## Outcome and next action
Specify matching and fallback behavior, then assign implementation.


## Publication — 0.7.13
- Published to `main` in merge commit `0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a` on 2026-09-26/27.
- Post-merge release verification: GitHub Actions run 36287058096 passed the full automated gate.
- Artifact: `plugin.video.appi-0.7.13.zip`; 0.7.8 remains the known-good fallback.
- Delivery is released; verification remains partial until the task's documented target-device checks are completed.
