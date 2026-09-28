# Next Appi release

Planning status: open. Version: not assigned. Current baseline and fallback: [PROJECT_STATE.md](PROJECT_STATE.md).

0.7.19 is published and is the current repository package. Target-device testing is positive for initial Buffered Look Ahead preparation/playback and the simple startup windows, but detailed-overlay visibility and seek/recovery remain broken. Preferred-language application shipped in 0.7.19 and still needs target-device confirmation.

## Proposed scope

| Task | Selection | Priority | Reason |
| --- | --- | --- | --- |
| [HLS-10](docs/tasks/HLS-10.md) | candidate | buffered UI defect | Detailed debug overlay is enabled but invisible on 0.7.19 |
| [HLS-11](docs/tasks/HLS-11.md) | candidate | playback regression | Seek recovery times out; resume briefly plays, shows Appi buffering, stutters and times out again |
| [PLAY-1](docs/tasks/PLAY-1.md) | backlog | investigation | Resume persistence is working; only investigate the playback-start Trakt API error |
| [HLS-1](docs/tasks/HLS-1.md) | backlog | investigation | Use buffered-mode/diagnostic evidence to diagnose any underlying provider stalls that remain |
| [UI-1](docs/tasks/UI-1.md) | backlog | investigation | Skin comparison needed |

## How to plan the release

1. Send a plain list of desired changes, priorities, expected behavior and constraints. Include bug reproduction/version when available.
2. Triage updates/creates task records, then the index and this plan. Merge duplicate requests.
3. Select a small coherent set as committed; resolve important acceptance/dependency gaps before assigning work.
4. Start focused worker threads by task ID and authorized outcome. Implementation, review and release use their respective procedures.
5. Before release, check committed tasks and evidence. Record any authorized deferral/exception explicitly.
6. Copy shipped task IDs and scope changes into RELEASE_NOTES, then reset this planning file for the next cycle.

## Scope decisions

2026-09-27: 0.7.19 target-device follow-up is positive for initial Buffered Look Ahead preparation/playback and the simple startup windows, but the detailed debug overlay is invisible and seek/recovery is reproducibly broken. HLS-10 tracks the overlay. HLS-11 tracks the seek timeout plus the consistent post-failure sequence where resume briefly plays, displays Appi buffering, stutters and exits with buffering-failed timeout. Both are candidates, not yet committed scope.

2026-09-27: 0.7.19 is published through PR #7 / merge `f495858b2e8c1f146802c04b8533334ee8b36b79`; HLS-8, LANG-3, HLS-9 and UI-4 are shipped and retained in their canonical review records for target-device acceptance.

2026-09-27: user explicitly instructed that **all changes be committed to the next release** after uploading revised artwork. HLS-9 is promoted from candidate to committed scope. UI-4 is created and committed to package the newly uploaded artwork, which currently differs from the icon in the add-on resources. Existing committed blockers HLS-8 and LANG-3 remain in scope. Backlog investigations remain backlog.

2026-09-27: user explicitly committed the next release to focus mainly on HLS-8 and LANG-3. HLS-8 is the primary release blocker for a robust Buffered Look Ahead implementation; LANG-3 is the other release blocker for preferred-language application. HLS-9 remains a candidate dependency improvement and is not part of the committed core scope. PLAY-1 is moved to backlog because the suspected resume regression was withdrawn after longer playback confirmed Kodi stores the resume point; only the Trakt API notification remains to investigate.

2026-09-27: PLAY-1 added as a candidate after the user reported that 0.7.18 no longer preserves Kodi resume/play points and shows a Trakt API error at playback start. Appi currently delegates resume/watched state to Kodi using the canonical plugin playback URL, so the task must verify stable media identity/URL and capture the Trakt error source without assuming it is causal.

2026-09-27: target-device testing confirms 0.7.18 no longer crashes Kodi at startup. Buffered Look Ahead still fails acceptance (no/erratic preparation progress, playback failure, near-90%-then-timeout, retry-dependent success), tracked as HLS-8. Preferred-language selection appears ineffective at playback, tracked as LANG-3. Both are candidates, not yet committed scope.

