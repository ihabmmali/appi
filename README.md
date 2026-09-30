# Appi Kodi Add-on

Appi is a Kodi video add-on for user-configured movie and TV-show M3U catalogues.

## Project documentation

- [Development lifecycle](LIFECYCLE.md) — roles, task states, ownership and evidence rules.
- [Next release](NEXT_RELEASE.md) — candidate scope and planning guide.
- [Record templates](docs/workflows/TEMPLATES.md) — task/experiment/decision formats and session starters.
- [Worker instructions](AGENTS.md) — stable development and release rules.
- [Project state](PROJECT_STATE.md) — current baseline and next session handoff.
- [Architecture](ARCHITECTURE.md) — source map and behavior contracts.
- [Known issues](KNOWN_ISSUES.md) — observed problems and planned work.
- [Changelog](CHANGELOG.md) — concise implemented feature history.
- [Release notes](RELEASE_NOTES.md) — package summaries and verification records.

## Direct install

Add `https://ihabmmali.github.io/appi/` in Kodi File Manager, then install the current `plugin.video.appi-<version>.zip`.

## 0.7.24 candidate — 2026-09-30

- Buffered Look Ahead treats Kodi-side localhost write timeout/disconnect during pause/resume as a consumer-request ending rather than a provider/session failure, retaining the buffered session for the next request.
- Duplicate/current, same-resource Range, recent re-read and adjacent resume requests remain in the active epoch; real forward/backward discontinuities and cold non-zero starts still use fresh seek epochs.
- The detailed buffer setting is re-read from current Kodi settings in the persistent service so OFF is authoritative. The accepted Back-to-dismiss behavior is preserved when the display is intentionally ON.
- Optional runtime metadata is applied using Kodi's native duration field when available, and season folders show locally available episode counts.
- Candidate run `36763427233` passed 108 tests (1 skipped), workflow validation, deterministic rebuild and package/index inspection. Target Fire TV acceptance remains separately required.

## 0.7.23 — 2026-09-29

- Buffered Look Ahead now releases an exact sequential segment as soon as recovery successfully caches it instead of holding Kodi behind the larger recovery-reserve rebuild. Background look-ahead refill continues; seek and cold-resume epochs retain their deliberate reserve gate.
- The producer can fetch a small bounded number of future segments concurrently (default 2 per track, configurable 1–4) while preserving duplicate suppression, stale-epoch cancellation and contiguous playable-order accounting.
- The detailed buffer overlay setting is now a true master switch. OFF is silent; ON renders four bounded telemetry lines instead of an overflowing single line.
- Existing HLS modes 0–2 and the established reservoir watermarks remain unchanged.
- Final candidate run `36661752457` passed 103 unit/smoke tests (1 skipped), workflow validation, deterministic rebuild and package/index inspection. Fire TV/provider acceptance remains separately required.

## 0.7.22 — 2026-09-28

- Buffered Look Ahead now retries transient depleted-segment/provider failures inside Appi under configurable bounds instead of making Kodi's retry behavior the primary recovery mechanism. Pause/buffering/stopped lifecycle states are separated so long pauses are retained by default.
- Advanced mode-3 settings expose reservoir thresholds, transfer/startup/recovery timeouts, seek/recovery reserve, prefetch lead and retry policy; defaults retain the healthy 0.7.21 behavior.
- Startup/handoff diagnostics now distinguish current playable data, startup target and capacity; record reservoir-ready through AV start; and retain a rolling per-track/segment failure timeline. The detailed overlay uses a bundled WindowXMLDialog target with a logged fallback.
- About displays the runtime installed version directly. The approved icon is byte-identical but referenced through a new resource path to bypass Kodi's cached old texture.
- Generated FFmpeg download scripts now use explicit first-video/first-audio mapping, `-c copy` and `-threads 0` while preserving safe partial-file handling.
- Existing HLS modes 0–2 are unchanged. Automated candidate testing passed 100 tests (1 skipped); Fire TV/provider acceptance remains separately required.

## 0.7.21 — 2026-09-28

- Buffered Look Ahead now uses the configured storage as a real rolling reservoir: startup fills a meaningful byte target, video and audio share capacity dynamically, and continuous high/low-water refill protects the selected rendition from intermittent provider stalls when average provider throughput is sufficient.
- Forward/backward seeks and saved non-zero starts create a fresh playback epoch at the requested timeline. Older in-flight work cannot publish into the new epoch, and required tracks rebuild a contiguous target reserve before playback continues.
- The normal preparation/recovery UI shows actual playable KB/MB instead of only a percentage. The optional detailed overlay uses a skin-independent Kodi dialog and adds seconds ahead, water state, epoch, selected bitrate and measured provider throughput.
- Slow transfers that continue making progress are no longer killed by a total 10-second wall-clock deadline. A bounded inactivity timeout still terminates genuinely stalled requests.
- Existing playback modes 0–2 are unchanged. Final candidate run `36381180991` passed 94 tests (1 skipped), workflow validation and deterministic package inspection; target Fire TV/provider acceptance remains required.

