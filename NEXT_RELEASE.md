# Next Appi release

Planning status: draft. Version: not assigned. Current baseline and fallback: [PROJECT_STATE.md](PROJECT_STATE.md).

Version 0.7.16 was published on 2026-09-27. No new release scope is committed. HLS-5 is delivered in 0.7.16 but remains in review/partial verification pending target-device evidence on the buffered playback path. 0.7.12 remains the usable manual-playback fallback until the newer playback line is accepted on the target device.

## Proposed scope

| Task | Selection | Priority | Reason |
| --- | --- | --- | --- |
| [HLS-1](docs/tasks/HLS-1.md) | backlog | investigation | Use DIAG-2/HLS-5 target-device evidence to diagnose any repeated stalls that remain |
| [UI-1](docs/tasks/UI-1.md) | backlog | investigation | Skin comparison needed |

## How to plan the release

1. Send a plain list of desired changes, priorities, expected behavior and constraints. Include bug reproduction/version when available.
2. Triage updates/creates task records, then the index and this plan. Merge duplicate requests.
3. Select a small coherent set as committed; resolve important acceptance/dependency gaps before assigning work.
4. Start focused worker threads by task ID and authorized outcome. Implementation, review and release use their respective procedures.
5. Before release, check committed tasks and evidence. Record any authorized deferral/exception explicitly.
6. Copy shipped task IDs and scope changes into RELEASE_NOTES, then reset this planning file for the next cycle.

## Scope decisions

2026-09-27: Appi 0.7.16 was published from merge commit `af6791128009e5e9afd408221d8427c2baed65e1`. Shipped scope: HLS-5. Post-merge verification run 36297143439 and Pages deployment run 36297143062 passed. HLS-5 remains in review/partial verification because publication and automated tests do not establish target-device buffering effectiveness.


2026-09-27: 0.7.16 release/package run 36296897848 passed after correcting isolated test-harness pollution caught by the first gate attempt. All four playback branches are covered; the deterministic 0.7.16 artifact was generated at commit `6e71ad93276c993724a5973cb8814e603653f4d0`. Proceed to authorized integration/publication while retaining target-device verification as HLS-5's remaining review item.


2026-09-27: user explicitly committed HLS-5 for the next release and authorized implementation, integration and publication. Source audit of 0.7.15 confirmed Native Kodi automatic does not set InputStream Adaptive properties, so modes 0–2 are frozen for compatibility and Buffered Look Ahead Playback will be a new isolated mode 3. Version 0.7.16 is assigned to this release.


2026-09-26: Appi 0.7.15 was published from merge commit `2ba3ba2dc78519f55e6c01c0372a17f31b310fba`. Shipped scope: reopened HLS-4. Automated release/package run 36291375057, post-merge verification run 36291431201 and Pages deployment run 36291430966 passed. HLS-4 remains in review because target-device acceptance is still required.


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

No new release is committed. Appi 0.7.16 is published from merge commit `af6791128009e5e9afd408221d8427c2baed65e1`; post-merge verification run 36297143439 and Pages deployment run 36297143062 passed. HLS-5 remains in review/partial verification until target-device buffering effectiveness is tested.
