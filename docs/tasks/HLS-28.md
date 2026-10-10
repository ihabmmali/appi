---
id: HLS-28
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-28 — Preserve embedded HLS subtitle tracks in Buffered Look Ahead

## Objective
Ensure Buffered Look Ahead exposes the same provider-supplied HLS subtitle tracks that Kodi exposes for the same stream in the other playback modes.

This is a compatibility/correctness candidate, not an inherent limitation of buffering.

## Target-device evidence
On Appi 0.7.24, the user reports streams with one or more subtitle tracks that are visible in other playback modes show no corresponding stream subtitle tracks when played through Buffered Look Ahead.

This concerns subtitle tracks carried by the provider stream, not externally downloaded subtitle files.

## Current architecture
Buffered Look Ahead already parses and rewrites HLS master-playlist URI attributes.

For `#EXT-X-MEDIA` resources it preserves metadata including:
- rendition type;
- group ID;
- name;
- language;
- default;
- autoselect;

and rewrites the URI to the Appi localhost proxy.

Therefore subtitle groups are not intentionally stripped from the master.

However:
- `_prepare_associated_media()` preloads only AUDIO and VIDEO groups;
- SUBTITLES groups intentionally do not participate in startup readiness;
- modes 1 and 2 hand the original provider master to InputStream Adaptive;
- mode 3 returns Appi's rewritten localhost master and deliberately does not configure InputStream Adaptive.

There is currently no automated coverage proving that provider `TYPE=SUBTITLES` groups remain discoverable/selectable by Kodi after the Buffered Look Ahead master is rewritten.

## Required investigation
Using a master known to expose subtitle tracks in another Appi mode, capture and compare:

1. provider master playlist;
2. Appi rewritten localhost master;
3. referenced subtitle media playlist(s);
4. Kodi-visible subtitle stream list in:
   - Manual / InputStream Adaptive;
   - automatic/adaptive modes where applicable;
   - Buffered Look Ahead.

Verify:
- the selected variant's `SUBTITLES` group reference is retained;
- every referenced `#EXT-X-MEDIA:TYPE=SUBTITLES` entry remains in the rewritten master;
- LANGUAGE, NAME, DEFAULT, AUTOSELECT, FORCED and CHARACTERISTICS attributes are preserved where supplied;
- the local subtitle playlist URI resolves successfully;
- subtitle playlist contents are rewritten correctly;
- WebVTT/fMP4 subtitle segment suffix/content type and byte-range handling remain valid;
- Kodi actually exposes the tracks from the local master.

## Repair constraints
Do not make subtitle renditions part of the mandatory audio/video startup reservoir. Provider subtitles must remain optional and must not delay initial video playback merely because a subtitle track exists.

Repair the proven compatibility boundary.

Possible implementation directions may include:
- correcting master-playlist attribute/URI rewriting;
- correcting subtitle media-playlist proxying/content types;
- lazy preparation of a subtitle rendition when Kodi requests it;
- using InputStream Adaptive for the localhost buffered master **only if** target-device testing proves it preserves Buffered Look Ahead behavior, audio, seeking, pause/resume and fixed selected rendition.

Do not switch mode 3 to ISA merely because modes 1/2 expose subtitles. Prior working Buffered Look Ahead behavior is a preservation constraint.

## Acceptance
- On the same target stream, the subtitle track list visible in Buffered Look Ahead matches the provider-supplied HLS subtitle tracks visible in the working comparison mode, subject only to tracks genuinely unsupported by Kodi itself.
- Multiple subtitle languages remain individually selectable.
- LANGUAGE/NAME labeling is retained where Kodi exposes it.
- Forced/default flags are preserved where supported.
- Selecting an embedded subtitle track works throughout playback.
- Switching embedded subtitle tracks does not reset the Buffered Look Ahead video/audio reservoir.
- Embedded subtitle traffic does not become a required startup/high-water track.
- Seeking and pause/resume do not make the selected subtitle track disappear.
- External/downloaded subtitle support remains independent.
- Modes 0-2 remain unchanged.
- Automated tests cover a master with at least two `TYPE=SUBTITLES` renditions and verify rewritten master/playlist accessibility.
- Fire TV target-device comparison against the same stream in a working non-buffered mode is mandatory.

## Authorization
Reported by the user on 2026-10-04 from target-device testing. The user requested no action only if missing stream subtitles were an inherent buffering limitation. Source review shows they are not intentionally excluded by the buffering architecture. On 2026-10-10 the user explicitly instructed that all current candidates be committed. HLS-28 is committed next-release scope.

## Evidence
0.7.24 source rewrites `EXT-X-MEDIA` URIs generically, including subtitle renditions, but only AUDIO/VIDEO associated groups are proactively prepared and Buffered mode does not use InputStream Adaptive. There is no subtitle-rendition regression coverage for the rewritten localhost master.

## Outcome and next action
Reproduce with a known subtitle-bearing HLS master, compare provider versus rewritten master and Kodi stream discovery, then repair the proven proxy/playback handoff boundary without making subtitles part of the required reservoir.
