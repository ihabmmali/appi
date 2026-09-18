# Appi Kodi Add-on

Appi is a Kodi video add-on for user-configured movie and TV-show M3U catalogues.

## Direct install

Add `https://ihabmmali.github.io/appi/` in Kodi File Manager, then install the current `plugin.video.appi-<version>.zip`.

## 0.8.0

- Replace static media-result directories with an incrementally loaded Appi `WindowXML` browser whose visible `ListItem` objects can be enriched in place without constructing the entire 20,000-item catalogue at startup.
- Queue the initial viewport automatically and queue each newly exposed viewport while scrolling; network lookups remain serialized and pause during playback.
- Update posters, plots, actor names/roles, directors, episode names and genuine IMDb ratings live without leaving and reopening the folder.
- Require TMDb Helper as a Kodi dependency.
- Add **Download for offline viewing** to the long-press menu for movies and episodes.
- Download direct MP4 and completed, unencrypted HLS media in the background, pause downloads during playback, and write Kodi-compatible filenames and NFO files beneath configurable Movies and TV Shows folders.
- Add **Remove from Recently Played** to individual recent movie and TV-show context menus.
- Keep 0.7.0 and the known-good 0.6.3 release available on the direct-install page.

### Offline library setup

Choose a writable **Download folder** in Appi settings. Appi creates `Movies` and `TV Shows` beneath it. Add those two folders as the corresponding Kodi video sources. Completed downloads trigger a targeted library scan; Kodi can then play and delete the media through its normal library interface. Encrypted or live HLS playlists are rejected rather than saved incompletely.

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
