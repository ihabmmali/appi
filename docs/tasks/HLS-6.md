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
# HLS-6 — Configurable Buffered Look Ahead buffer and quality choice

## Objective
Make Buffered Look Ahead Playback configurable in exactly two user-facing dimensions:

1. **Buffer size:** the user can configure how much local storage Buffered Look Ahead may use for prefetched media.
2. **Stream quality behavior:** the user chooses whether Buffered Look Ahead automatically uses the **highest bitrate available** from the HLS master playlist, or **prompts before playback** to select from the available bitrate/resolution variants.

There is no requested maximum-bitrate ceiling mode for Buffered Look Ahead. The quality choices are automatic highest available or prompt/select.

## Scope
Extend only the isolated Buffered Look Ahead Playback path introduced by [HLS-5](HLS-5.md). The three pre-existing playback modes remain compatibility constraints and must not be changed.

### User-configurable buffer size
Expose a Buffered Look Ahead buffer-size setting in storage units (MB).

The configured size must affect the actual amount of media the proxy is allowed/trying to retain ahead of Kodi. The current fixed approximately 30-second target must not silently prevent a larger configured storage buffer from being used.

Define a bounded implementation that relates:
- configured buffer size in MB;
- actual cached bytes ahead of playback;
- known/estimated playable seconds represented by those bytes;
- startup/recovery reserve behavior;
- cleanup and an absolute safety limit if one is still needed internally.

Because HLS bitrate varies, the same MB setting may correspond to different playable durations. Diagnostics should report both storage use and playable-duration estimates.

### Buffered quality behavior
Expose a Buffered Look Ahead quality setting with two behaviors:

- **Highest available bitrate:** inspect the multi-variant HLS master playlist and automatically use the variant with the highest advertised bitrate/bandwidth.
- **Prompt for quality:** before buffered playback begins, show the available variants and let the user select one. Each option should show accurate bitrate/bandwidth and resolution when supplied by the manifest.

For a single-rendition stream, proceed directly without an unnecessary prompt.

The selected variant must be the one the buffered proxy fetches and serves. Variant URL handling must preserve relative/absolute URL resolution and provider query/auth semantics and must not repeat the manual child-playlist regression tracked by [HLS-4](HLS-4.md).

## Acceptance
- Buffered Look Ahead exposes a clearly named user-configurable buffer-size setting in MB.
- Changing the configured buffer size measurably changes the allowed/effective cached-ahead media size; the old fixed ~30-second target does not silently cap larger settings.
- A sensible default preserves reasonable 0.7.16 behavior for users who do not change the setting.
- Disk use remains bounded and invalid/unsafe values are handled safely.
- Diagnostics report configured buffer size, cached-ahead bytes, cached-ahead segment count and known/estimated playable seconds.
- Buffered Look Ahead exposes exactly the requested quality choices: **Highest available bitrate** and **Prompt for quality**.
- Highest-available mode automatically selects the variant with the highest advertised bitrate/bandwidth from a multi-variant master playlist.
- Prompt mode lists all usable available variants with correct advertised bitrate/bandwidth and resolution where present.
- Selecting a prompted variant causes the proxy to fetch and serve that exact variant.
- Single-rendition streams play without an unnecessary quality prompt.
- If bitrate metadata is missing or malformed, fallback behavior is deterministic and documented rather than inventing a bitrate.
- Relative/absolute variant URLs and signed/query-bearing master URLs retain required provider access semantics.
- Buffer-size and quality settings apply only to Buffered Look Ahead and do not modify Native Kodi, manual InputStream Adaptive or ABR playback modes.
- Startup, depletion/recovery, seeking/re-centering and cleanup continue to work under both quality behaviors and across different configured buffer sizes.
- Diagnostics record the quality behavior, selected representation, advertised bitrate/bandwidth and resolution.
- Automated tests cover at least two buffer sizes, automatic highest-bitrate selection, prompted selection, single-rendition playback and authenticated/relative variant URL handling.
- Target-device verification records the configured buffer size, selected quality behavior/representation and observed cached bytes/seconds on the previously problematic stream.

## Authorization
Requested by the user on 2026-09-27 while HLS-5 target-device testing is still pending. The user requires Buffered Look Ahead Playback to have a user-configurable buffer size and a quality behavior setting that either automatically uses the highest available bitrate or prompts the user to select from the available bitrate/resolution variants.

This task is recorded as actionable work but is not committed release scope unless the user explicitly commits/includes it in the next release under AGENTS.md.

## Evidence
Current 0.7.16 source in `resources/lib/buffered_hls.py` defines `DEFAULT_TARGET_SECONDS = 30.0` and `MAX_SESSION_BYTES = 384 * 1024 * 1024`. Current settings expose the playback-mode selector but no Buffered Look Ahead buffer-size or quality-behavior controls.

The previous HLS-6 wording incorrectly introduced a maximum-bitrate ceiling. On 2026-09-27 the user corrected the requirement: Buffered Look Ahead should instead either automatically use the highest available bitrate or prompt the user to choose an available bitrate/resolution.

## Outcome and next action
Implement the user-configurable Buffered Look Ahead buffer size plus the two requested quality behaviors: automatic highest available bitrate or prompt/select. Preserve modes 0–2 unchanged and retain the buffered proxy's isolated architecture.
