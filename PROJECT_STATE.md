# Appi project state

Updated: 2026-09-24. Read this first in each new development session. The repository and `plugin.video.appi/addon.xml` are authoritative if this snapshot becomes stale.

## Current baseline

- Default branch: `main`; add-on source: `plugin.video.appi/`.
- Current packaged version: **0.7.12** (source manifest and GitHub Pages index). This identifies what is published, not a claim that all behavior has been verified on a device.
- User-confirmed known-good fallback: **0.7.8**, especially for playback. Keep `plugin.video.appi-0.7.8.zip` available and do not alter that archive when making a new release.
- The repository contains an experimental 0.8.0 ZIP/branch, but `main` currently packages 0.7.12 and uses Kodi's standard directory browser.
- Install page: https://ihabmmali.github.io/appi/ ; source: https://github.com/ihabmmali/appi.
- There are no GitHub Releases entries as of this update. Packages, the Pages index and the README are the existing distribution and historical summary.

## Product and implementation

Appi browses user-configured M3U movie and numbered TV episode catalogues, indexes shows and seasons, searches cached titles, plays HLS/MP4, manages favorites/recent items/subtitles, and queues background metadata. Kodi's native video database owns watched and resume status. Current downloads generate external FFmpeg watcher scripts; earlier 0.7.1–0.7.5 device-side download behavior is historical.

See [ARCHITECTURE.md](ARCHITECTURE.md) for code and data flows, [CHANGELOG.md](CHANGELOG.md) for implemented changes, [RELEASE_NOTES.md](RELEASE_NOTES.md) for the latest package's release record, and [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for observed problems and pending work.

## Current priorities

1. Reproduce and verify 0.7.12 search/back/cancel/favorites navigation on the target Kodi skin/device; prior search releases had regressions. Record actual test results before marking fixed.
2. Design and implement an optional fast refresh for prepend-only provider catalogues: compare a configurable leading window with cached records, preserve order and deduplication, and fall back to full refresh when assumptions or overlap checks fail. The current code still fetches all numbered TV pages until an end condition; movies fetch their single M3U.
3. Add default audio and subtitle language preferences with normalized matching of labels/codes (e.g. `eng` ↔ `English`), plus defined fallback behavior. These settings are absent from the current manifest.
4. Investigate particular HLS URLs that repeatedly stall despite buffering, without changing the known-good playback path speculatively.

These are requests or investigations, **not released features**. Consult [KNOWN_ISSUES.md](KNOWN_ISSUES.md) before choosing an iteration.

## Working and release rule

For each focused task, start from the current `main` commit, read this state, the relevant issues and source, then record the result in the appropriate tracker. Update the state and issue files only when evidence changes. For a release, update source and tests, increment `addon.xml`, add release notes and a changelog entry, run `python3 -m unittest discover -s tests` and `python3 tools/build_repository.py`, inspect generated ZIP and index, test in Kodi where possible, then publish the source and generated artifacts together. Keep 0.7.8 available. Record the commit and any device verification in [RELEASE_NOTES.md](RELEASE_NOTES.md); do not equate automated tests with device validation.
