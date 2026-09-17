# Appi Kodi Add-on

Appi is a Kodi video add-on for user-configured movie and TV-show M3U catalogues.

## Install directly from the Kodi file source

Add this source in Kodi File Manager:

`https://ihabmmali.github.io/appi/`

Then use **Add-ons -> Install from zip file -> Appi** and select the current
`plugin.video.appi-<version>.zip` file. The `repository.appi-<version>.zip`
shown beside it is optional and is only needed if you want Kodi repository-based
updates.

## Catalogue behaviour

- Movie catalogue is cached locally until manually refreshed.
- TV catalogue is cached locally until manually refreshed.
- TV navigation is **TV Show -> Season -> Episode**.
- Movie and TV searches are scoped separately so a movie search does not load or
  scan the TV catalogue.
- Playback uses the original provider media URL only at playback time; catalogue
  directory URLs use compact cached references.
- Kodi receives title/year/season/episode/IMDb-style IDs for playback and subtitle
  matching. The M3U feeds do not contain plots, posters, cast or ratings, so Appi
  does not invent those fields.

## Build

```bash
python3 tools/build_repository.py
python3 -m unittest discover -s tests -v
```

The build script creates the plugin package, optional repository package,
SHA-256 files, `addons.xml`, and the GitHub Pages `index.html` used by Kodi's
file-source browser.
