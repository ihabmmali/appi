# Appi architecture

Updated for the 0.7.13 release candidate (2026-09-26). Source describes implemented behavior; accepted requirements and decisions describe intended behavior.

## Project goals and binding rules

- Provide responsive Kodi browsing/search/playback of user-configured movie and TV M3U catalogues.
- Preserve native Kodi watched/resume authority and user favorites, metadata and subtitles.
- Preserve provider order where required; a partial refresh must not discard a valid cache on failure/cancellation.
- Keep navigation predictable through search, show/back, cancellation and favorite actions.
- Evaluate playback changes with real evidence and retain the fallback named in PROJECT_STATE.
- Keep experiments, metadata service, external FFmpeg scripts and catalogue refresh scoped to their responsibilities.
- Release commands: `python3 -m unittest discover -s tests`, then `python3 tools/build_repository.py`; inspect packages/hashes/index and record device checks separately.
- Tracker-only edits use `python3 tools/check_workflow.py` and relevant checker tests; no add-on package rebuild is needed.

These goals bind the portable [lifecycle](LIFECYCLE.md) to Appi. Accepted changes to these rules require a documented decision; current source may not satisfy every goal.

## Entry points and modules

| Area | Primary source | Responsibility |
| --- | --- | --- |
| Kodi plugin UI | `plugin.video.appi/default.py`, `resources/lib/app.py` | Routes, directories, search, refresh, playback and context actions |
| M3U and network | `resources/lib/m3u.py`, `http.py` | Parse feeds and request list/stream data |
| Catalogues and cache | `resources/lib/catalog.py`, `cache.py`, `refresh_logic.py`, `refresh_state.py` | Identity, sorting, pagination, provider-order cache, fast-refresh overlap logic and refresh serialization/state |
| Playback state | `resources/lib/kodi_status.py`, `playback_history.py`, `playback_prefs.py` | Kodi watched/resume integration, recent order and preferences |
| Metadata service | `service.py`, `resources/lib/metadata.py` | Background TMDb Helper requests and bounded SQLite cache |
| Other user data | `resources/lib/favorites.py`, `search_history.py`, `subtitle_store.py`, `subtitle_service.py`, `languages.py` | Favorites, search history, saved subtitles and playback language preferences |
| HLS / diagnostics | `resources/lib/hls.py`, `diagnostics.py` | Master-playlist rendition parsing, explicit HLS mode support and bounded privacy-safe playback evidence |\n| External downloads | `resources/lib/downloads.py` | Produce scripts for an external FFmpeg watcher |
| Build and distribution | `tools/build_repository.py`, `repository.appi/`, `addons.xml`, `index.html` | Kodi ZIPs, checksums, repository feed and Pages install index |

## Catalogue flow

- The configured movie URL yields one M3U list. Refresh parses movie records, deduplicates them, records provider order and atomically replaces the JSON cache.
- The configured TV base URL expands to numbered pages (explicit `{page}` token or a trailing `/N`). Full refresh starts at page 1, stops on an expected end HTTP status after at least one successful page, empty later page, or repeated page content, and has a page safety limit. It deduplicates episodes by media URL and rebuilds show summaries and per-show indexed caches.
- Provider sequence matters. New provider entries are reported to be prepended, pushing older entries to later TV pages (about 2,000 per page in the user's feed). This remains a **provider assumption to validate**, not a guarantee from M3U. The 0.7.13 fast refresh checks a configurable leading page window for a contiguous overlap with the cached provider-order episode feed; when overlap cannot be proven it falls back to the existing full refresh rather than truncating the cache.
- Search runs synchronously over cached movie items and TV show summaries. Version 0.7.13 keeps bounded result sessions and also stores a separate bounded persistent keyword history. Search cancellation explicitly routes to the prior result session or Appi root instead of relying on Kodi failed-directory behavior. Target-device navigation still requires acceptance testing.
- Metadata is separate from the catalogue cache. A focus delay and explicit actions enqueue lookups; TMDb Helper is a declared dependency. Genuine IMDb ratings require TMDb Helper's OMDb ratings source configuration.

## Playback and data ownership

- Playback uses `app.py` for MP4 buffering and three distinct HLS modes: native Kodi handling, Appi-selected fixed rendition, and explicit InputStream Adaptive `adaptive` mode with an optional maximum bitrate ceiling. Manual rendition selection happens before playback is resolved, making Cancel an abort rather than a playback choice.
- As of 0.7.8, Kodi's native video database owns watched state and resume bookmarks. Appi's Recently Played cache records identity/order, not duplicate playback status.
- Favorites, metadata and subtitle data have distinct storage. A catalogue refresh must preserve user data and should not silently clear favorites or Kodi playback status.
- Preferred audio and internal-subtitle labels are normalized and applied once at AV start when a matching Kodi stream is exposed. Per-title subtitle modes and saved external subtitles take precedence over the global internal-subtitle preference.\n- Saved-subtitle capture normally waits for a stable temporary-file fingerprint; playback stop performs a final capture pass so a subtitle downloaded immediately before exit is not lost between polling intervals.\n- Optional diagnostics retain only a bounded number of sanitized sessions and events. They record playback position and available Kodi InfoLabels, exclude raw authenticated URLs/credentials/subtitle contents, and explicitly mark per-segment timing, inputstream buffer level and representation history unavailable when Kodi Python does not expose them.\n- Optional automatic catalogue refresh is serialized by a profile lock, only launched by the service while video is idle, and uses bounded retry backoff after failures.

## Publishing

`python3 tools/build_repository.py` regenerates add-on ZIPs, SHA-256 sidecars, `addons.xml` and its checksum, and the Pages `index.html`. The install page lists the current package plus selected fallback packages; the repository retains other older ZIPs. `repository.appi` reads the repository feed from the raw `main` files. A documentation-only change requires no rebuild or version bump.

