---
id: REFRESH-1
role: research
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# REFRESH-1 — Fast leading-window catalogue refresh

## Objective
Compare a configurable leading window against cached records to avoid downloading every numbered TV page.

Provider is reported to prepend new entries, pushing old entries to later pages, about 2,000 records per page. Current code performs full TV refresh.

## Scope
Triage/research/verification for the stated area; confirm current source before edits. Candidate source areas are described in [ARCHITECTURE.md](../../ARCHITECTURE.md). Product edits and publishing follow the assigned session's scope. Record actual base SHA and paths on assignment.

## Acceptance
- Measure unchanged-feed requests, prepend cases spanning page boundaries and duplicate handling.
- Preserve provider order and valid caches on cancellation/failure.
- Define overlap/no-overlap behavior and full refresh fallback.
- Explicitly document that a leading window cannot detect every deep deletion/edit.

## Authorization
Migrated from the existing Appi tracker and user reports on 2026-09-24. The current request authorizes lifecycle/tracker setup. This migration does not start product implementation or publish an add-on release; a worker must record applicable task authorization from its assignment or prior explicit request.

## Evidence
Existing KNOWN_ISSUES entry preserved. No new experiment, implementation or device verification has been performed in this documentation task.

## Outcome and next action
Specify the algorithm and test cases; use synthetic feeds before implementing.

