# Appi release notes

Each entry records the package shipped, its main user-visible changes, and verification at release time. For the current baseline and next tasks read [PROJECT_STATE.md](PROJECT_STATE.md) and [KNOWN_ISSUES.md](KNOWN_ISSUES.md); the [CHANGELOG.md](CHANGELOG.md) is the implemented feature history.

## 0.7.22 — 2026-09-28

- Committed scope: HLS-16, HLS-17, HLS-18, HLS-19, HLS-20, HLS-21, UI-5, UI-6 and DOWNLOAD-1. Base `fd0bd5b08228c34b09de684f7b4b1f865a09e2d2`; branch `release/0.7.22`.
- HLS-19 moves true depletion recovery inside Appi: transient provider/transport failures retry the exact required segment under configurable delay/attempt/overall-timeout bounds and then rebuild a recovery reserve. A final HTTP failure is returned only after Appi's policy is exhausted; stale seek epochs remain independently supersedable.
- HLS-18 exposes advanced tuning while retaining 0.7.21-equivalent defaults: startup 50%, high-water 80%, low-water 60%, critical 15%, media inactivity 15s, startup 180s, seek reserve 12s/4MB minimum, prefetch lead 24s, recovery timeout 60s, retry delay 500ms, unlimited retries within the overall timeout, recovery reserve 6s and unlimited paused-session retention by default.
- HLS-20 instruments reservoir-ready, plugin handoff, first master/media/key/map/segment requests, first bytes served and Kodi AV start with monotonic timestamps; required key/map resources are preloaded before startup handoff.
- HLS-21 retains a bounded rolling pre-failure timeline with playable/total cache, required-track reserve/next-segment states, transfer timing/throughput, recovery state and lifecycle state, then classifies observable failure modes without fabricating unsupported Kodi internals.
- HLS-16 uses a bundled modeless `WindowXMLDialog` as the primary detailed-overlay renderer and keeps the prior WindowDialog only as a logged compatibility fallback. HLS-17 distinguishes current playable data, startup target and configured capacity in preparation feedback.
- UI-5 removes the nested About dialog and synchronizes a read-only installed-version field from runtime add-on metadata. UI-6 references `resources/icon-v2.png`; its Git blob SHA is exactly the approved prior icon SHA `08016a229ed053e000deffad659a2b94bd64acfc`.
- DOWNLOAD-1 generates FFmpeg remux scripts with `-map 0:v:0 -map 0:a:0 -c copy -threads 0` while preserving shell quoting, noninteractive execution, temporary partial output and atomic final rename.
- First package gate run `36515215335` was blocked by seven stale/compatibility test assumptions before artifact creation. After fixing the direct-session timeout compatibility and release fixtures, run `36515421099` passed all 100 unit/smoke tests (1 skipped) and stopped only on task-record template validation; those task records were normalized before the final gate.
- Final candidate/package run `36515744781` passed all 100 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/hash/index inspection and the package job. Deterministic artifact commit: `971d29d4145411e0c78703326246b770c82d95c3`. ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`.
- Published through PR #11 / merge `92131c95c1d047eb7a683e8e5e2e6abe10e1a518`. Final publication gate run `36626983906` passed 100 tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/index inspection and packaging. Final artifact commit `6f78d101be5069d79f3a4328cb6a90a2df9cd47f`; ZIP SHA-256 `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`. Pages deployment run `36627135052` completed successfully. Delivery: [plugin.video.appi-0.7.22.zip](https://ihabmmali.github.io/appi/plugin.video.appi-0.7.22.zip). The published index retains 0.7.21 and 0.7.8 alongside 0.7.22 (plus 0.7.14 and 0.7.12).
- Target-device acceptance remains required for visible overlay rendering, real provider recovery/classification, long-pause resume, handoff latency, icon cache refresh and actual FFmpeg transfer-rate comparison. Modes 0–2 are intentionally unchanged.

## 0.7.21 — 2026-09-28

- Committed scope: HLS-12, HLS-13, HLS-14 and HLS-15. Base `4a415f9eaeb48c77ef2fcaa895db90d7e66ab183`; branch `release/0.7.21`; main implementation `f91e3f25c012267a86d91c344a68ee5b941438e2`; capacity/test correction `568300582687d75c0ddfacab9b4a0a2e3cf31dff`.
- HLS-13 replaces fixed 12-second/equal-share buffering with a shared byte reservoir: 50% configured-capacity startup target, 80% high-water, 60% low-water, 15% critical reserve, dynamic video/audio use, continuous refill, measured throughput and inactivity-based media transfer timeout.
- HLS-12 gives each seek/resume target a new epoch, aligns required tracks by timeline, cancels or discards stale work, prioritizes the target and requires a fresh contiguous reserve before that epoch can serve playback.
- HLS-15 wires the ordinary preparation/recovery UI to active-epoch playable bytes and target bytes, so KB/MB remains visible without enabling detailed debug.
- HLS-14 replaces fullscreen-window control injection with a guarded modeless `WindowDialog` overlay and exposes playable MB/seconds, water state, epoch and optional selected/provider bitrate metrics.
- Existing HLS modes 0–2 are intentionally unchanged. The design does not auto-downgrade quality and cannot sustain a rendition indefinitely when long-term provider throughput remains below consumption.
- Gate run `36380665062` exposed four stale 0.7.20-oriented test assumptions; corrected run `36380784448` then passed 90 tests but correctly stopped on lifecycle tracker metadata. Run `36380895989` passed the full gate and produced the first candidate package. The acceptance suite was then strengthened for high/low-water hysteresis, upstream-stall masking, measured sustained-throughput deficit reporting and slow-but-progressing transfers.
- Final candidate run `36381180991` passed 94 tests (1 skipped), tracker validation, deterministic rebuild and package/index inspection. Final deterministic artifact commit: `26216385f185476b778f73b8dae5e7abfe73f339`. ZIP SHA-256: `0e8c615d40cf9f42e0345c61e11a7b244fc443c8858902d53fffda92c1935c81`.
- Published through PR #10 / merge `d9e0be64681fa2dbe9cc434f81375a9c0992a3e1`. Post-merge verification run `36381516837` passed and Pages deployment run `36381516378` completed successfully. Delivery: [plugin.video.appi-0.7.21.zip](https://ihabmmali.github.io/appi/plugin.video.appi-0.7.21.zip).
- Target-device acceptance remains required for the user's problematic higher-bitrate stream, forward/backward/repeated seek, saved-point start, numeric startup status and visible detailed overlay.

## 0.7.20 — 2026-09-27

- Candidate scope: AUDIO-1, HLS-10 and HLS-11. Base `24ac0358640864a0129d97b638ca37c616f6612b`; branch `release/0.7.20`; implementation `4c5363e3220dc16507b308e6ccfa8bbec4eb6d40`.
- AUDIO-1 preserves the original native/manual/adaptive HLS handoff and hardens only preferred-audio mutation: stable/revalidated stream enumeration, inert No preference/no-match behavior, and a best-effort current-stream check that avoids redundant `setAudioStream()` calls.
- HLS-11 coordinates random access across active tracks, prioritizes the requested target, keeps recovery timeouts request-scoped/retriable, and removes generic lower-quality advice where throughput has not been established as causal.
- HLS-10 retains window 12005 pending a confirmed HLS target-device reproduction and adds exact non-fatal logging for Window, ControlLabel, addControl, setLabel and removeControl.
- First gate run `36375728261` was correctly blocked by an existing pure-overlay test because the new module imported `xbmc` outside Kodi. The compatibility correction kept runtime logging intact; corrected release/package run `36375784976` then passed 87 tests (1 skipped), tracker validation, deterministic rebuild and package/index inspection.
- Deterministic artifact commit: `1ca52ad0b55a3f3e19acd8e4b288d8d13fe57ab4`. ZIP SHA-256: `41e1bdec7229d1a0a3d8787427ac9c434fb773e302c7d8f5bae428de0de7755f`.
- Published through PR #8 / merge `6e6db9bec185ec6b5eea664d27cb7b94f4efa2ef`. Post-merge verification run `36376270017` passed and Pages deployment run `36376269821` completed successfully. Delivery: [plugin.video.appi-0.7.20.zip](https://ihabmmali.github.io/appi/plugin.video.appi-0.7.20.zip).
- Target-device acceptance remains separately required for audible ISA playback, multi-variant HLS seek/resume and enabled/disabled debug-overlay visibility.

## 0.7.19 — 2026-09-27

- Target-device regression: InputStream Adaptive playback is completely silent in manual selection and other ISA playback on 0.7.19 even though Kodi still displays audio-stream details; reverting the same media/device to 0.7.8 restores audible playback. AUDIO-1 tracks this. The newer preferred-audio selection service is a primary regression boundary to A/B test, but cause is not yet established.

- Published through PR #7 / merge `f495858b2e8c1f146802c04b8533334ee8b36b79`; the repository install index lists 0.7.19 as current.
- Target-device follow-up: positively identified multi-variant HLS masters prepare and play well from time 0. Manual seeking and starting from a saved non-zero playback point still fail; after a seek timeout, resume briefly plays, displays **Appi buffering**, stutters and exits with another buffering-failed timeout (HLS-11). The earlier no-overlay observation is not yet conclusive because that test item may not have traversed Buffered Look Ahead; HLS-10 now requires confirmation on a known HLS buffered session.

- Committed scope: HLS-8, LANG-3, HLS-9 and UI-4. Base `c7a344ae2afa1160adb7daf522092c89b46105bf`; branch `release/0.7.19`; PR #7.
- HLS-8: replace optimistic/single-track preparation with a coordinated startup gate. The selected video and associated default audio rendition are prepared before handoff; startup progress is the minimum readiness of required tracks. Independent resources download concurrently under explicit byte reservations rather than sharing one network-wide lock, so a stalled request cannot block every track.
- HLS-8: retain a 45-second bounded preparation deadline but give the plugin/service mailbox a 65-second control window, preventing the previous same-deadline race. Progress reaches 100% only when the playable reserve is ready; stalled preparation reports retry state and fails explicitly.
- LANG-3: preferred audio/internal-subtitle application retries for up to 12 seconds after AV start so Kodi/InputStream Adaptive can enumerate streams first. No preference remains inert; missing matches fall back cleanly; saved external/per-title subtitle choices retain precedence.
- HLS-9: `inputstream.adaptive` is now a required manifest dependency while runtime fallback diagnostics remain intact.
- UI-4: `plugin.video.appi/resources/icon.png` is the exact current `artwork/appi-icon-selected.png` blob.
- Existing HLS modes 0–2 are unchanged by the implementation.
- Gate evidence: run 36370310600 correctly failed before packaging because an older quality-selection test fixture advertised an audio rendition without providing its playlist; the fixture was updated to model the now-required associated-audio preparation. Corrected run 36370407423 then passed 81 tests (1 skipped), tracker validation, deterministic rebuild and package/index inspection and completed the package job.
- Candidate artifact commit: `f25cfffb099eaa43f3865c5ac2a227d4958a7a2d`. ZIP SHA-256: `1bee04f63b79a4654ff0dcf8e8db94ee89e709d16091722f38283c1b01bf2f4d`.
- Final review adds direct assertions against the generated ZIP for the required InputStream Adaptive dependency and exact revised icon. Target-device acceptance remains separately required for the two reported Buffered Look Ahead episodes, actual language switching, clean dependency resolution and Kodi artwork display.

## 0.7.18 — 2026-09-27

- Scoped crash hotfix: reopened LANG-2. Base `a0b9eacb23b4816df7ac4c0f60e9c51fb7d1eb79`; branch `release/0.7.18`.
- Fix the 0.7.17 Kodi startup crash trigger: the No preference language options now have a non-empty `none` value, avoiding a null text child in Kodi's native settings parser.
- Preserve legacy language preferences and explicit No preference, including recovery from empty 0.7.17 values. Playback code is unchanged.
- Add checks against the actual archived 0.7.17 settings and validate every list option/default in both source and ZIP. Target Fire TV recovery still needs confirmation.

- Local verification: 76 tests passed, including all prior regressions plus native-settings structural safety, archived 0.7.17 reproduction fixture and language migration across fresh/legacy/empty/explicit-None cases. This is self-review; no target-device crash dump or recovery observation is available yet.
- ZIP SHA-256: `0a0a739e8f8eca85c0268d46027c060b57b185b2b8ec4464b3ebb72289181447`. Release/package run 36351377864 passed and produced artifact commit `052db2530469cd2582dcd8e4b8e197f48071db7d`. Published through [PR #6](https://github.com/ihabmmali/appi/pull/6), merge `22bf3ba0e59ee5cf045836aa3d8256be3cc684e0`; post-merge verification run 36352524841 and Pages deployment run 36352524365 passed. Delivery: [plugin.video.appi-0.7.18.zip](https://ihabmmali.github.io/appi/plugin.video.appi-0.7.18.zip).
- The 0.7.17 archive is retained for regression evidence, not recommended installation. 0.7.12 remains the usable fallback.

## 0.7.17 — 2026-09-27

**Failed device acceptance:** user reports Kodi crashes immediately after installation and on subsequent Kodi launches, without entering Appi. Empty language-list option text is a native settings-parser crash trigger; superseded by the 0.7.18 correction.

- Committed scope: HLS-7, HLS-6, LANG-2, UI-2, UI-3. Base: `6d36d9a52733fbe6f3ded3ba5ee335cb779883e3`; candidate branch: `release/0.7.17`.
- Buffered Look Ahead now prepares asynchronously with cancellable progress before Kodi receives the URL. Recovery waits occur for missing media, and failure/cancel/retry/replacement cleanup is isolated by session token. VOD playlists remain stable across repeated access; opaque proxy URLs keep media extensions and byte-range requests are honored.
- Add buffered storage size (32–1024 MB, default 128), Highest available bitrate / Prompt for quality, a simple buffering indicator and optional cached-ahead MB/seconds overlay. Byte-based prefetch replaces the fixed 30-second ceiling. Initial reserve is 12 seconds; missing-segment recovery reserve is 6 seconds. Configuration affects only mode 3.
- Language lists retain alias matching and migrate legacy preferences. Settings About reads installed metadata; the packaged Appi icon matches the approved design exactly.
- Automated local verification: 73 tests passed, including real FFmpeg MPEG-TS and fMP4 decoding at start and after forward/backward seeks, real HTTP transfer integrity/auth/ranges, buffer-size differences, selected rendition preservation, failed retries/cancellation/replacement, legacy-language migration, About upgrade/rollback and unchanged modes 0–2. Tracker validation, ZIP/source/icon inspection and fallback checks passed.
- Tested implementation commit: `842ef37c8deb6ce340946dbbafa29fbd8745ec0c`.
- Local package SHA-256: `77dd83244e01bae295d3118073d28b13b2a6d634576cf4ffae84fde14a49b0b1`. Release/package run 36350783947 passed; deterministic artifact commit `20785a1af1e4ebe4d474532b42f4777bff8e337e`. Published through [PR #5](https://github.com/ihabmmali/appi/pull/5), merge commit `18ffae9349b2d225b575cee6a276ea8dcd59143b`. Post-merge verification run 36350856112 and Pages deployment run 36350855315 passed.
- Delivery: [plugin.video.appi-0.7.17.zip](https://ihabmmali.github.io/appi/plugin.video.appi-0.7.17.zip). The deployed ZIP was downloaded and its SHA-256/ZIP integrity verified against the tested package; the install index includes 0.7.17 and the preserved 0.7.12/0.7.8 fallbacks.
- Self-review only. Target-device acceptance remains pending for the user's failing streams, UI/skin behavior and icon caching. HLS-7 code-level repair is implemented; it is not a claim that Fire TV/provider behavior has been proven fixed. Tasks remain review/partial. 0.7.12 stays the usable fallback and 0.7.8 is retained.
- Bounds/limitations: 45-second preparation deadline excludes quality-choice time; reserve waits are 20 seconds. Per-transfer size is limited to one quarter of the budget/active-track share, so unusually large segments may require a larger buffer or lower quality. Overlay seconds describe media cached ahead of Kodi's request cursor, excluding its private decode queue. See ARCHITECTURE for resource limits.

## 0.7.16 — 2026-09-27

- Included committed task: HLS-5.
- Pre-change source audit of the published 0.7.15 baseline confirmed that Native Kodi automatic returns before Appi assigns any `inputstream` property; no correction to that mode was required.
- Modes 0–2 remain the same playback paths: native Kodi on the original provider URL, InputStream Adaptive `ask-quality` on the original master URL, and InputStream Adaptive `adaptive` with its optional bitrate ceiling.
- New mode 3, **Buffered Look Ahead Playback**, is isolated behind a localhost HLS proxy owned by Appi's persistent service. It uses a temporary disk-backed rolling buffer with a 30-second target, 18-second startup reserve and 15-second recovery reserve and does not transcode media.
- The proxy rewrites variant and rendition playlists plus key/map URIs to opaque localhost resources, preserves discontinuities and representation metadata, handles byte ranges without double-ranging local resources, re-centres after seeks, and removes temporary session data on stop/error/abort.
- DIAG-2 now receives direct buffered-mode segment latency/throughput, actual buffered seconds, queued/downloaded segment counts, depletion/recovery and observed representation information; upstream authenticated URLs remain excluded.
- Automated verification: the first package attempt (run 36296858373) was correctly blocked by isolation pollution in the new test harness; after that test-only defect was corrected, release/package run 36296897848 passed all 54 unit/smoke tests, workflow tracker validation, deterministic build, ZIP/hash/index inspection and packaging.
- Release artifact commit: `6e71ad93276c993724a5973cb8814e603653f4d0`; `plugin.video.appi-0.7.16.zip` SHA-256: `ecb310e42b016cf968b27e2af4d25ed6f1b106b888a9c0da387bde4bde595138`.
- Final candidate lifecycle gate run 36297078894 passed after the review/tracker evidence was recorded.
- Published merge commit: [af6791128009e5e9afd408221d8427c2baed65e1](https://github.com/ihabmmali/appi/commit/af6791128009e5e9afd408221d8427c2baed65e1). Post-merge main verification run 36297143439 passed and Pages deployment run 36297143062 succeeded.
- Package: [plugin.video.appi-0.7.16.zip](https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.16.zip); SHA-256: `ecb310e42b016cf968b27e2af4d25ed6f1b106b888a9c0da387bde4bde595138`.
- Target-device verification remains required to determine whether 30+ seconds of actual buffered media eliminates the reported intermittent stalls; HLS-5 therefore remains in review/partial verification.

## 0.7.15 — 2026-09-26

- Included committed task: HLS-4.
- 0.7.14 failed target-device manual-selection playback exactly as 0.7.13 did; the query-preservation repair did not restore the required path.
- Source comparison against working 0.7.12 commit `a099e521cfa767bc8cdee9a72988dcd8a92b9c73` showed that 0.7.12 passed the original HLS master URL to InputStream Adaptive with `stream_selection_type=ask-quality`; Appi did not resolve/play a child rendition itself.
- 0.7.15 restores that architecture: the original master URL remains the ListItem path and InputStream Adaptive owns rendition discovery, manual quality selection and child-playlist playback.
- Native Kodi HLS, automatic adaptive mode, diagnostics, subtitles and playback history remain in place.
- Automated verification: release/package run 36291375057 passed unit/smoke tests, workflow tracker validation, deterministic build, ZIP/hash/index inspection and packaging; post-merge main run 36291431201 passed the same release verification on the integrated source; Pages deployment run 36291430966 succeeded.
- Published merge commit: [2ba3ba2dc78519f55e6c01c0372a17f31b310fba](https://github.com/ihabmmali/appi/commit/2ba3ba2dc78519f55e6c01c0372a17f31b310fba).
- Package: [plugin.video.appi-0.7.15.zip](https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.15.zip); SHA-256: `d8952fcd9b2a30dbcf4e113c28ec8f3ba316c44498218cbb437beaefd65f7bba`.
- Target-device acceptance remains pending. HLS-4 stays in review/partial verification until manual selection is confirmed on the target Fire TV/provider stream. 0.7.12 remains the usable playback fallback.

## 0.7.14 — 2026-09-26

- Included committed tasks: HLS-4 and DIAG-2.
- HLS manual fixed-quality playback now resolves relative child playlists without dropping an authenticated master's query string, preserves Kodi URL request options, and keeps resolution/average bandwidth/peak bandwidth/codecs attached to the exact selected variant.
- Diagnostics schema 2 adds timestamped stall intervals, representation changes, Kodi cache/read-ahead InfoLabels when available, bounded pre-stall history and evidence-qualified causal classifications.
- Privacy is retained: raw authenticated URLs, queries, cookies/credentials and subtitle contents are not exported.
- Known observability limit: supported Kodi add-on Python does not reliably expose per-segment InputStream Adaptive HTTP timing, exact internal queue depth or every internal ABR decision. Those fields are explicitly reported unavailable rather than fabricated.
- Published merge commit: [4eb272c0da19b716906e4909366f6d6ba4173874](https://github.com/ihabmmali/appi/commit/4eb272c0da19b716906e4909366f6d6ba4173874).
- Automated verification: PR run 36290602785 passed; packaging run 36290637371 passed verification and committed deterministic artifacts; post-merge main run 36290741628 passed unit/smoke tests, workflow tracker validation, deterministic repository build, ZIP/hash/index inspection and fallback preservation.
- Package: [plugin.video.appi-0.7.14.zip](https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.14.zip); SHA-256: `99e2a84c741c8b518058cd93233412ea771969dd4f34690beb31880d5a0db691`.
- Target-device acceptance remains pending. Delivery is published, but HLS-4 and DIAG-2 remain in review/partial verification until manual rendition playback and failing/working diagnostic captures are verified on the target Fire TV/provider stream. 0.7.12 remains the usable playback fallback.

## 0.7.13 — 2026-09-26

- Published merge commit: [0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a](https://github.com/ihabmmali/appi/commit/0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a). The implementation checkpoint was `48c2af72df70ed3e6f3e82d805691c49bcbe6553`.
- Included tasks: SEARCH-1, SUB-1, SEARCH-2, REFRESH-1, REFRESH-2, LANG-1, DIAG-1, HLS-3 and HLS-2.
- Search: explicit cancellation returns to the prior Appi context; bounded persistent history supports reuse/edit/delete/clear while preserving stable result sessions.
- Subtitles: playback-stop finalization captures a newly downloaded external subtitle even when the ordinary poller has seen it only once.
- Catalogues: fast TV refresh proves a contiguous overlap with the provider-order cache and otherwise falls back to full refresh; optional scheduled/startup refresh runs only while idle, serializes refreshes and backs off after failures.
- Languages: preferred audio and internal-subtitle labels normalize common names/codes such as English/eng/en; per-title subtitle modes and saved external subtitles retain precedence.
- Diagnostics: opt-in bounded sanitized playback session data can be exported as a ZIP. Full authenticated URLs, credentials, cookies and subtitle contents are excluded; metrics unavailable through Kodi Python are marked unavailable.
- HLS: Native Kodi, Manual fixed quality and explicit InputStream Adaptive ABR are separate modes. Manual selection occurs before playback resolution so Cancel aborts without creating a playback session; ABR supports an optional bitrate ceiling.
- Automated verification: implementation run 36277010649 passed; reconciled release-candidate run 36287035152 passed; post-merge `main` run 36287058096 passed the unit/smoke suite, tracker validation, deterministic repository build, ZIP/hash/index inspection and 0.7.8 fallback preservation.
- Published limitations: target-device acceptance is still pending for real Kodi back/cancel/favorites navigation, subtitle restore across actual stop/resume/restart, provider-specific fast refresh, preferred-language behavior on provider tracks, diagnostic capture during a real stall, and runtime InputStream Adaptive representation switching. HLS-2 must not be interpreted as device proof that switching occurred.
- Package: [plugin.video.appi-0.7.13.zip](https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.13.zip); SHA-256: `9767a9dee2302e26422f245ab3d8773ff3e6693ce0446ad86e4267e6a54b7b53`.
- Fallback retained: 0.7.8 remains published as the user-confirmed known-good fallback. The repository index lists 0.7.13 as current followed by 0.7.12, 0.7.11 and 0.7.8.

## 0.7.12 — 2026-09-24

- Source commit: [a099e521cfa767bc8cdee9a72988dcd8a92b9c73](https://github.com/ihabmmali/appi/commit/a099e521cfa767bc8cdee9a72988dcd8a92b9c73).
- Package: [plugin.video.appi-0.7.12.zip](https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.12.zip), listed as current on the Pages install index.
- Implemented: bounded search-session storage, stable **New Search...**, retention of search results after favorites refresh, and preservation of the 0.7.8 playback path.
- Verification recorded: repository manifest, package index, source and README inspected on 2026-09-24. Device acceptance of the 0.7.12 search behavior has not been recorded.
- There was no GitHub Releases entry for this package as of 2026-09-24; the packaged ZIP and Pages index are the published artifacts.
