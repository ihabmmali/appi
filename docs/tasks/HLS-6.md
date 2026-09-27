---
id: HLS-6
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-6 — Configurable Buffered Look Ahead capacity and quality

## Objective
Make Buffered Look Ahead Playback configurable in two independent dimensions:
1. effective look-ahead capacity, at minimum through a storage-based setting; and
2. HLS rendition policy, so the user can constrain or explicitly choose bitrate/resolution when the stream exposes multiple variants.

The 0.7.16 implementation uses a fixed approximately 30-second look-ahead target and a hardcoded 384 MB per-session disk ceiling. A configurable storage ceiling alone is insufficient if the fixed 30-second target still stops prefetching first. The user setting must therefore influence the actual amount of playable media held ahead of Kodi.

Buffered mode must also not force an opaque rendition choice when the HLS master provides multiple qualities. It should support either a highest-allowed bitrate ceiling and/or an explicit selectable bitrate/resolution, while preserving the buffered proxy architecture.

## Scope
Extend only the isolated Buffered Look Ahead Playback path introduced by [HLS-5](HLS-5.md). The three pre-existing playback modes remain compatibility constraints and must not be changed.

### Look-ahead capacity
Add a user-facing playback setting expressed in storage units (MB) for buffered look-ahead capacity. Define and implement the relationship between:
- the user-selected storage target/budget;
- the amount of cached media ahead of the current playback position;
- the existing startup/recovery reserve behavior;
- any absolute safety ceiling required to prevent uncontrolled disk use.

The storage setting must drive effective look-ahead rather than merely changing a limit that the current fixed ~30-second target never reaches. A time-based target may also be exposed if useful, but storage-based configurability is the minimum requirement.

### Rendition / quality control
For multi-variant HLS, add a Buffered Look Ahead quality policy that can constrain or select the representation before/while the proxy fetches media.

At minimum support a user-configurable maximum bitrate when advertised bandwidth information is available. Where the master playlist exposes distinct variants with usable metadata, also provide an explicit selectable bitrate/resolution option so the user can choose a specific rendition.

Quality selection must use the master playlist's actual variant metadata and preserve required URL/query/auth semantics. It must not reproduce the 0.7.13/0.7.14 manual-child-playlist regression tracked by HLS-4.

The buffered proxy must fetch segments for the chosen/allowed representation and diagnostics must record the selected representation and any representation changes.

The implementation should account for variable-bitrate HLS: the same MB setting can correspond to different playable durations at different bitrates. Diagnostics should therefore report both bytes cached ahead and the corresponding known/estimated seconds of playable media.

## Acceptance
- Buffered Look Ahead Playback exposes a clearly named user-configurable storage-capacity setting in MB.
- The storage setting applies only to Buffered Look Ahead Playback and cannot alter Native Kodi, manual InputStream Adaptive, or ABR playback behavior.
- Changing the configured MB value measurably changes the amount of media Appi is willing/trying to prefetch ahead; the fixed ~30-second target must not silently prevent larger configured buffers.
- The implementation defines whether the storage value is a target, maximum, or target-with-safety-cap and labels/help text match that behavior.
- A sensible default preserves reasonable 0.7.16 behavior for users who do not change the setting.
- The implementation enforces bounded disk use and validates unsafe/invalid values.
- Variable-bitrate streams are handled without assuming that a fixed byte count equals a fixed playback duration.
- For a multi-variant HLS master, Buffered Look Ahead exposes a maximum-bitrate control when advertised bandwidth is available.
- When variant metadata permits, Buffered Look Ahead also allows an explicit rendition selection showing accurate resolution and advertised bitrate/bandwidth.
- A maximum-bitrate setting selects/permits only representations at or below the configured ceiling, with deterministic fallback if no advertised representation falls below it.
- An explicitly selected bitrate/resolution causes the proxy to fetch and serve that exact representation rather than silently substituting another one.
- Single-rendition streams continue to play without unnecessary quality prompts or errors.
- Relative/absolute variant URLs and signed/query-bearing master URLs are handled without losing provider authentication semantics.
- Buffered rendition selection does not regress the manual-selection repair in HLS-4 and does not modify playback modes 0–2.
- Diagnostics record configured buffer capacity, current cached-ahead bytes, cached-ahead segment count, known/estimated playable seconds, selected representation, advertised bitrate/bandwidth, resolution and representation changes.
- Startup and depletion/recovery behavior continue to work when the configured capacity is smaller or larger than the 0.7.16 default behavior.
- Seek/re-centering and session cleanup continue to respect the configured capacity and selected representation and remove temporary files on stop/error.
- Automated tests cover at least two distinct configured capacities and prove they produce different effective look-ahead limits/targets.
- Automated tests cover multi-variant masters for maximum-bitrate filtering and explicit rendition selection, including URL-resolution/auth preservation.
- Target-device verification records the configured capacity, chosen quality policy/representation, and observed buffered bytes/seconds during the previously problematic stream.

## Authorization
Requested by the user on 2026-09-27 while HLS-5 target-device testing is still pending. The user first required Buffered Look Ahead Playback to have a user-configurable buffer length, at least in storage terms, and subsequently required Buffered Look Ahead to support a highest-bitrate limit or selectable bitrate/resolution when the stream permits it.

This task is recorded as actionable work but is not committed release scope unless the user explicitly commits/includes it in the next release under AGENTS.md.

## Evidence
Current 0.7.16 source in `resources/lib/buffered_hls.py` defines `DEFAULT_TARGET_SECONDS = 30.0` and `MAX_SESSION_BYTES = 384 * 1024 * 1024`. Current settings expose the playback-mode selector but no Buffered Look Ahead capacity control.

The buffered proxy already parses/re-writes multi-variant HLS resources as part of HLS-5, but the shipped settings do not expose a buffered-mode maximum bitrate or explicit rendition selector.

Because prefetch is governed by a fixed time target separately from the hardcoded disk ceiling, simply making `MAX_SESSION_BYTES` editable would not necessarily increase the actual look-ahead beyond approximately 30 seconds.

## Outcome and next action
Implement both Buffered Look Ahead controls together: effective storage/look-ahead capacity and rendition policy. Preserve all non-buffered playback paths. Before implementation, choose a safe capacity range/default and define deterministic quality-selection/fallback behavior for masters with complete, partial or missing bitrate/resolution metadata.
