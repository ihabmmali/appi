---
id: REFRESH-2
role: triage
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
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

## Outcome and next action
Set actionable requirements and dependency on REFRESH-1.

