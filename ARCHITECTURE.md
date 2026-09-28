# Appi architecture

Updated for the 0.7.20 release candidate (2026-09-27). Source describes implemented behavior; accepted requirements and decisions describe intended behavior.

## Project goals and binding rules

- Provide responsive Kodi browsing/search/playback of user-configured movie and TV M3U catalogues.
- Preserve native Kodi watched/resume authority and user favorites, metadata and subtitles.
- Preserve provider order where required; a partial refresh must not discard a valid cache on failure/cancellation.
- Keep navigation predictable through search, show/back, cancellation and favorite actions.
- Evaluate playback changes with real evidence and retain the fallback named in PROJECT_STATE.
- Keep experiments, metadata service, external FFmpeg scripts and catalogue refresh scoped to their responsibilities.
- Release commands: `python3 -m unittest discover -s tests`, then `python3 tools/build_repository.py`; inspect packages/hashes/index and record device checks separately.
- Tracker-only edits use `python3 tools/check_workflow.py` and relevant checker tests; no add-on package rebuild is needed.
- **Algorithmic behavior parameters must be settings-backed, not hard-coded tuning constants.** New features and future algorithm changes must expose user-adjustable behavior thresholds/ratios/timeouts in the appropriate settings group, with defaults matching the accepted baseline behavior. True protocol constants and non-tunable safety invariants may remain internal, but a value that tunes algorithm behavior must not be buried in source.

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
| HLS / diagnostics | `resources/lib/app.py`, `resources/lib/hls.py`, `diagnostics.py` | HLS mode configuration, legacy parser utilities, and bounded privacy-safe playback evidence |\n| External downloads | `resources/lib/downloads.py` | Produce scripts for an external FFmpeg watcher |
| Build and distribution | `tools/build_repository.py`, `repository.appi/`, `addons.xml`, `index.html` | Kodi ZIPs, checksums, repository feed and Pages install index |

## Catalogue flow

