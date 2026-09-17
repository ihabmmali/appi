# Appi Kodi Add-on

Appi is a Kodi video add-on for user-configured movie and TV-show M3U catalogues.

## Direct install

Add this source in Kodi File Manager:

`https://ihabmmali.github.io/appi/`

Then use **Add-ons -> Install from zip file -> Appi** and install the current `plugin.video.appi-<version>.zip`. The Pages source intentionally exposes only the video add-on ZIP; a repository ZIP is not required for this workflow.

## 0.5.0 highlights

- Indexed TV cache: the TV Shows screen loads a compact show index instead of reparsing every episode.
- TV navigation remains **Show -> Season -> Episode**.
- Explicit default sorting in **Appi Settings -> Browsing** by title or year.
- HLS playback can ask for quality before playback or cap maximum bitrate using InputStream Adaptive.
- Plain MP4 playback can apply Kodi's native HTTP file-cache memory/read-factor settings.
- Downloaded external subtitles detected in Kodi's temporary area are copied into Appi profile storage and reused on replay.
- Errors are shown on-screen with the exception type/message, useful on Fire TV where logs are inconvenient.

The M3U feeds remain the catalogue source. Rich metadata such as plots, posters and ratings is intentionally deferred to a later metadata-cache layer.
