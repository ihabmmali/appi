# Next Appi release

Planning status: draft. Version: not assigned. Current baseline and fallback: [PROJECT_STATE.md](PROJECT_STATE.md).

This is a proposed selection from the backlog. No product task is newly authorized for implementation or publication by this planning file.

## Proposed scope

| Task | Selection | Priority | Reason |
| --- | --- | --- | --- |
| [SEARCH-1](docs/tasks/SEARCH-1.md) | candidate | recommended first | Verify existing 0.7.12 navigation before building on it |
| [REFRESH-1](docs/tasks/REFRESH-1.md) | candidate | requested feature | Fast refresh algorithm needs evidence and acceptance checks |
| [REFRESH-2](docs/tasks/REFRESH-2.md) | candidate | requested feature | Scheduling requirements; coordinate with refresh design |
| [LANG-1](docs/tasks/LANG-1.md) | candidate | requested feature | Define matching and fallback before implementation |
| [HLS-1](docs/tasks/HLS-1.md) | backlog | investigation | Reproducible stream diagnosis needed |
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

2026-09-24: existing requests migrated as candidates/backlog during lifecycle setup. No release scope or new version has been committed.

## Readiness

No release is declared ready by this file. Task evidence, source checks, required device results and the [release procedure](docs/workflows/release.md) determine readiness. Keep the known-good fallback available.

