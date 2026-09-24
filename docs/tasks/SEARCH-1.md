---
id: SEARCH-1
role: review
status: ready
delivery: released
verification: partial
owner: unassigned
base_commit: unset
artifact: https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.12.zip
---
# SEARCH-1 — Search navigation verification

## Objective
Version 0.7.12 claims to retain search sessions after prior regressions. Device acceptance is not recorded.

Existing report: enter a show from search, go back, add/remove favorites, and cancel search; previous behavior reopened the dialog or exited the add-on.

## Scope
Triage/research/verification for the stated area; confirm current source before edits. Candidate source areas are described in [ARCHITECTURE.md](../../ARCHITECTURE.md). Product edits and publishing follow the assigned session's scope. Record actual base SHA and paths on assignment.

## Acceptance
- Test movie, TV and mixed search with matches/no matches.
- Show/back and favorite/unfavorite preserve results.
- Cancellation returns to the originating directory; record the exact intended navigation if device behavior is ambiguous.
- Record Kodi version, skin, platform and outcomes.

## Authorization
Migrated from the existing Appi tracker and user reports on 2026-09-24. The current request authorizes lifecycle/tracker setup. This migration does not start product implementation or publish an add-on release; a worker must record applicable task authorization from its assignment or prior explicit request.

## Evidence
Source manifest, README and package index previously inspected at 0.7.12; no target-device acceptance recorded. The existing shipped candidate is linked above; this verification task remains open.

## Outcome and next action
Verify the installed 0.7.12 behavior first. Reopen implementation if a failure is reproduced.

