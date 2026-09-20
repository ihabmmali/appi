# Appi Kodi Add-on

Appi is a Kodi video add-on for user-configured movie and TV-show M3U catalogues.

## Direct install

Add `https://ihabmmali.github.io/appi/` in Kodi File Manager, then install the current `plugin.video.appi-<version>.zip`.

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
