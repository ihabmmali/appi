# Appi release notes and handoff

This file records the latest published package and gives the next short-lived development session a concise starting point. Historical implemented features are in [CHANGELOG.md](CHANGELOG.md) and [README.md](README.md). An archive in the repo is not automatically a GitHub Releases entry.

## Current package: 0.7.12

- Source commit: [a099e521cfa767bc8cdee9a72988dcd8a92b9c73](https://github.com/ihabmmali/appi/commit/a099e521cfa767bc8cdee9a72988dcd8a92b9c73).
- Package: [plugin.video.appi-0.7.12.zip](https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.12.zip); listed as current on the Pages install index.
- User-confirmed known-good fallback: [0.7.8 package](https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.8.zip).
- Implemented: bounded search-session storage, stable **New Search...**, retention of search results after favorites refresh, and preservation of the 0.7.8 playback path.
- Verification: repository manifest, package index, source and README inspected on 2026-09-24. Device acceptance of the 0.7.12 search behavior is **not yet recorded**. No GitHub Releases entry exists for this package as of this update.
- Outstanding: search navigation device check; fast/automatic refresh; default audio/subtitle language matching; intermittent HLS stalls. See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Release handoff template

Copy this section into a new version entry at each package release and keep the newest entry at the top.

### Version X.Y.Z — YYYY-MM-DD

- Source commit:
- Package and install location:
- Previous user-confirmed fallback:
- Implemented features:
  -
- User-visible fixes:
  -
- Automated checks (commands/results):
  -
- Kodi device checks (version, skin, actions/results):
  -
- Known issues and regressions:
  -
- Architecture/data changes and migration:
  -
- Next iteration:
  -

Update the add-on version, README summary, this file, [CHANGELOG.md](CHANGELOG.md), [PROJECT_STATE.md](PROJECT_STATE.md), and [KNOWN_ISSUES.md](KNOWN_ISSUES.md) as applicable. Build packages and repository metadata with `python3 tools/build_repository.py`; validate before publishing and preserve the 0.7.8 fallback.