## 0.7.20 — 2026-09-27

- Preferred-audio application now waits for a stable Kodi/ISA stream enumeration, rechecks it before using an index, leaves No preference/no-match playback untouched, and avoids redundant switching when Kodi already has the requested language selected.
- Buffered Look Ahead now coordinates forward/backward seeks and cold saved-point starts across video/audio tracks, immediately prioritizes the requested segment, and keeps bounded recovery timeouts retriable instead of tearing down the whole session.
- Generic buffered failures no longer advise lowering quality without evidence that quality/throughput is causal.
- The detailed overlay keeps the existing fullscreen-window target but now logs the exact Kodi GUI operation if creation, update or teardown fails.
- Modes 0–2 retain their existing playback handoff. Automated candidate run `36375784976` passed; target Fire TV acceptance remains required.

## 0.7.19 — 2026-09-27

- Buffered Look Ahead now gates handoff on a real contiguous startup reserve for the selected video plus its associated default audio track, with progress based on the least-ready required track.
- Independent buffered tracks can fetch concurrently under a reserved disk budget, preventing one stalled request from blocking all prefetch work; preparation and control-response deadlines are separated so a late service result cannot race the plugin timeout.
- Preferred audio/subtitle choices retry briefly after AV start until Kodi exposes its stream list, while external/per-title subtitle behavior retains precedence.
- InputStream Adaptive is a required installation dependency, and the latest flat/low-color Appi artwork is packaged unchanged.
- Existing HLS modes 0–2 are intentionally unchanged. Target Fire TV/provider acceptance remains required for Buffered Look Ahead and language selection.

## 0.7.18 — 2026-09-27

- Fix the 0.7.17 Kodi startup crash trigger: the No preference language options now have a non-empty `none` value, avoiding a null text child in Kodi's native settings parser.
- Preserve legacy language preferences and explicit No preference, including recovery from empty 0.7.17 values. Playback code is unchanged.
- Add checks against the actual archived 0.7.17 settings and validate every list option/default in both source and ZIP. Target Fire TV recovery still needs confirmation.

## 0.7.17

- Repair Buffered Look Ahead startup, seek recovery and session replacement. Startup has a visible cancelable progress dialog; failures are bounded and explicit. Existing playback modes 0–2 remain unchanged.
- Add a 32–1024 MB buffered storage setting (128 MB default), Highest available bitrate / Prompt for quality, simple buffering feedback and an optional live MB/seconds overlay.
- Replace preferred audio/subtitle text fields with common-language lists, migrate old aliases, add About with the installed runtime version, and package the approved Appi icon.
- Fire TV/provider acceptance remains pending. Keep 0.7.12 as the usable fallback.

## 0.7.16

- Add **Buffered Look Ahead Playback** as a fourth HLS choice. It runs through Appi's isolated localhost HLS proxy, stores prefetched media in Kodi's temporary storage and targets about 30 seconds of playable media ahead of Kodi.
- Wait for about 18 seconds of startup reserve before releasing the selected media playlist; after depletion, rebuild a larger reserve rather than resuming as soon as only one segment arrives.
- Proxy HLS variants, audio/subtitle rendition playlists, encryption keys and initialization maps while preserving discontinuities and stream metadata. Media is passed through unchanged; Appi does not transcode or re-encode it.
- Keep the three 0.7.15 modes functionally unchanged: Native Kodi remains truly native, manual quality remains InputStream Adaptive `ask-quality` on the original master URL, and adaptive bitrate remains InputStream Adaptive `adaptive` with its optional ceiling.
- Add buffered-path diagnostics for actual segment download latency/throughput, buffered seconds, queued/downloaded segment counts, depletion/recovery and selected representation.
- Automated verification covers the four playback branches and deterministic proxy behavior. Real Fire TV/provider testing remains required to establish whether the deeper buffer removes the intermittent stalls.

## 0.7.15

- Restore manual HLS selection to the working 0.7.12 mechanism after the Appi-side chooser introduced in 0.7.13 remained broken in 0.7.14.
- Keep the original HLS master URL intact and let InputStream Adaptive display/select the rendition through `ask-quality`; Appi no longer resolves and substitutes a child playlist for manual mode.
- Preserve Native Kodi automatic and Adaptive bitrate modes plus the current diagnostics/subtitle/history behavior.
- Keep 0.7.12 directly available until 0.7.15 is confirmed on the target Fire TV/provider stream.

## 0.7.14

