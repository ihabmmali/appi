---
id: HLS-5
role: implementation
status: review
delivery: unreleased
verification: partial
owner: ChatGPT release worker 2026-09-27
base_commit: 9dfd6a2802dc03bf5acd1d4806a76185849eac72
artifact: none
---
# HLS-5 — Buffered Look Ahead Playback

## Objective
Add a fourth HLS playback mode named **Buffered Look Ahead Playback** that protects playback from intermittent provider/CDN segment-delivery stalls by keeping a materially deeper amount of actual playable HLS media on local disk ahead of Kodi.

This is an experimental remedy for the repeated-stall problem tracked by [HLS-1](HLS-1.md). It does not close HLS-1 until target-device evidence shows whether the deeper buffer changes the failure mode.

## Baseline playback audit
Source inspection of the published 0.7.15 baseline at `9dfd6a2802dc03bf5acd1d4806a76185849eac72` established the three existing HLS paths before implementation:
- Mode 0, **Native Kodi automatic**: `_configure_hls()` returns `native-kodi` before setting any `inputstream` property. Appi passes the original provider URL to Kodi, so this is genuinely Kodi's native/default HLS path.
- Mode 1, **Ask quality before playback (InputStream Adaptive)**: Appi keeps the original master URL and explicitly sets `inputstream=inputstream.adaptive` plus `stream_selection_type=ask-quality`.
- Mode 2, **Adaptive bitrate (InputStream Adaptive)**: Appi explicitly sets InputStream Adaptive with `stream_selection_type=adaptive` and, when configured, `chooser_bandwidth_max`.

Because Kodi Default is already genuinely native, all three existing branches are compatibility constraints and must remain functionally unchanged. HLS-5 is added as an isolated fourth branch.

## Scope
Implement a local loopback HLS buffering proxy owned by Appi's persistent service. The plugin requests a buffered session only when HLS mode 3 is selected; the service fetches and rewrites HLS playlists to opaque local URLs, stores media segments in a temporary disk-backed rolling buffer, and serves them to Kodi without transcoding.

Required behavior:
- Default target look-ahead about 30 seconds, with constants/settings architecture that can later support 15/30/60 seconds.
- Startup reserve about 18 seconds (within the requested 15–20 second range) before the selected media playlist is released to Kodi.
- Sequential VOD segment prefetch and rolling cleanup of consumed temporary segments.
- On depletion, rebuild a reserve before releasing the blocked requested segment where technically feasible instead of resuming after a single newly arrived segment.
- Preserve playlist tag order and pass through discontinuities.
- Rewrite and proxy child playlists, audio/subtitle rendition playlists, encryption key URIs, initialization-map URIs and other URI attributes without exposing provider credentials on the localhost URL.
- Preserve direct bytes/pass-through behavior; no transcoding or re-encoding.
- Seeking must re-centre the prefetch cursor or fall back to safe on-demand fetching. Stop/error/abort must fail safely and temporary session data must be cleaned.
- Existing manual selection, adaptive selection, subtitles, resume, Recently Played and watched-state behavior must not be modified.

## Diagnostics
For buffered mode, extend DIAG-2's session timeline with directly observed proxy data where available:
- buffered seconds ahead and cached/queued segment count;
- per-segment request/download latency, duration, byte count and effective throughput;
- depletion and recovery events;
- stall-correlated proxy state;
- selected HLS representation metadata and representation changes when the local proxy observes variant requests.

Authenticated upstream URLs, query strings, cookies/credentials and subtitle contents remain excluded from exported diagnostics.

## Acceptance
- The three published 0.7.15 HLS modes retain the same source-level branches/properties and pass regression tests independently.
- A fourth selectable global/per-title mode is exposed as **Buffered Look Ahead Playback**.
- Buffered mode routes only that mode through the Appi loopback proxy; modes 0–2 never invoke it.
- A sanitized multi-variant VOD fixture proves master/child URI rewriting, relative URL resolution, audio/subtitle URI association, key/map URI proxying, discontinuity preservation and representation metadata association.
- A deterministic segment fixture proves at least ~18 seconds are cached before startup proceeds and ~30 seconds are targeted during steady playback.
- A depletion test proves a requested segment can be held until a recovery reserve is rebuilt, within bounded timeout/failure handling.
- A seek/jump test proves the proxy safely serves an out-of-order requested segment and resumes/re-centres look-ahead without corrupting ordering.
- Cleanup tests prove temporary buffered files are removed when the session is stopped/aborted.
- Diagnostics tests prove segment latency/throughput, queued/downloaded segment counts, buffered seconds, depletion/recovery and representation identity are emitted without raw authenticated URLs.
- Full unit/smoke suite, workflow validation, deterministic package build and repository artifact inspection pass.
- Publish only after automated regression checks for modes 0–2 and buffered-mode tests pass. Target-device verification remains required to establish whether 30+ seconds of actual media eliminates the observed intermittent stalls.

## Authorization
On 2026-09-27 the user explicitly instructed the release worker to inspect the 0.7.15 playback implementation, preserve the three existing playback modes, add this fourth buffered mode, commit it to the next release scope, implement it, run the documented release lifecycle and publish only after regression testing passes. This authorizes implementation, integration and publication of HLS-5 as the next release.

## Evidence
The 0.7.15 source audit above establishes that Kodi Default is already native and therefore requires no corrective change. HLS-5 begins from the published 0.7.15 `main` head `9dfd6a2802dc03bf5acd1d4806a76185849eac72`.

Implementation/review evidence on 2026-09-27:
- Self-review was performed against release-artifact commit `6e71ad93276c993724a5973cb8814e603653f4d0` and the published 0.7.15 base. The mode 0 branch still returns before any InputStream Adaptive property assignment; mode 1 still uses the original master URL plus `ask-quality`; mode 2 still uses `adaptive` plus the optional bandwidth ceiling. Mode 3 is the only branch that requests and substitutes the localhost buffered URL.
- During pre-package self-review an `EXT-X-MAP` byte-range defect was found: the proxy already stored the exact requested byte slice while the rewritten tag could still retain `BYTERANGE`. Commit `16dffd73fbe84599b4eaf733ea4fe1a03030f890` corrected the double-range risk and `ebee56cc004e90726c4842fea3e7bd5281209ade` added regression coverage before the release gate.
- The first package attempt, run 36296858373, was blocked by test-harness module pollution in the new buffered test; it did not identify a production playback failure. Commit `56e0c2477c7227f2af9834cb995ef67d7211af5b` isolates the test modules.
- Release/package run 36296897848 passed: 54 unit/smoke tests, workflow tracker validation, deterministic repository build, ZIP/hash/index inspection, and the packaging job all succeeded.
- The successful gate produced branch artifact commit `6e71ad93276c993724a5973cb8814e603653f4d0`; `plugin.video.appi-0.7.16.zip` SHA-256 is `ecb310e42b016cf968b27e2af4d25ed6f1b106b888a9c0da387bde4bde595138`.
- Automated tests explicitly cover all four HLS branches and buffered startup reserve, depletion/recovery, seek re-centering, cleanup, master/rendition/key/map rewriting, discontinuities, byte ranges, representation metadata and sanitized proxy telemetry.

## Outcome and next action
Implementation and automated release verification pass. HLS-5 remains in review/partial verification because only target-device playback can establish whether the 30-second look-ahead eliminates the reported provider stalls. Publication is authorized by the user and may proceed; after integration, record the published commit and post-merge/Pages evidence without treating publication as target-device acceptance.
