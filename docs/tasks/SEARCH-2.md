---
id: SEARCH-2
role: review
status: review
delivery: released
verification: partial
owner: ChatGPT build session 2026-09-26
base_commit: 8a9b1ad21b3944d8045e1d1abff2a2556c3035cc
artifact: https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.13.zip
---
# SEARCH-2 — User-manageable search history

## Objective
Add a persistent, user-manageable history of prior search keywords so common searches can be selected, optionally edited, and run again without retyping the full term.

The history should accelerate repeat searches without changing the intended navigation rules owned by [SEARCH-1](SEARCH-1.md).

## Scope
Define and implement keyword-history behavior for Appi search. The history should use Appi-owned profile storage and remain lightweight and bounded.

The initial requirement is keyword history, not a replacement for search category/filter selection. Reusing a history entry should feed the selected/edited keyword into the normal search flow so the user can continue with the applicable search scope/filter.

User-management operations should include selecting/reusing an entry, editing it before running the search, deleting an individual entry, and clearing the history. Exact UI placement should be chosen during implementation to minimize extra dialogs and remote-control steps.

## Acceptance
- Successful non-empty search terms are retained across Kodi/Appi restarts.
- Opening search presents a usable recent-keyword history without making a new search slower or materially more cumbersome.
- Selecting a history entry can reuse it directly through the normal search flow.
- The user can edit a selected historical keyword before executing the search.
- The user can delete one history entry and clear all search history.
- Repeating an existing keyword does not create uncontrolled duplicates; the history remains bounded and recent-use ordering is deterministic.
- Cancelled/empty keyword entry does not create a meaningless history item.
- Clearing search history does not affect favorites, Recently Played, catalogue caches, metadata, watched/resume state or other user data.
- Search-history actions preserve the navigation guarantees and active-results behavior defined by SEARCH-1.
- Storage format and migration/failure behavior are defined so corrupt history cannot break the search feature.

## Authorization
Requested by the user on 2026-09-24 as a proposed Appi feature. This authorizes triage/planning records only in this thread; implementation, integration and publication remain separate assignments.

## Evidence
User requirement: provide a manageable list of prior keywords that can be quickly selected, edited and used for another search.

No implementation or device verification has been performed.

## Build session — 2026-09-26
- User authorization: all candidates committed to the next release; implementation, integration and publication explicitly authorized.
- Release branch: `release/0.7.13`; base: `8a9b1ad21b3944d8045e1d1abff2a2556c3035cc`.
- Planned paths: plugin.video.appi/resources/lib/search_history.py; app.py; settings/tests.
- This worker owns the committed release sequence; review will be recorded as self-review unless independent evidence is added.

## Review evidence — 2026-09-26
- Added a separate persistent search-history store bounded to 20 normalized entries with case-insensitive deduplication, reuse, edit-before-search, single-entry delete and clear-all actions.
- Corrupt/malformed history falls back to an empty list without affecting catalogue/search-session caches.
- Search-history persistence/bounds/corruption regression coverage was added for the final candidate, in addition to the existing navigation smoke coverage.
- Verification remains partial until the history UI and keyboard/back behavior are exercised on the target device.

## Outcome and next action
Keep SEARCH-2 separate from SEARCH-1 so history UX can be implemented without obscuring navigation defects. Before implementation, choose the smallest remote-friendly UI flow and bounded persistence policy consistent with the acceptance criteria.

## Publication — 0.7.13
- Published to `main` in merge commit `0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a` on 2026-09-26/27.
- Post-merge release verification: GitHub Actions run 36287058096 passed the full automated gate.
- Artifact: `plugin.video.appi-0.7.13.zip`; 0.7.8 remains the known-good fallback.
- Delivery is released; verification remains partial until the task's documented target-device checks are completed.