- The configured movie URL yields one M3U list. Refresh parses movie records, deduplicates them, records provider order and atomically replaces the JSON cache.
- The configured TV base URL expands to numbered pages (explicit `{page}` token or a trailing `/N`). Full refresh starts at page 1, stops on an expected end HTTP status after at least one successful page, empty later page, or repeated page content, and has a page safety limit. It deduplicates episodes by media URL and rebuilds show summaries and per-show indexed caches.
- Provider sequence matters. New provider entries are reported to be prepended, pushing older entries to later TV pages (about 2,000 per page in the user's feed). This remains a **provider assumption to validate**, not a guarantee from M3U. The 0.7.13 fast refresh checks a configurable leading page window for a contiguous overlap with the cached provider-order episode feed; when overlap cannot be proven it falls back to the existing full refresh rather than truncating the cache.
- Search runs synchronously over cached movie items and TV show summaries. Version 0.7.13 keeps bounded result sessions and also stores a separate bounded persistent keyword history. Search cancellation explicitly routes to the prior result session or Appi root instead of relying on Kodi failed-directory behavior. Target-device navigation still requires acceptance testing.
- Metadata is separate from the catalogue cache. A focus delay and explicit actions enqueue lookups; TMDb Helper is a declared dependency. Genuine IMDb ratings require TMDb Helper's OMDb ratings source configuration.

## Playback and data ownership

- Playback uses `app.py` for MP4 buffering and four distinct HLS modes: native Kodi handling, InputStream Adaptive `ask-quality` manual selection, InputStream Adaptive `adaptive` mode with an optional maximum bitrate ceiling, and the isolated Appi Buffered Look Ahead localhost proxy. InputStream Adaptive is a required packaged dependency because modes 1–2 depend on it. In 0.7.15 manual mode deliberately restores the 0.7.12 architecture: Appi keeps the original provider master URL on the ListItem and does not parse/substitute a child rendition before playback; Kodi/InputStream Adaptive owns rendition discovery, selection and child-playlist resolution.
- As of 0.7.8, Kodi's native video database owns watched state and resume bookmarks. Appi's Recently Played cache records identity/order, not duplicate playback status.
- Favorites, metadata and subtitle data have distinct storage. A catalogue refresh must preserve user data and should not silently clear favorites or Kodi playback status.
- Preferred audio and internal-subtitle labels are normalized from the visible settings. Audio preference application is retried for up to 12 seconds, but 0.7.20 requires the exact non-empty audio stream list to remain stable across a service poll boundary before using an index. A second enumeration immediately precedes any switch; No preference performs no audio mutation; a stable no-match leaves Kodi's current stream untouched; and a best-effort JSON-RPC current-stream check avoids a redundant `setAudioStream()` call when the preferred stream is already active. Per-title subtitle modes and saved external subtitles take precedence over the global internal-subtitle preference.\n- Saved-subtitle capture normally waits for a stable temporary-file fingerprint; playback stop performs a final capture pass so a subtitle downloaded immediately before exit is not lost between polling intervals.\n- Optional diagnostics retain only a bounded number of sanitized sessions and events. Schema 2 records playback position, stall intervals, resolution/bitrate transitions and Kodi Player.Cache* InfoLabels when exposed, excludes raw authenticated URLs/credentials/subtitle contents, and explicitly records unsupported per-segment timing and exact InputStream Adaptive queue/representation internals rather than inferring them.\n- Optional automatic catalogue refresh is serialized by a profile lock, only launched by the service while video is idle, and uses bounded retry backoff after failures.

## Publishing

`python3 tools/build_repository.py` regenerates add-on ZIPs, SHA-256 sidecars, `addons.xml` and its checksum, and the Pages `index.html`. The install page lists the current package plus selected fallback packages; the repository retains other older ZIPs. `repository.appi` reads the repository feed from the raw `main` files. A documentation-only change requires no rebuild or version bump.


## Buffered Look Ahead — 0.7.21

Mode 3 alone uses `buffered_hls.py`. The plugin creates a unique request mailbox and displays cancellable preparation progress; the persistent service prepares the selected stream on a background thread before resolving Kodi playback. Kodi receives a filtered localhost master retaining associated rendition groups, media extensions, byte ranges and authenticated upstream semantics. Modes 0–2 keep their existing provider URL and InputStream Adaptive configuration paths.

The configured storage budget remains 32–1024 MiB (UI label MB), default 128. It is now a shared producer/consumer reservoir rather than an equal per-track allocation. In the published 0.7.21 baseline, startup targets 50% of configured bytes, high-water is 80%, low-water is 60% and critical reserve is 15%. HLS-18 plans to expose these and the other behavior-affecting Buffered Look Ahead tuning thresholds as settings while retaining the 0.7.21 values as defaults. A short VOD may become ready once every remaining required media segment is cached even when it cannot physically fill the byte target. Video and associated/default audio advance toward a common playable horizon; a required track more than 24 seconds ahead of the least-ready track pauses so low-bitrate audio cannot monopolize storage while high-bitrate video is starved. After handoff, prefetch runs toward high-water, pauses there, and resumes at low-water. Consumed/remote windows remain evictable while in-use paths are pinned.

Per-transfer file safety and session-capacity admission are separate. A media file is bounded to 8 MiB or one quarter of configured capacity, capped at 32 MiB, while only a 2–4 MiB admission allowance is reserved before network I/O. This prevents worst-case file ceilings from artificially reducing the reachable reservoir. Completed media is published only while the active epoch still owns the transfer; stale completions are discarded. The session enforces the configured disk ceiling after publication and keeps duplicate requests coordinated per resource.

Initial handoff no longer depends on the legacy 12-second readiness gate. The startup reservoir has a 180-second bounded preparation deadline and the plugin/service mailbox has a 210-second control window, allowing intentionally deeper configured buffers time to fill. The visible progress message is based on actual contiguous playable bytes and reports values such as `Filling buffer — 42.6 MB / 64.0 MB`. Reported bytes include only media usable across the common required-track horizon, not stale files or arbitrary disk usage.

Every discontinuous request creates a new authoritative buffer epoch. The request's playlist-relative timeline is mapped onto each required track, prior track cursors are replaced, in-flight old-epoch work becomes cancellable/stale, and the exact requested media is prioritized. A fresh target reserve is then built before the request is released; the target is derived from about 12 seconds at the selected advertised bitrate, with a 4 MiB floor and bounds from the configured reservoir. If the VOD remainder is smaller, fully caching the remainder also satisfies readiness. Repeated seeks advance the epoch again, so only the newest target can publish state. A stale completion or stale HTTP request cannot mutate the active epoch.

Media `urlopen` timeout is now an inactivity/no-progress bound (15 seconds), not a total-transfer wall-clock deadline. A transfer that continues yielding bytes may exceed 15 seconds overall. Session/epoch cancellation remains checked between reads, while startup and target-reserve preparation retain explicit overall deadlines. Measured segment transfer throughput is aggregated for diagnostics; no automatic quality downgrade is performed. If sustained provider throughput stays below selected-rendition consumption long enough to drain finite reserve, Appi reports depletion rather than claiming buffering can defeat the throughput deficit.

The normal recovery display and the optional detailed debug overlay both consume the same active-epoch reserve metrics. The detailed overlay no longer injects a label into fullscreen window 12005; it uses a modeless `xbmcgui.WindowDialog`, with guarded creation/show/update/close operations so GUI failure remains non-fatal. Detailed text includes playable bytes/target, seconds ahead, water state, epoch and, when known, selected bitrate and measured provider throughput. The service exports the same watermarks and epoch fields to sanitized diagnostics.

## Settings parser safety — 0.7.18

Kodi's native string-option parser expects a text child in every static option. No preference therefore uses the non-empty `none` sentinel (normalized to no preference in Python), never an empty XML option. Source/ZIP checks validate option text and listed defaults. The 0.7.17 empty options are retained only in the archived regression fixture; that release failed startup acceptance.
