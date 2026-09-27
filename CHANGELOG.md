# Appi changelog

Implemented features, grouped by add-on version. A version listed here means its source/package was published in the repository; it does not by itself certify device testing. For details and earlier 0.7.x entries, see [README.md](README.md). This file is the concise ongoing release history; [RELEASE_NOTES.md](RELEASE_NOTES.md) records what each package shipped and how it was verified.

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
