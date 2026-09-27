# Appi release notes

Each entry records the package shipped, its main user-visible changes, and verification at release time. For the current baseline and next tasks read [PROJECT_STATE.md](PROJECT_STATE.md) and [KNOWN_ISSUES.md](KNOWN_ISSUES.md); the [CHANGELOG.md](CHANGELOG.md) is the implemented feature history.

## 0.7.17 — candidate, 2026-09-27

- Committed scope: HLS-7, HLS-6, LANG-2, UI-2, UI-3. Base: `6d36d9a52733fbe6f3ded3ba5ee335cb779883e3`; candidate branch: `release/0.7.17`.
- Buffered Look Ahead now prepares asynchronously with cancellable progress before Kodi receives the URL. Recovery waits occur for missing media, and failure/cancel/retry/replacement cleanup is isolated by session token. VOD playlists remain stable across repeated access; opaque proxy URLs keep media extensions and byte-range requests are honored.
- Add buffered storage size (32–1024 MB, default 128), Highest available bitrate / Prompt for quality, a simple buffering indicator and optional cached-ahead MB/seconds overlay. Byte-based prefetch replaces the fixed 30-second ceiling. Initial reserve is 12 seconds; missing-segment recovery reserve is 6 seconds. Configuration affects only mode 3.
- Language lists retain alias matching and migrate legacy preferences. Settings About reads installed metadata; the packaged Appi icon matches the approved design exactly.
- Automated local verification: 73 tests passed, including real FFmpeg MPEG-TS and fMP4 decoding at start and after forward/backward seeks, real HTTP transfer integrity/auth/ranges, buffer-size differences, selected rendition preservation, failed retries/cancellation/replacement, legacy-language migration, About upgrade/rollback and unchanged modes 0–2. Tracker validation, ZIP/source/icon inspection and fallback checks passed.
- Local package SHA-256: `77dd83244e01bae295d3118073d28b13b2a6d634576cf4ffae84fde14a49b0b1`. GitHub release/package gate and publication are pending.
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
