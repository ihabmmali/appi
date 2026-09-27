# Appi release notes

Each entry records the package shipped, its main user-visible changes, and verification at release time. For the current baseline and next tasks read [PROJECT_STATE.md](PROJECT_STATE.md) and [KNOWN_ISSUES.md](KNOWN_ISSUES.md); the [CHANGELOG.md](CHANGELOG.md) is the implemented feature history.

## 0.7.16 — release candidate, 2026-09-27

- Included committed task: HLS-5.
- Pre-change source audit of the published 0.7.15 baseline confirmed that Native Kodi automatic returns before Appi assigns any `inputstream` property; no correction to that mode was required.
- Modes 0–2 remain the same playback paths: native Kodi on the original provider URL, InputStream Adaptive `ask-quality` on the original master URL, and InputStream Adaptive `adaptive` with its optional bitrate ceiling.
- New mode 3, **Buffered Look Ahead Playback**, is isolated behind a localhost HLS proxy owned by Appi's persistent service. It uses a temporary disk-backed rolling buffer with a 30-second target, 18-second startup reserve and 15-second recovery reserve and does not transcode media.
- The proxy rewrites variant and rendition playlists plus key/map URIs to opaque localhost resources, preserves discontinuities and representation metadata, handles byte ranges without double-ranging local resources, re-centres after seeks, and removes temporary session data on stop/error/abort.
- DIAG-2 now receives direct buffered-mode segment latency/throughput, actual buffered seconds, queued/downloaded segment counts, depletion/recovery and observed representation information; upstream authenticated URLs remain excluded.
- Release publication remains conditional on the repository's full automated release/package gate. Target-device verification remains required to determine whether 30+ seconds of actual buffered media eliminates the reported intermittent stalls.

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
