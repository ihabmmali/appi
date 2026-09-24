---
id: SEARCH-2
role: triage
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
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

## Outcome and next action
Keep SEARCH-2 separate from SEARCH-1 so history UX can be implemented without obscuring navigation defects. Before implementation, choose the smallest remote-friendly UI flow and bounded persistence policy consistent with the acceptance criteria.
