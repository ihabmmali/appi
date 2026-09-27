# Appi release notes

Each entry records the package shipped, its main user-visible changes, and verification at release time. For the current baseline and next tasks read [PROJECT_STATE.md](PROJECT_STATE.md) and [KNOWN_ISSUES.md](KNOWN_ISSUES.md); the [CHANGELOG.md](CHANGELOG.md) is the implemented feature history.

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
