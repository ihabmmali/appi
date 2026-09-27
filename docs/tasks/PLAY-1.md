---
id: PLAY-1
role: implementation
status: ready
delivery: unreleased
verification: failed
owner: unassigned
base_commit: unset
artifact: none
---
# PLAY-1 — Restore Kodi resume points and investigate playback-start Trakt API error

## Objective
Restore Kodi's ability to remember and resume playback positions for Appi media after the 0.7.18 line, and investigate the Trakt API error that appears at playback start.

The Trakt notification is correlated evidence, not an assumed root cause.

## Observed target-device behavior
On Appi 0.7.18:
- Kodi no longer appears to remember playback/resume points for media;
- a **Trakt API error** notification appears in the top-right corner at the beginning of playback;
- this is reported alongside otherwise playable media, so the regression is not limited to Buffered Look Ahead startup failures.

## Current architecture
`playback_history.py` explicitly records Recently Played identity only; resume and watched state are delegated to Kodi.

`kodi_status.py` reads Kodi's canonical `playcount` and `resume` bookmark using `Files.GetFileDetails` against the Appi plugin playback URL.

Therefore the repair must verify that the logical media item has a stable canonical plugin URL/identity before and after playback, independent of the actual resolved stream/proxy URL.

## Scope
Investigate the end-to-end playback identity and resume path across the current 0.7.18 code line:
- canonical Appi plugin URL used for Kodi resume/playcount storage;
- ListItem/path/resolved URL handling at playback start;
- whether buffered/local-proxy or InputStream Adaptive paths replace or destabilize the identity Kodi associates with the media;
- whether media metadata needed by Kodi/Trakt (title, media type, year, season, episode, IDs where available) is present and stable at playback start;
- stop/end/error lifecycle needed for Kodi to persist the bookmark;
- Resume / Play from beginning behavior when a bookmark exists;
- interactions with Recently Played and Appi's own session tracking;
- the Trakt API notification and whether it comes from Appi, Kodi's Trakt add-on, or malformed/incomplete playback metadata exposed by Appi.

Do not make Appi create a second competing resume database unless evidence proves Kodi-native bookmarks cannot satisfy the requirement.

## Acceptance
- Reproduce the 0.7.18 failure where playback progress is not remembered.
- Record the canonical plugin URL Kodi uses for the item before playback and after stop; it remains stable for the same logical movie/episode.
- Stop an item part-way through, return to Appi, and verify Kodi exposes a non-zero resume bookmark for the same media item.
- Reopening the item offers/uses the remembered resume point according to Kodi/Appi's intended UI behavior.
- **Play from beginning / reset resume** still works without destroying unrelated watched/history state.
- Verify movies and TV episodes separately.
- Verify at least Native Kodi playback and one ISA-dependent mode; verify Buffered Look Ahead separately if HLS-8 is functional enough to test.
- Playback failure/cancel does not incorrectly overwrite a valid prior resume bookmark with zero.
- The top-right Trakt API error is captured with enough diagnostic/log context to identify its originating add-on/component and exact request/error.
- If the Trakt error is caused by Appi metadata or playback identity, fix it and add regression coverage.
- If the Trakt error originates entirely in an external Trakt add-on/provider and Appi is supplying correct metadata/identity, document that boundary rather than masking the error.
- Automated tests cover stable plugin-media identity and resume/watched URL construction where practical.
- Target-device verification confirms resume persistence survives Kodi/Appi navigation and restart.

## Authorization
Reported by the user on 2026-09-27 while testing Appi 0.7.18. This task is recorded as ready planning work but is not committed release scope unless explicitly included under AGENTS.md.

## Evidence
Current `playback_history.py` states: “resume and watched state belong to Kodi.” Current `kodi_status.py` reads those values using Kodi JSON-RPC `Files.GetFileDetails` for a plugin playback URL. The user reports that 0.7.18 no longer appears to retain those resume points and also shows a Trakt API error at playback start.

## Outcome and next action
Trace one failing movie and one failing episode from Appi's canonical plugin URL through Kodi playback start, stop and subsequent `Files.GetFileDetails`, while capturing the Trakt notification source. Repair the first point where stable media identity or bookmark persistence is lost.
