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
# HLS-6 — User-configurable Buffered Look Ahead capacity

## Objective
Make Buffered Look Ahead Playback's effective look-ahead capacity user-configurable, at minimum through a storage-based setting.

The 0.7.16 implementation uses a fixed approximately 30-second look-ahead target and a hardcoded 384 MB per-session disk ceiling. A configurable storage ceiling alone is insufficient if the fixed 30-second target still stops prefetching first. The user setting must therefore influence the actual amount of playable media held ahead of Kodi.

## Scope
Extend only the isolated Buffered Look Ahead Playback path introduced by [HLS-5](HLS-5.md). The three pre-existing playback modes remain compatibility constraints and must not be changed.

Add a user-facing playback setting expressed in storage units (MB) for buffered look-ahead capacity. Define and implement the relationship between:
- the user-selected storage target/budget;
- the amount of cached media ahead of the current playback position;
- the existing startup/recovery reserve behavior;
- any absolute safety ceiling required to prevent uncontrolled disk use.

The storage setting must drive effective look-ahead rather than merely changing a limit that the current fixed ~30-second target never reaches. A time-based target may also be exposed if useful, but storage-based configurability is the minimum requirement.

The implementation should account for variable-bitrate HLS: the same MB setting can correspond to different playable durations at different bitrates. Diagnostics should therefore report both bytes cached ahead and the corresponding known/estimated seconds of playable media.

## Acceptance
- Buffered Look Ahead Playback exposes a clearly named user-configurable storage-capacity setting in MB.
- The setting applies only to Buffered Look Ahead Playback and cannot alter Native Kodi, manual InputStream Adaptive, or ABR playback behavior.
- Changing the configured MB value measurably changes the amount of media Appi is willing/trying to prefetch ahead; the fixed ~30-second target must not silently prevent larger configured buffers.
- The implementation defines whether the setting is a target, maximum, or target-with-safety-cap and labels/help text match that behavior.
- A sensible default preserves reasonable 0.7.16 behavior for users who do not change the setting.
- The implementation enforces bounded disk use and validates unsafe/invalid values.
- Variable-bitrate streams are handled without assuming that a fixed byte count equals a fixed playback duration.
- Diagnostics record configured buffer capacity, current cached-ahead bytes, cached-ahead segment count, and known/estimated playable seconds.
- Startup and depletion/recovery behavior continue to work when the configured capacity is smaller or larger than the 0.7.16 default behavior.
- Seek/re-centering and session cleanup continue to respect the configured capacity and remove temporary files on stop/error.
- Automated tests cover at least two distinct configured capacities and prove they produce different effective look-ahead limits/targets.
- Target-device verification records the configured capacity and observed buffered bytes/seconds during the previously problematic stream.

## Authorization
Requested by the user on 2026-09-27 while HLS-5 target-device testing is still pending. The user stated that Buffered Look Ahead Playback must have a user-configurable buffer length, at least in terms of storage. This task is recorded as actionable work but is not committed release scope unless the user explicitly commits/includes it in the next release under AGENTS.md.

## Evidence
Current 0.7.16 source in `resources/lib/buffered_hls.py` defines `DEFAULT_TARGET_SECONDS = 30.0` and `MAX_SESSION_BYTES = 384 * 1024 * 1024`. Current settings expose the playback-mode selector but no Buffered Look Ahead capacity control.

Because prefetch is governed by a fixed time target separately from the hardcoded disk ceiling, simply making `MAX_SESSION_BYTES` editable would not necessarily increase the actual look-ahead beyond approximately 30 seconds.

## Outcome and next action
Implement the storage-based capacity control as a follow-up to HLS-5, preserving all non-buffered playback paths. Before implementation, choose a safe settings range/default and make the storage target's interaction with startup/recovery reserves explicit.