- Repair manual fixed-quality HLS child-URL resolution so same-origin relative renditions inherit an authenticated master URL query when the child supplies no query, while preserving Kodi URL request options.
- Show manual rendition labels from the same EXT-X-STREAM-INF entry that supplies the played URL, including resolution, average/peak bandwidth and codecs.
- Upgrade playback diagnostics to schema 2 with explicit stall start/end intervals, sampled Kodi cache/read-ahead InfoLabels where exposed, resolution/bitrate representation transitions, bounded pre-stall history and causal classifications.
- Keep unavailable evidence explicit: supported Kodi add-on Python does not reliably expose InputStream Adaptive per-segment HTTP timings, exact internal queue depth or every internal ABR decision, so the bundle does not fabricate those measurements.
- Preserve 0.7.12 as the usable playback fallback until 0.7.14 manual HLS behavior is accepted on the target Fire TV/provider stream.

## 0.7.13

- Stabilize Search cancellation/context and keep results stable across back/favorite refreshes; add a persistent bounded keyword history with reuse, edit, delete and clear actions.
- Finalize newly downloaded subtitle capture when playback stops so an immediate exit cannot discard a subtitle that the periodic poller has only observed once.
- Add leading-window TV fast refresh using contiguous cached overlap, provider-order preservation and automatic full-refresh fallback; add optional idle-only startup/scheduled refresh with locking and failure backoff.
- Add normalized preferred audio and internal-subtitle language matching, while retaining per-title subtitle overrides and saved external subtitles.
- Add opt-in bounded playback diagnostics with sanitized ZIP-exportable session summaries and explicit reporting of unavailable Kodi metrics.
- Separate HLS behavior into Native Kodi automatic, Manual fixed quality, and explicit InputStream Adaptive ABR. Manual quality is selected before playback so Cancel aborts cleanly; ABR supports an optional maximum bitrate ceiling.
- Automated verification covers unit/smoke tests, tracker validation, package layout, SHA-256 sidecars, repository metadata/index and preservation of the 0.7.8 fallback. Device checks for Kodi navigation, subtitle restore and runtime ABR switching remain pending.

## 0.7.12

- Preserve the active search query in a bounded search-session cache so returning from a TV show reconstructs the same results instead of reopening the keyboard.
- Keep the same results visible after adding or removing an Appi Favorite and Kodi refreshes the container.
- Add a stable **New Search...** entry; cancelling it returns to the previous results rather than leaving a blank directory.
- Preserve the complete 0.7.8 HLS and playback implementation without modification.

## 0.7.11

- Restore the synchronous search path used by the known-good 0.7.8 release so matching cached movies and TV shows are returned directly.
- Remove the unreliable asynchronous prompt-to-results `Container.Update` handoff introduced in 0.7.9 and modified in 0.7.10.
- Retain the configurable automatic next episode, season-level native watched action, and Favorites-first context ordering added after 0.7.8.
- Preserve the complete 0.7.8 HLS and playback implementation without modification.

## 0.7.10

- Fix Search returning to the add-on main menu after category and search-term entry.
- Finish the prompt directory successfully before navigating to the stable search-results route.
- Preserve the complete 0.7.8 HLS and playback implementation without modification.

## 0.7.9

- Keep search results open after Appi Favorite actions and make the results-folder parent reopen the search-term prompt.
- Put Appi Favorite actions first among Appi's custom context actions.
- Add a season-folder action that marks every episode watched through Kodi's native playback-status database.
- Replace the repetitive next-episode prompt with a persistent automatic-next-episode setting.
- Preserve the complete 0.7.8 HLS and playback implementation without modification.

## 0.7.8

- Make Kodi's video database the sole authority for watched state and resume bookmarks.
- Remove Appi's duplicate watched/unwatched, resume, play-from-beginning and reset-resume controls and prompts.
- Reset the superseded Appi playback-status cache without migrating it; Recently Played begins clean and continues storing identity/order only.
- Preserve watched-aware recent-TV progression by reading the relevant episode status from Kodi rather than copying it into Appi storage.
- Limit the GitHub Pages install index to the current release and three prior releases while retaining older packages in GitHub.

## 0.7.7

- Replace Kodi's conflicting resume handling with an Appi-controlled Resume / Play from beginning choice and a working reset-resume action.
- Add Appi watched/unwatched state, watched-aware recent TV progression, and configurable Stop / Ask / Automatic next-episode playback.
- Add separate Favorite Movies and Favorite TV Shows folders whose entries resolve against the current catalogue and metadata cache.
- Remove the synthetic `dateadded` timestamps that overflowed to 1963 on affected devices while preserving provider-list order.
- Validate non-episode IMDb identities and refresh seven-day-old cached IMDb ratings asynchronously when an item is focused.
- Remove the media-server output-root setting. Generated FFmpeg scripts now write their MP4 beside the script itself using stream copy.
- Keep 0.7.6 and earlier packages directly available as fallbacks.

