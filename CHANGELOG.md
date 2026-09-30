# Appi changelog

Implemented features, grouped by add-on version. A version listed here means its source/package was published in the repository; it does not by itself certify device testing. For details and earlier 0.7.x entries, see [README.md](README.md). This file is the concise ongoing release history; [RELEASE_NOTES.md](RELEASE_NOTES.md) records what each package shipped and how it was verified.

## 0.7.23 — 2026-09-29

- HLS-24: release a successfully recovered exact sequential segment to Kodi immediately instead of waiting for the full recovery reserve; background refill continues and low reserve alone is not a terminal playback error. Fresh-epoch seek/cold-resume reserve gating remains intact.
- HLS-22: add settings-backed bounded per-track producer concurrency (default 2, range 1–4), distinct segment claims and active/peak concurrency telemetry while retaining contiguous reserve accounting, duplicate suppression and stale-epoch cancellation.
- HLS-23: make the debug-overlay setting a true master gate, close stale windows when disabled, render enabled telemetry as four bounded lines, and log renderer state transitions without sensitive stream data.
- Existing HLS modes 0–2 and the HLS-13 reservoir thresholds/accounting remain unchanged. Final candidate run `36661752457` passed 103 unit/smoke tests (1 skipped), workflow validation and deterministic package/index inspection; target Fire TV/provider acceptance remains pending.

## 0.7.22 — 2026-09-28

- Buffered Look Ahead now owns recovery for transient segment/provider stalls: it retries the exact needed media inside Appi under a bounded configurable policy instead of relying on repeated Kodi 503 retries, while stale/superseded seek epochs remain request-scoped.
- Add advanced Buffered Look Ahead controls for startup/high/low/critical reservoir thresholds, media/startup/recovery timeouts, seek/recovery reserve, prefetch lead, retry delay/attempts and optional paused-session retention. Defaults preserve the healthy 0.7.21 reservoir behavior.
- Separate playing, buffering, paused and stopped lifecycle handling so a long pause no longer looks like a dead player. Add handoff timing from reservoir-ready through Kodi requests/AV start and preload required key/map resources before handoff.
- Expand live and persisted diagnostics with per-track contiguous reserve, next-segment state, total cached bytes, retry state, a rolling pre-failure timeline and evidence-based failure classification. Detailed overlay rendering now targets a bundled modeless WindowXMLDialog, with a logged compatibility fallback.
- About shows the installed add-on version directly in its settings pane, and the approved flat icon is referenced through a new byte-identical resource path to bypass Kodi texture caching.
- Generated FFmpeg download scripts explicitly map the first video/audio streams and use stream copy plus `-threads 0`, retaining safe quoting and atomic partial-file rename.
- Existing HLS modes 0–2 remain unchanged. Automated candidate run `36515421099` passed all 100 unit/smoke tests (1 skipped); final lifecycle/package verification remains required before publication, and target Fire TV/provider acceptance remains separate.

## 0.7.21 — 2026-09-28

- Replace Buffered Look Ahead's fixed 12-second/equal-share cache with a configured-capacity producer/consumer reservoir. Startup now fills 50% of the configured bytes (or the complete remaining short VOD), background prefetch continues toward an 80% high-water mark, and refill resumes below a 60% low-water mark without statically splitting capacity between video and audio.
- Replace mutable seek re-centering with authoritative buffer epochs. Every discontinuous seek or cold non-zero resume aligns required tracks to the requested timeline, invalidates obsolete transfers, prioritizes the target, and rebuilds a fresh contiguous playable reserve before the request is released.
- Treat media-transfer timeout as a no-progress/inactivity bound rather than a total wall-clock deadline, while retaining explicit cancellation and bounded startup/recovery waits.
- Make the normal preparation/recovery text show actual contiguous playable KB/MB and its current target. Detailed buffer debug now uses a skin-independent modeless Kodi dialog and also reports playable seconds, water state, epoch, selected bitrate and measured provider throughput when available.
- Keep Native Kodi, InputStream Adaptive manual selection and InputStream Adaptive ABR modes unchanged. Automated release verification is required before publication; target Fire TV acceptance remains separate.

