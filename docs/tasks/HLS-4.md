---
id: HLS-4
role: review
status: review
delivery: unreleased
verification: partial
owner: ChatGPT release worker 2026-09-26
base_commit: 90b9561481a14d04765b0bd999ee47ddf232e6c5
artifact: none
---
# HLS-4 — Repair 0.7.13 manual HLS playback regression

## Objective
Restore working manual/fixed HLS rendition playback after the 0.7.13 regression.

On the user's target device, the new 0.7.13 manual fixed-rate selector is not usable:
- the rendition-selection menu displays incorrect resolution/stream information;
- selecting any listed rendition results in a playback failure error;
- the user reverted to 0.7.12 because 0.7.13 playback is effectively broken for this workflow.

The expected behavior is that the manual chooser accurately describes the variants in the HLS master playlist and that selecting any valid listed rendition resolves and plays that exact stream successfully.

## Scope
Investigate the 0.7.13 manual HLS implementation introduced as part of HLS-2/HLS-3, with emphasis on master-playlist parsing, rendition metadata mapping, variant URL resolution and the final Kodi playback path.

Compare the 0.7.13 implementation against 0.7.12's working playback path and the provider's actual HLS master/variant structure. Do not preserve a new abstraction merely because automated tests pass; preserve the 0.7.12 behavior where it is the known working reference.

Check at minimum:
- whether resolution, BANDWIDTH/AVERAGE-BANDWIDTH, codec and variant URI are being associated with the correct `#EXT-X-STREAM-INF` entry;
- whether relative and absolute variant URIs are resolved correctly against the master playlist URL;
- whether signed/query-bearing master URLs require query/auth propagation when resolving a variant;
- whether selected variants are passed to Kodi with the correct MIME/content-lookup/InputStream properties;
- whether Appi is accidentally passing a malformed, sanitized, stale or otherwise non-playable variant URL;
- whether manual-mode changes interact incorrectly with diagnostics, subtitles, playback history or InputStream Adaptive.

This repair is distinct from [HLS-3](HLS-3.md), which owns Cancel semantics, and [HLS-2](HLS-2.md), which owns ABR/mode semantics. HLS-4 owns the 0.7.13 regression where displayed rendition information is wrong and selecting a rendition fails playback.

## Acceptance
- Reproduce the 0.7.13 failure on a target-device/provider stream that offers multiple HLS variants.
- Compare the same media item under 0.7.12 and record the working baseline behavior.
- The manual chooser displays the correct resolution and advertised bitrate/bandwidth for every presented variant.
- Codec/stream metadata shown by Appi corresponds to the same variant URL that will actually be played.
- Selecting each valid listed rendition resolves to a playable URL and starts playback without an Appi/Kodi playback-failure error.
- Relative, absolute and query/signed variant URL handling is verified against representative master playlists used by the provider.
- Selecting one rendition does not silently play a different rendition.
- Cancel behavior continues to satisfy HLS-3.
- Automatic/native and adaptive modes are regression-tested so the manual-playback repair does not break them.
- Diagnostics, subtitle-session setup and Recently Played do not corrupt or replace the selected variant URL.
- Add automated parser/URL-resolution coverage based on a sanitized fixture matching the failing manifest structure, plus target-device verification.
- Do not declare the repair complete until a real 0.7.13-derived build plays a manually selected rendition successfully on the user's target device.

## Authorization
Reported by the user on 2026-09-26 as a blocking regression in released Appi 0.7.13. The user reported incorrect manual rendition information and playback failure for every available manual selection, and reverted to 0.7.12 to restore usable playback. This task is ready for a separate implementation assignment; publication remains separately authorized by the release lifecycle.

## Evidence
User device evidence on 2026-09-26:
- 0.7.13 manual fixed-rate selection displays incorrect resolution/stream information.
- Selecting any available stream results in a playback failure error.
- The user reverted to 0.7.12 because 0.7.13 playback is effectively broken for this use case.

The 0.7.13 HLS-2/HLS-3 review record states that automated smoke tests covered master-playlist parsing and selection, but target-device playback verification was still pending. This report is therefore a failed target-device acceptance result and demonstrates that the existing automated fixture did not represent the failing provider/runtime path adequately.

## Build session — 2026-09-26
- Assigned under the user's explicit build/integrate/publish instruction; NEXT_RELEASE lists HLS-4 as committed release-blocking scope.
- Working base: `90b9561481a14d04765b0bd999ee47ddf232e6c5`; task branch: `release/0.7.14-hls4-diag2`.
- Initial source inspection identified a concrete regression risk in 0.7.13 manual mode: Python `urljoin()` resolves a relative child URI but does not inherit a signed/query-bearing master URL's query string, unlike passing the working master URL to Kodi as in 0.7.12. The repair will preserve query/auth material for same-origin relative variants and retain Kodi URL options.
- Target-device acceptance remains required after publishing a 0.7.13-derived repair build.

## Implementation evidence — 2026-09-26
- Manual rendition resolution now preserves the exact master query for same-origin relative child URIs when the child has no query, and carries Kodi URL request options across resolution.
- EXT-X-STREAM-INF parsing retains peak and average bandwidth separately, resolution and codecs, and the chooser label is generated from the same variant object whose URL is played.
- Appi passes sanitized selected-variant identity/metadata into diagnostics without exporting the authenticated URL.
- Added regression tests for signed relative variants, child-query precedence, cross-origin isolation, Kodi URL options and metadata/URL association.
- GitHub Actions PR run 36290602785 passed the unit/smoke suite, tracker validation, deterministic build, ZIP/hash/index inspection and fallback checks. Target-device playback remains required before HLS-4 can be marked done.

## Outcome and next action
Review the 0.7.14 candidate with the automated gate, then target-device test at least one authenticated multi-variant provider stream. Keep 0.7.12 available until a manually selected rendition plays successfully and the chooser metadata is confirmed.
