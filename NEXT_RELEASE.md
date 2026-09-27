# Next Appi release

Planning status: committed / release candidate. Version: 0.7.15. Current baseline and fallback: [PROJECT_STATE.md](PROJECT_STATE.md).

Version 0.7.14 failed target-device acceptance for manual stream selection. HLS-4 is reopened and explicitly committed as the sole release-blocking scope for 0.7.15. The repair must restore the proven 0.7.12 InputStream Adaptive ask-quality playback path; 0.7.12 remains the usable fallback until accepted.

## Proposed scope

| Task | Selection | Priority | Reason |
| --- | --- | --- | --- |
| [HLS-4](docs/tasks/HLS-4.md) | committed | release blocker | 0.7.14 still fails manual selection; restore the 0.7.12 master-URL + InputStream Adaptive ask-quality path |
| [HLS-1](docs/tasks/HLS-1.md) | backlog | investigation | Diagnose repeated stalls using DIAG-2 evidence and distinguish configured cache size from actual playable read-ahead |
| [UI-1](docs/tasks/UI-1.md) | backlog | investigation | Skin comparison needed |

## How to plan the release

1. Send a plain list of desired changes, priorities, expected behavior and constraints. Include bug reproduction/version when available.
2. Triage updates/creates task records, then the index and this plan. Merge duplicate requests.
3. Select a small coherent set as committed; resolve important acceptance/dependency gaps before assigning work.
4. Start focused worker threads by task ID and authorized outcome. Implementation, review and release use their respective procedures.
5. Before release, check committed tasks and evidence. Record any authorized deferral/exception explicitly.
6. Copy shipped task IDs and scope changes into RELEASE_NOTES, then reset this planning file for the next cycle.

## Scope decisions

2026-09-26: user reported that 0.7.14 manual stream-selection playback is still broken exactly as in 0.7.13 and explicitly instructed that the bug fix be committed, executed and published. HLS-4 is reopened and committed as the sole 0.7.15 release-blocking task. The implementation direction is to restore the 0.7.12 playback architecture: retain the original HLS master URL and delegate manual rendition selection/playback to InputStream Adaptive `ask-quality`, rather than Appi resolving a child playlist.


2026-09-26: Appi 0.7.14 was published from merge commit `4eb272c0da19b716906e4909366f6d6ba4173874`. Shipped scope: HLS-4 and DIAG-2. Automated post-merge verification passed in run 36290741628. Both tasks remain in review because their documented target-device acceptance evidence is still pending; publication does not imply device acceptance.


2026-09-26: user explicitly corrected the release plan and confirmed that HLS-4 and DIAG-2 are changes for the next release. Both are now committed scope. The prior candidate-only state was a planning error that caused the release worker to find no committed work.

2026-09-26: HLS-4 added as a release-blocking regression after target-device testing showed that 0.7.13 manual HLS selection displays incorrect rendition information and every selected stream fails playback. The user reverted to 0.7.12. Repair should precede additional HLS feature work.

2026-09-26: DIAG-2 added as a candidate after target-device use of the released DIAG-1 package showed that stall detection alone does not capture enough evidence to identify the cause. The requested successor must preserve a full-session causal timeline across playback-mode changes.

2026-09-26: Appi 0.7.13 was published from merge commit `0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a`. Shipped scope: SEARCH-1, SUB-1, SEARCH-2, REFRESH-1, REFRESH-2, LANG-1, DIAG-1, HLS-3 and HLS-2. NEXT_RELEASE was reset for the next planning cycle; task records retain pending target-device verification where applicable.

2026-09-26: user explicitly committed all current candidate tasks (SEARCH-1, SUB-1, SEARCH-2, REFRESH-1, REFRESH-2, LANG-1, DIAG-1, HLS-3, HLS-2) and authorized the build, integration and publishing lifecycle for this release.

2026-09-24: existing requests migrated as candidates/backlog during lifecycle setup. No release scope or new version has been committed.

2026-09-24: DIAG-1 added as a candidate at user request. It is intended to enable efficient evidence collection for HLS-1; HLS-1 remains a separate investigation rather than being folded into the diagnostic feature.

2026-09-24: SEARCH-1 was expanded with the user's explicit cancel/favorites navigation failure paths. SEARCH-2 was added as a separate search-history candidate so navigation correctness can be established before layering on new search UX.

2026-09-24: HLS-2 added after source inspection confirmed "Automatic - Kodi default" does not explicitly request InputStream Adaptive, while the existing maximum-bitrate mode does request adaptive stream selection with a ceiling. HLS-2 will verify runtime switching and clarify/expose ABR behavior rather than duplicate the existing adaptive path.

2026-09-24: HLS-3 added for the manual quality chooser cancel regression. It is tracked separately from HLS-2 because cancel semantics must be correct regardless of future HLS mode design.

2026-09-24: HLS-2 was refined after the user reported that "Limit maximum bitrate" appears to select the highest rendition below the cap and remain there. The task must now prove whether runtime switching actually occurs before treating the existing path as ABR.

2026-09-26: SUB-1 added as a current-baseline regression candidate after the user reported that downloaded subtitles are forgotten after exiting and resuming/restarting the same media. Existing persistence code must be reproduced end-to-end before repair.

## Readiness

0.7.15 source implementation is prepared with HLS-4 as the sole committed release blocker. The candidate restores the 0.7.12 original-master-URL + InputStream Adaptive `ask-quality` path. Automated release/package verification and target-device acceptance remain pending; 0.7.12 remains the usable playback fallback.