## 0.7.20 — 2026-09-27

- Harden preferred-audio selection against InputStream Adaptive startup churn: No preference is inert, stream lists must stabilize and be revalidated before selection, and the current Kodi audio stream is checked when available so an already-correct stream is not redundantly switched.
- Rework Buffered Look Ahead random access so cold non-zero resume starts and later seeks coordinate video/audio cursors by timeline, prioritize the requested segment, and keep bounded recovery timeouts request-scoped/retriable rather than failing the entire buffered session.
- Make recovery-timeout telemetry reachable and remove unconditional lower-quality advice from generic buffered preparation failures.
- Keep the detailed-overlay rendering target unchanged while adding operation-specific non-fatal logging for Kodi GUI lifecycle failures.
- Existing HLS modes 0–2 remain unchanged. Automated release/package run `36375784976` passed; target-device acceptance remains required.

## 0.7.19 — 2026-09-27

- Rework Buffered Look Ahead startup around a coordinated playable-reserve gate: the selected video and associated default audio rendition must both have contiguous startup media before Kodi receives the localhost URL, and progress reports the least-ready required track rather than optimistic aggregate work.
- Allow independent buffered tracks/resources to fetch concurrently while reserving disk capacity up front, so one stalled audio/key/media request cannot serialize and freeze every look-ahead download. Keep mode 3 isolated; native Kodi, manual InputStream Adaptive and adaptive-bitrate modes remain unchanged.
- Separate the 45-second preparation deadline from a 65-second plugin/service control-response window, make preparation/retry state visible, and keep failures bounded and session-isolated.
- Retry preferred audio/subtitle selection for up to 12 seconds after AV start while Kodi enumerates tracks, preserving No preference and saved/per-title subtitle precedence.
- Make InputStream Adaptive a required dependency and package the revised flat Appi icon exactly.

## 0.7.18 — 2026-09-27

- Fix the 0.7.17 Kodi startup crash trigger: the No preference language options now have a non-empty `none` value, avoiding a null text child in Kodi's native settings parser.
- Preserve legacy language preferences and explicit No preference, including recovery from empty 0.7.17 values. Playback code is unchanged.
- Add checks against the actual archived 0.7.17 settings and validate every list option/default in both source and ZIP. Target Fire TV recovery still needs confirmation.

## 0.7.17 — 2026-09-27

- Repair Buffered Look Ahead startup, seek recovery and session replacement. Startup has a visible cancelable progress dialog; failures are bounded and explicit. Existing playback modes 0–2 remain unchanged.
- Add a 32–1024 MB buffered storage setting (128 MB default), Highest available bitrate / Prompt for quality, simple buffering feedback and an optional live MB/seconds overlay.
- Replace preferred audio/subtitle text fields with common-language lists, migrate old aliases, add About with the installed runtime version, and package the approved Appi icon.
- Fire TV/provider acceptance remains pending. Keep 0.7.12 as the usable fallback.

## 0.7.16 — 2026-09-27

- Add **Buffered Look Ahead Playback** as a fourth, isolated HLS mode backed by a localhost proxy and temporary disk buffer; the target look-ahead is 30 seconds, startup reserve 18 seconds and recovery reserve 15 seconds.
- Confirm before implementation that **Native Kodi automatic** is genuinely native: it does not assign InputStream Adaptive properties. Preserve that path plus the existing InputStream Adaptive ask-quality and adaptive-bitrate paths.
- Prefetch sequential VOD HLS segments to disk without transcoding, proxy child/audio/subtitle playlists, keys and initialization maps, preserve discontinuities, and safely re-centre look-ahead after seeks.
- Extend diagnostics for the buffered path with measured segment latency/throughput, buffer depth, queued/downloaded segment counts, depletion/recovery and selected-representation metadata while excluding authenticated upstream URLs.
- Add independent regression coverage for all four HLS modes plus deterministic buffer, recovery, seek, cleanup, byte-range and playlist-rewrite tests.
- Target-device testing is still required to determine whether the deeper playable buffer eliminates the reported intermittent provider stalls.

## 0.7.15 — 2026-09-26

