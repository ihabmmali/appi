# Appi Kodi Add-on

Appi is a Kodi video add-on for user-configured movie and TV-show M3U catalogues.

## Direct install

Add `https://ihabmmali.github.io/appi/` in Kodi File Manager, then install the current `plugin.video.appi-<version>.zip`.

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

Add the generated `Movies` and `TV Shows` subfolders beneath the configured download folder as Kodi video sources to browse and delete downloads using Kodi's standard library interface.

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
