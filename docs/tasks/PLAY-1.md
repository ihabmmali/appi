---
id: PLAY-1
role: research
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# PLAY-1 — Investigate playback-start Trakt API error

## Objective
Investigate the Trakt API error notification that appears at playback start on Appi 0.7.18.

The previously suspected Kodi resume-point regression is withdrawn: after allowing playback to run longer, the user confirmed Kodi does remember the resume point. Do not treat resume persistence as broken without new evidence.

## Observed target-device behavior
On Appi 0.7.18 a **Trakt API error** notification appears in the top-right corner at the beginning of playback. Kodi resume points were initially suspected to be broken, but subsequent testing showed resume works once the media has played long enough.

## Current architecture
`playback_history.py` explicitly records Recently Played identity only; resume and watched state are delegated to Kodi.

`kodi_status.py` reads Kodi's canonical `playcount` and `resume` bookmark using `Files.GetFileDetails` against the Appi plugin playback URL.

Therefore the repair must verify that the logical media item has a stable canonical plugin URL/identity before and after playback, independent of the actual resolved stream/proxy URL.

## Scope
Investigate the playback-start Trakt error across the current 0.7.18 code line:
- the Trakt API notification and its originating add-on/component;
- playback metadata exposed by Appi at playback start, including title, media type, year, season, episode and IDs where available;
- whether the canonical plugin URL / resolved URL presentation causes an external Trakt add-on to misidentify the item;
- whether the error occurs across Native Kodi, InputStream Adaptive and Buffered Look Ahead;
- exact Kodi/Trakt log message, request context and response/error when available.

Do not make Appi create a second competing resume database unless evidence proves Kodi-native bookmarks cannot satisfy the requirement.

## Acceptance
- Reproduce the top-right Trakt API error on 0.7.18.
- Capture enough diagnostic/log context to identify its originating add-on/component and exact request/error.
- Verify movies and TV episodes separately.
- Verify at least Native Kodi playback and one ISA-dependent mode; verify Buffered Look Ahead separately if HLS-8 is functional enough to test.
- Confirm Kodi resume points continue to work after sufficient playback time; do not alter resume handling unless new reproducible evidence shows a defect.
- If the Trakt error is caused by Appi metadata or playback identity, fix it and add regression coverage.
- If the Trakt error originates entirely in an external Trakt add-on/provider and Appi is supplying correct metadata/identity, document that boundary rather than masking the error.
- Automated tests cover stable plugin-media identity and resume/watched URL construction where practical.
- Target-device verification confirms resume persistence survives Kodi/Appi navigation and restart.

## Authorization
Reported by the user on 2026-09-27 while testing Appi 0.7.18. The user subsequently confirmed resume-point persistence works after sufficient playback time. The remaining Trakt investigation is not committed release scope.

## Evidence
Current `playback_history.py` states that resume and watched state belong to Kodi. The user initially suspected resume loss, then confirmed Kodi remembers the resume point after the video has played long enough. The remaining observed issue is the Trakt API error shown at playback start.

## Outcome and next action
Do not change resume-point logic based on the withdrawn report. Capture and identify the Trakt error source in a separate investigation.
