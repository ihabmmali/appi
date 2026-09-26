# Appi changelog

Implemented features, grouped by add-on version. A version listed here means its source/package was published in the repository; it does not by itself certify device testing. For details and earlier 0.7.x entries, see [README.md](README.md). This file is the concise ongoing release history; [RELEASE_NOTES.md](RELEASE_NOTES.md) records what each package shipped and how it was verified.

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
