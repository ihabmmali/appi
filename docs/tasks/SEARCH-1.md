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
# SEARCH-1 — Search navigation regression investigation

## Objective
Version 0.7.12 claims to retain search sessions after prior regressions, but target-device acceptance is not recorded and previously reported navigation failures remain important to reproduce explicitly.

Known reported failure paths include:
- Cancelling out of search can return to Kodi's add-on level outside Appi instead of Appi's main menu or the logical originating Appi directory.
- Adding a search result to favorites can reopen the search category-selection dialog instead of returning to the existing search results.
- Back/cancel/favorite operations have historically produced inconsistent transitions between keyword entry, category selection, results and media detail/show views.

The task is to investigate search navigation as a state-flow problem, reproduce each path, identify the failing route/session behavior, and route confirmed failures to repair without redefining intended navigation around the bug.

## Scope
Review/reproduce the current search navigation behavior first, then record the exact source/state transition implicated by any failure. Candidate source areas are described in [ARCHITECTURE.md](../../ARCHITECTURE.md).

This task owns search-session and navigation correctness. [SEARCH-2](SEARCH-2.md) owns reusable search history and must not be used to mask or work around navigation defects.

Product edits, integration and publishing remain separate assigned work under the lifecycle. A confirmed regression should transition this task to implementation with the actual base SHA/owner recorded rather than creating a duplicate bug task.

## Acceptance
- Test movie, TV and mixed search with matches and no matches.
- Map the expected transition sequence among Appi main menu, keyword entry, category/filter selection, results, show/media detail and return paths.
- Cancelling from search entry/category selection returns to the correct originating Appi directory and never unexpectedly exits to Kodi's add-on browser.
- Entering a result and navigating back restores the same search-results context rather than restarting search unless the user intentionally exits results.
- Adding/removing a result from favorites returns to the same search-results context and does not reopen the category-selection dialog.
- Repeated enter/back/favorite/cancel cycles do not lose the active search session or produce progressively different navigation.
- Distinguish Kodi directory refresh/reload behavior from Appi session-state bugs and record the exact failing route/state transition for every reproduced defect.
- If a defect is reproduced, define the repair and regression checks needed before the task can pass.
- Record Kodi version, skin, platform, installed Appi version and outcomes.

## Authorization
Migrated from the existing Appi tracker and user reports on 2026-09-24. On 2026-09-24 the user explicitly reiterated the cancel-to-add-on-level and favorite-to-category-dialog failures and requested a proper investigation with repairs applied where necessary.

This triage thread is authorized to maintain the canonical records and release plan. Implementation, integration and publication remain separate assignments under the thread scope.

## Evidence
Source manifest, README and package index were previously inspected at 0.7.12; no target-device acceptance is recorded. The user has reiterated two concrete historical failure paths: cancelling search can leave Appi, and favoriting a search result can return to category selection rather than results.

No new device reproduction has been performed in this triage update.

## Outcome and next action
Treat SEARCH-1 as the canonical navigation-regression task. A review worker should reproduce the explicit flows above on the current baseline. Any confirmed failure should move this same task into implementation with targeted regression tests; do not close it based only on the existence of the 0.7.12 session-retention code.