2026-09-27: HLS-9 added as a candidate after the user required InputStream Adaptive to be an installation prerequisite whenever Appi uses it. Current 0.7.18 metadata marks inputstream.adaptive optional despite manual ISA and ABR modes depending on it.

2026-09-27: Appi 0.7.18 was published through PR #6 / merge `22bf3ba0e59ee5cf045836aa3d8256be3cc684e0`. The release/package run 36351377864, post-merge verification run 36352524841 and Pages deployment run 36352524365 passed. Shipped scope: reopened LANG-2 native-settings crash correction only. Target-device startup confirmation remains pending; scope is reset for the next planning cycle.

2026-09-27: 0.7.17 published all five committed tasks through PR #5 / merge `18ffae9349b2d225b575cee6a276ea8dcd59143b`. Release/package 36350783947, post-merge verification 36350856112 and Pages 36350855315 passed; deployed ZIP checksum verified. Scope reset for the next cycle; device acceptance stays open in the canonical task records.

2026-09-27: user explicitly instructed that **all tracked changes so far be committed for the next release**. HLS-6, LANG-2, UI-2 and UI-3 are now committed scope. HLS-7 is added and committed as a release blocker for the failed Buffered Look Ahead target-device behavior. HLS-1 and UI-1 remain backlog investigations because they were not current candidates.

2026-09-27: target-device testing of 0.7.16 Buffered Look Ahead failed acceptance. Observed behavior includes excessive startup delay, unreliable fast-forward/seek, a silent spin/no-playback state, later immediate playback-failed errors after retries, and a return to spinning after leaving and re-entering Recently Played. HLS-7 owns robustness and lifecycle-state repair. HLS-6 now separates a simple normal startup/buffering indicator from the optional detailed debug overlay.

2026-09-27: LANG-2 added as a candidate after the user required preferred audio and subtitle language settings to use curated common-language selection lists instead of free-text inputs. The released LANG-1 normalization behavior should be preserved underneath the new settings UX. This request was logged but not explicitly committed to release scope.

2026-09-27: UI-3 artwork dependency satisfied. The user selected the first generated Appi design and requested that it be stored in the repository for a future dev worker. The approved 512×512 PNG handoff asset is `artwork/appi-icon-selected.png`. UI-3 remains candidate scope; this request stores the artwork but does not explicitly commit UI-3 to the next release.

2026-09-27: UI-2 and UI-3 added as candidates. UI-2 adds a settings About entry that reads the installed Appi version from runtime metadata. UI-3 tracks Kodi add-on icon artwork and originally depended on the user supplying the graphic. Neither request was explicitly committed to release scope.

2026-09-27: HLS-6 expanded with an optional buffer-state debug overlay. The user requires a user-configurable visibility setting and considers a simple live text overlay sufficient, provided it shows the current buffer state. This remains part of the HLS-6 candidate and is not committed release scope yet.

2026-09-27: HLS-6 quality requirements corrected by the user. Buffered Look Ahead should not have the previously inferred maximum-bitrate ceiling. It must provide user-configurable buffer size plus a choice between automatically using the highest available bitrate and prompting the user to select an available bitrate/resolution. The task remains a candidate because this request was logged but not explicitly committed to release scope.

2026-09-27: HLS-6 added as a candidate after the user required Buffered Look Ahead Playback to have user-configurable buffer capacity, at minimum in storage units. The released 0.7.16 path has a fixed ~30-second target and hardcoded 384 MB disk ceiling, so the follow-up must make the configured storage value affect actual prefetch depth rather than merely exposing the existing safety cap. This request was logged but not explicitly committed to release scope.

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

No new implementation scope is committed. HLS-10 and HLS-11 are ready candidates based on 0.7.19 target-device findings. LANG-3 remains a shipped review item awaiting target-device language-selection confirmation.