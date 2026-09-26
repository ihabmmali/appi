---
id: REFRESH-1
role: review
status: review
delivery: unreleased
verification: partial
owner: ChatGPT build session 2026-09-26
base_commit: 8a9b1ad21b3944d8045e1d1abff2a2556c3035cc
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

## Build session — 2026-09-26
- User authorization: all candidates committed to the next release; implementation, integration and publication explicitly authorized.
- Release branch: `release/0.7.13`; base: `8a9b1ad21b3944d8045e1d1abff2a2556c3035cc`.
- Planned paths: plugin.video.appi/resources/lib/app.py; refresh helpers/settings/tests.
- This worker owns the committed release sequence; review will be recorded as self-review unless independent evidence is added.

## Review evidence — 2026-09-26
- Added a cached provider-order episode feed plus a leading-window fast-refresh path that requires a contiguous overlap before merging new head entries with the cached tail.
- No reliable overlap, repeated-page ambiguity or missing provider-order cache falls back to the existing full refresh; fetch/parse exceptions leave the prior cache intact.
- Automated coverage includes unchanged feed, prepended entries and no-overlap fallback logic; final candidate adds direct overlap regression tests.
- Provider assumptions and real page-boundary behavior remain pending on the configured production feed, so verification is partial.

## Outcome and next action
Specify the algorithm and test cases; use synthetic feeds before implementing.

