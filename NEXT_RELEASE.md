# Next Appi release

Planning status: open. Version: not assigned. Current baseline and fallback: [PROJECT_STATE.md](PROJECT_STATE.md).

0.7.21 is published. No next-release scope is currently committed. HLS-12, HLS-13, HLS-14 and HLS-15 remain in review for target-device acceptance of the shipped 0.7.21 behavior; any follow-up repair must be triaged and explicitly committed.

## Proposed scope

| Task | Selection | Priority | Reason |
| --- | --- | --- | --- |
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

2026-09-28: Appi 0.7.21 published through PR #10 / merge `d9e0be64681fa2dbe9cc434f81375a9c0992a3e1`. Final strengthened candidate run `36381180991` passed 94 tests (1 skipped), workflow validation and deterministic package inspection; final pre-integration evidence run `36381370108` also passed with no generated artifact drift. Post-merge verification run `36381516837` and Pages deployment run `36381516378` passed. Shipped scope: HLS-12, HLS-13, HLS-14 and HLS-15. Their delivery is released while target-device verification remains review/partial. Planning is reset; no next-release scope is committed.


2026-09-28: user explicitly summarized and committed the next Buffered Look Ahead repair scope: HLS-12 (seek/resume still broken), HLS-13 (buffering algorithm/deep-reservoir defect), HLS-14 (detailed debug overlay renders nothing), and new HLS-15 (normal preparation/recovery UI must show actual buffered KB/MB, not just a percentage bar). All four are committed next-release scope; HLS-12 and HLS-13 are release blockers.

2026-09-28: HLS-13 added after source review and target-device testing showed Buffered Look Ahead is not yet acting as the intended deep reservoir. 0.7.20 starts after a fixed 12-second reserve and then divides 70% of configured capacity equally across tracks; with 128 MB and video+audio, video receives only ~44.8 MB. HLS-13 requires startup to build a meaningful configured-capacity reservoir, dynamic track allocation, continuous high-water refill and progress-aware transfer timeouts. It must prove value on the problematic higher bitrate, not merely a lower rendition that ordinary ISA already plays.

2026-09-28: HLS-14 added as a confirmed implementation defect because the detailed overlay remains invisible during confirmed Buffered Look Ahead playback on 0.7.20. HLS-10 is therefore failed target-device verification; HLS-14 owns the actual display repair.

2026-09-28: published 0.7.20 failed target-device acceptance for HLS-11: Buffered Look Ahead still times out on seek/resume. HLS-12 replaces the recovery direction entirely. Each seek or saved-point start must create a fresh buffer epoch at the target, invalidate/cancel prior work, prepare aligned video/audio reserve there, and only then resume. Do not attempt another timeout increase or incremental re-centering patch. HLS-12 is a candidate pending explicit release commitment.

2026-09-27: Appi 0.7.20 published through PR #8 / merge `6e6db9bec185ec6b5eea664d27cb7b94f4efa2ef`. Post-merge verification run `36376270017` and Pages deployment run `36376269821` passed. Shipped scope: AUDIO-1, HLS-10 and HLS-11. Their delivery is released while target-device verification remains review/partial. The planning file is reset; no next-release scope is committed.


2026-09-27: 0.7.20 candidate passed corrected release/package run `36375784976` after the first gate caught and the branch fixed an overlay test-isolation regression. AUDIO-1 and HLS-11 candidate repairs are implemented without changing HLS modes 0–2. HLS-10 adds operation-specific overlay logging while retaining the existing window target until a confirmed HLS device test supplies evidence to change it. Artifact commit `1ca52ad0b55a3f3e19acd8e4b288d8d13fe57ab4`; target-device verification remains pending.


2026-09-27: user explicitly instructed that **all current candidates be committed**. AUDIO-1, HLS-10 and HLS-11 are now committed next-release scope. AUDIO-1 and HLS-11 are release-blocking playback regressions. HLS-10 is committed as an investigation-first verify/repair task: it must first reproduce the detailed-overlay failure on a confirmed Buffered Look Ahead HLS session before changing the overlay implementation. Existing backlog items remain backlog.

2026-09-27: AUDIO-1 added as a ready release-blocker candidate after the user confirmed that 0.7.19 is silent whenever InputStream Adaptive is used (manual selection and other ISA playback), while reverting the same media/device to 0.7.8 restores audible playback. Kodi still displays the audio-stream details during the silent state, so audio discovery is occurring; the newer preferred-audio service logic is a primary A/B regression boundary but is not assumed causal without evidence.

2026-09-27: target-device evidence refined: known multi-variant HLS masters (identified by exposed resolution choices) prepare and play well from time 0, but fail on manual seek and when starting from a saved non-zero playback point. HLS-11 is narrowed to HLS random-access/recovery and must test both in-session seek and cold resume-point start. The earlier HLS-10 no-overlay observation is now considered inconclusive until repeated on a positively identified HLS buffered session, because non-HLS items bypass Buffered Look Ahead entirely.

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

No next-release scope is committed. HLS-12, HLS-13, HLS-14 and HLS-15 are shipped in 0.7.21 and remain review/partial pending target-device acceptance. PLAY-1, HLS-1 and UI-1 remain backlog investigations; target-device acceptance for earlier shipped tasks remains tracked in their canonical task records.