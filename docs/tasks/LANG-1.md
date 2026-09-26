---
id: LANG-1
role: implementation
status: active
delivery: unreleased
verification: pending
owner: ChatGPT build session 2026-09-26
base_commit: 8a9b1ad21b3944d8045e1d1abff2a2556c3035cc
artifact: none
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

## Outcome and next action
Specify matching and fallback behavior, then assign implementation.