- Restore the proven 0.7.12 manual HLS playback architecture after 0.7.13 and 0.7.14 both failed target-device manual-selection playback.
- Manual selection now keeps the original provider HLS master URL and delegates rendition discovery/selection/playback to InputStream Adaptive `ask-quality`.
- Remove Appi's pre-play child-rendition substitution from the active playback path while preserving native HLS mode, adaptive ABR mode, diagnostics, subtitles and playback history.
- Retain 0.7.12 as the usable fallback until target-device acceptance of 0.7.15.

## 0.7.14 — 2026-09-26

- Repair authenticated manual HLS variant resolution by preserving the master query for same-origin relative child playlists and retaining Kodi request options.
- Keep HLS rendition metadata associated with the exact selected child URL; expose resolution, advertised average/peak bandwidth and codecs in the chooser.
- Extend diagnostics to schema 2 with stall intervals, representation changes, cache/read-ahead InfoLabels when available, pre-stall history and evidence-qualified causal classification.
- Explicitly record unsupported per-segment HTTP timing and exact InputStream Adaptive queue/representation internals rather than treating configured cache size as proof of buffered media.
- Target-device acceptance remains pending; 0.7.12 is retained as the usable playback fallback.

## 0.7.13 — 2026-09-26

- Repair Search cancellation/context handling and add persistent bounded keyword history with reuse, edit, delete and clear actions.
- Finalize downloaded-subtitle capture at playback stop so a newly downloaded subtitle is not lost between polling intervals.
- Add overlap-proven fast TV refresh plus optional idle-only automatic refresh with lock/backoff and full-refresh fallback.
- Add normalized preferred audio/internal-subtitle language selection while retaining per-title subtitle precedence.
- Add opt-in bounded, sanitized playback diagnostic capture/export.
- Separate HLS playback into native Kodi, Appi-selected fixed rendition, and explicit InputStream Adaptive ABR with an optional bitrate ceiling; manual quality Cancel now aborts before playback side effects.
- Automated tests and package verification pass; target-device verification remains pending for navigation, subtitle restoration and runtime ABR switching.

## 0.7.12 — 2026-09-24

- Preserve active search query in a bounded session so returning from a TV show can reconstruct results without another keyboard prompt.
- Keep search results visible after Appi Favorite actions refresh the Kodi container.
- Add **New Search...** while retaining results on cancellation.
- Retain the 0.7.8 HLS and playback path. Search navigation still needs device verification.

## 0.7.11 — 2026-09-22

- Restore synchronous cached-title search from 0.7.8 after asynchronous navigation regressions in 0.7.9–0.7.10.
- Keep automatic next episode, season watched action and Favorites-first context actions.

## 0.7.10 — 2026-09-22

- Attempt to restore search results navigation after entering category and query. Superseded by 0.7.11–0.7.12 search changes.

## 0.7.9 — 2026-09-22

- Add automatic next episode preference, native season watched action and Favorites-first context ordering.
- Change search result/favorites navigation. Subsequent releases addressed regressions in that path.

## 0.7.8 — 2026-09-20

- Make Kodi's video database authoritative for watched state and resume bookmarks; remove duplicate Appi controls.
- Preserve Recently Played as identity/order and keep the package available as the user-confirmed fallback.

## 0.7.7 — 2026-09-20

- Add favorites folders, recent TV progression and playback options, metadata rating refresh and local FFmpeg script output. Its Appi-managed watched/resume behavior was superseded in 0.7.8.

## 0.7.6 — 2026-09-19

- Replace device-side download/mux handling with external FFmpeg scripts; expand metadata queue/status controls.

## 0.7.0–0.7.5

- Introduce background TMDb Helper metadata, batching, offline download iterations and management, then transition toward the external download workflow. See the version-by-version [README](README.md) for the distinct behavior in each release.

## 0.6.3

- Preserve provider order, add native sorting and indexed catalogue browsing, and move refresh/clear actions to Settings.

## 0.8.0 experimental archive

- The ZIP and branch exist, but the standard Kodi browser was restored in 0.7.1 and the current release line is 0.7.13. Do not treat 0.8.0 as the current release based on its higher number.
