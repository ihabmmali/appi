# Appi Kodi Add-on

Appi is a Kodi video add-on that reads user-configured M3U catalogues for movies and TV shows.

## Supported Kodi versions

This project is built against the current stable Kodi 21 Omega API and requires `xbmc.python` 3.0.1 (also present in Kodi 20 Nexus). The repository definition uses Kodi's current `<dir>` repository schema.

## Features

- Movie catalogue from one M3U URL.
- TV catalogue from sequential pages `1..N`, with a configurable page count (default 30).
- TV base URL may be either a base such as `https://example.invalid/m3u8/tvshows` or a template containing `{page}`.
- Persistent local cache. Catalogue data is downloaded only when a cache does not yet exist or when you explicitly refresh it.
- Manual refresh commands for movies, TV shows, or both.
- Simple text search across movie titles and TV episodes/shows.
- Movie year, IMDb-style ID, TV show title, season, and episode are passed into Kodi's video metadata layer.
- Playback passes the provider's original media URL to Kodi, allowing Kodi to follow redirects and handle HLS/MP4 streams itself.
- No `curl`, shell helper, or third-party Python HTTP library is required.
- Provider URLs and credentials are configured in Kodi settings and are not hard-coded in this repository.

## Repository layout

```text
appi/
├── .gitignore
├── .nojekyll
├── README.md
├── addons.xml
├── addons.xml.sha256
├── index.html
├── repository.appi-1.1.0.zip          # bootstrap ZIP linked by GitHub Pages
├── plugin.video.appi/
│   ├── addon.xml
│   ├── default.py
│   ├── plugin.video.appi-0.3.0.zip    # package consumed by Kodi repository
│   ├── plugin.video.appi-0.3.0.zip.sha256
│   └── resources/
│       ├── settings.xml
│       ├── language/resource.language.en_gb/strings.po
│       └── lib/
├── repository.appi/
│   ├── addon.xml
│   ├── repository.appi-1.1.0.zip      # package consumed by Kodi repository
│   └── repository.appi-1.1.0.zip.sha256
├── tests/
└── tools/
    └── build_repository.py
```

The package locations intentionally follow Kodi's repository convention:
`<datadir>/<addon-id>/<addon-id>-<version>.zip`.

The additional root-level `repository.appi-1.1.0.zip` is only the bootstrap package linked from GitHub Pages so Kodi can install the repository in the first place. Published repository packages also receive `.sha256` sidecars so Kodi 21 can verify downloaded ZIPs.

## Build and validate

From the repository root:

```bash
python3 tools/build_repository.py
python3 -m unittest discover -s tests -v
```

Run the build script after changing an add-on version or any packaged file. It automatically rebuilds both add-on ZIPs, `addons.xml`, the SHA-256 index checksum, the root bootstrap repository ZIP, and `index.html`.

## Kodi configuration

After installing Appi, open **Appi → Settings** and configure:

1. **Movie M3U URL** — the complete movie catalogue URL.
2. **TV Show M3U base URL** — for example `https://example.invalid/m3u8/tvshows`; Appi appends `/1`, `/2`, etc. You may instead use a URL containing `{page}`.
3. **TV Show page count** — defaults to `30`.

On first access to Movies, TV Shows, or Search, Appi downloads any missing catalogue. After that it uses the persistent cache until you select one of the refresh commands.

## GitHub hosting

The repository add-on is already configured for:

- GitHub repository: `ihabmmali/appi`
- branch: `main`
- repository metadata/data: `raw.githubusercontent.com`
- bootstrap page: `https://ihabmmali.github.io/appi/`

Enable GitHub Pages for the `main` branch, root (`/`) directory. The generated `index.html` exposes the repository ZIP as a clickable link.
