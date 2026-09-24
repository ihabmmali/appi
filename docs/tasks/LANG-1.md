---
id: LANG-1
role: triage
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
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

## Outcome and next action
Specify matching and fallback behavior, then assign implementation.

