# Next Appi release

Planning status: committed / release candidate. Version: 0.7.13. Current baseline and fallback: [PROJECT_STATE.md](PROJECT_STATE.md).

This is the user-authorized committed scope for the next release. Implementation, integration and publication were explicitly authorized on 2026-09-26.

## Proposed scope

| Task | Selection | Priority | Reason |
| --- | --- | --- | --- |
| [SEARCH-1](docs/tasks/SEARCH-1.md) | committed | recommended first | Reproduce and repair search cancel/back/favorites navigation before extending search UX |
| [SUB-1](docs/tasks/SUB-1.md) | committed | regression | Downloaded subtitles should persist and restore across stop/resume/restart |
| [SEARCH-2](docs/tasks/SEARCH-2.md) | committed | requested feature | Add persistent, editable and user-manageable keyword history after navigation behavior is stable |
| [REFRESH-1](docs/tasks/REFRESH-1.md) | committed | requested feature | Fast refresh algorithm needs evidence and acceptance checks |
| [REFRESH-2](docs/tasks/REFRESH-2.md) | committed | requested feature | Scheduling requirements; coordinate with refresh design |
| [LANG-1](docs/tasks/LANG-1.md) | committed | requested feature | Define matching and fallback before implementation |
| [DIAG-1](docs/tasks/DIAG-1.md) | committed | requested diagnostic feature | Create a privacy-safe evidence bundle for playback/buffering diagnosis |
| [HLS-3](docs/tasks/HLS-3.md) | committed | requested bug fix | Cancelling manual HLS quality selection must abort playback and restore the prior Appi view |
| [HLS-2](docs/tasks/HLS-2.md) | committed | requested playback feature | Verify whether the current cap is only ceiling-based rendition selection, then expose true ABR distinctly if supported |
| [HLS-1](docs/tasks/HLS-1.md) | backlog | investigation | Diagnose repeated stalls while distinguishing fixed/ceiling-limited playback from actual ABR |
| [UI-1](docs/tasks/UI-1.md) | backlog | investigation | Skin comparison needed |

Selection values: candidate / committed / deferred / backlog. Task status remains canonical in the linked record. The user or an authorized planner chooses committed scope; record the decision/date here. Prioritization above is a recommendation.

## How to plan the release

1. Send a plain list of desired changes, priorities, expected behavior and constraints. Include bug reproduction/version when available.
2. Triage updates/creates task records, then the index and this plan. Merge duplicate requests.
3. Select a small coherent set as committed; resolve important acceptance/dependency gaps before assigning work.
4. Start focused worker threads by task ID and authorized outcome. Implementation, review and release use their respective procedures.
5. Before release, check committed tasks and evidence. Record any authorized deferral/exception explicitly.
6. Copy shipped task IDs and scope changes into RELEASE_NOTES, then reset this planning file for the next cycle.

## Scope decisions

2026-09-26: user explicitly committed all current candidate tasks (SEARCH-1, SUB-1, SEARCH-2, REFRESH-1, REFRESH-2, LANG-1, DIAG-1, HLS-3, HLS-2) and authorized the build, integration and publishing lifecycle for this release.


2026-09-24: existing requests migrated as candidates/backlog during lifecycle setup. No release scope or new version has been committed.

2026-09-24: DIAG-1 added as a candidate at user request. It is intended to enable efficient evidence collection for HLS-1; HLS-1 remains a separate investigation rather than being folded into the diagnostic feature.

2026-09-24: SEARCH-1 was expanded with the user's explicit cancel/favorites navigation failure paths. SEARCH-2 was added as a separate search-history candidate so navigation correctness can be established before layering on new search UX.

2026-09-24: HLS-2 added after source inspection confirmed "Automatic - Kodi default" does not explicitly request InputStream Adaptive, while the existing maximum-bitrate mode does request adaptive stream selection with a ceiling. HLS-2 will verify runtime switching and clarify/expose ABR behavior rather than duplicate the existing adaptive path.

2026-09-24: HLS-3 added for the manual quality chooser cancel regression. It is tracked separately from HLS-2 because cancel semantics must be correct regardless of future HLS mode design.

2026-09-24: HLS-2 was refined after the user reported that "Limit maximum bitrate" appears to select the highest rendition below the cap and remain there. The task must now prove whether runtime switching actually occurs before treating the existing path as ABR.

2026-09-26: SUB-1 added as a current-baseline regression candidate after the user reported that downloaded subtitles are forgotten after exiting and resuming/restarting the same media. Existing persistence code must be reproduced end-to-end before repair.

## Readiness

Automated implementation verification passed in GitHub Actions run 36277010649 before release preparation. A final release-candidate run is still required after version/documentation changes. Target-device checks remain pending and must stay identified as such rather than being treated as automated acceptance. Keep 0.7.8 available as the known-good fallback.
