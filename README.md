# Appi Kodi Add-on

Appi is a Kodi video add-on for user-configured movie and TV-show M3U catalogues.

## Direct install

Add `https://ihabmmali.github.io/appi/` in Kodi File Manager, then install the current `plugin.video.appi-<version>.zip`.

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