## 0.7.6

- Replace all device-side media downloading and TS muxing with atomic POSIX shell scripts for an external FFmpeg watcher.
- Use Kodi's native path selector and VFS layer for local, SMB, NFS and other writable sources supported by the installed Kodi build.
- Pass the original media URL to FFmpeg and use automatic stream selection with `-c copy`, producing one MP4 without re-encoding or playback-speed throttling.
- Add a separate media-server output-root setting because the server's filesystem path may differ from Kodi's script-watch path.
- Expand metadata status with worker state, queue age, success/failure totals, last activity, pinned retention and disk usage.
- Make metadata pausing during playback configurable and disable repetitive bulk-queue confirmations by default.
- Fetch directors and place IMDb rating, director and a concise cast list above the plot in standard Kodi browse descriptions.
- Keep 0.7.5 and earlier working packages directly available as fallbacks.

## 0.7.5

- Keep both **Fetch metadata for all Recently Played...** actions on their home-screen folders and prevent Kodi from reusing stale cached root-menu items after an upgrade.
- Select the highest advertised HLS video rendition for downloads and stream-copy separate MPEG-TS video/audio renditions into one playable `.ts` file without re-encoding.
- Add **Manage Downloads** with individual stop-and-keep-partial, resume, cancel-and-delete-partial, retry, and delete-completed-file controls.
- Keep 0.7.4 and the earlier stable packages available as fallbacks.

## 0.7.4

- Expose **Fetch metadata for all Recently Played...** from within both recent-media lists as well as on their home-screen folders.
- Give recent TV shows separate batch actions for the selected show and for every recently played show.
- Download completed, unencrypted HLS programmes that use separate video and audio renditions as a local offline HLS bundle.
- Surface the offline bundle through a Kodi-library-compatible STRM file and remove orphaned bundle data after that STRM file is deleted.
- Keep the existing direct MP4 and single-track HLS download paths unchanged.

## 0.7.3

- Add **Stop and Clear Metadata Queue** without deleting metadata already fetched.
- Show the metadata database disk usage in **Metadata Status**.
- Add folder-level batch metadata retrieval to both Recently Played folders.
- Add **Remove from Recently Played** to movie, TV-show and recent continuation-item context menus.
- Keep 0.7.2 directly available as the previous working release.

## 0.7.2

- Repackage the 0.7.1 feature set under a fresh URL after Kodi received an invalid cached 0.7.1 package from the web source.
- Declare TMDb Helper as a required dependency with an explicit minimum version.

## 0.7.1

- Restore the stable standard Kodi directory browser from 0.7.0; the experimental 0.8 WindowXML browser is not used.
- Add **Download for offline viewing** to movie and episode context menus.
- Download direct MP4 streams and compatible completed, unencrypted HLS streams in the background, yielding whenever playback starts.
- Write Kodi-compatible movie/episode NFO files and scan completed downloads into the standard Kodi library.
- Add explicit folder, TV-show and season metadata batch actions. Network lookups remain sequential and pause during playback and downloads.
- Store shared TV-show poster, cast and identifiers once per show; episode rows contain only episode title, plot and episode-specific ratings.
- Retain explicitly requested batch metadata while continuing to bound metadata discovered through ordinary item focus.

In releases 0.7.1 through 0.7.5, downloaded `Movies` and `TV Shows` subfolders could be added as Kodi video sources. Versions 0.7.6 and later delegate file creation and library integration to the external watcher.

## 0.7.0

- Fetch plot, poster, cast and episode names in the background for a title that remains focused for three seconds.
- Reuse TMDb Helper through Kodi's public plugin interface; metadata fetching never scans the full catalogue.
- Cache at most 1,000 enriched titles by default in a small SQLite database, configurable from Settings.
- Populate Kodi list and playback information with cached metadata, including genuine IMDb ratings when TMDb Helper's OMDb ratings source is configured.
- Add a per-item **Fetch / refresh metadata** action plus metadata status and clear-cache controls.
- Keep 0.6.3 available as the known-good fallback package and branch.

## 0.6.3

- Preserve original provider order in All Movies and All TV Shows.
- Add native Date added, title and year sorting while keeping the year visible beside titles.
- Keep the current search category dialog and make Movies and TV Shows the first/default choice.
- Move catalogue refresh commands from the home screen into Settings.
- Add confirmed Settings actions to clear either or both catalogue caches, saved subtitles, and recent/resume history.
- Retain indexed A-Z/year browsing and automatic TV catalogue page discovery.
- Retain long-hold playback options, Recently Played/resume support, MP4 buffering controls and persistent subtitles.

