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
# HLS-6 — Configurable Buffered Look Ahead buffer, quality choice and debug overlay

## Objective
Make Buffered Look Ahead Playback configurable in three user-facing dimensions:

1. **Buffer size:** the user can configure how much local storage Buffered Look Ahead may use for prefetched media.
2. **Stream quality behavior:** the user chooses whether Buffered Look Ahead automatically uses the **highest bitrate available** from the HLS master playlist, or **prompts before playback** to select from the available bitrate/resolution variants.
3. **Buffer-state overlay:** an optional debug overlay can display the current buffered state during playback, with user-configurable visibility.

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

### Optional buffer-state debug overlay
Expose a user setting that controls whether a small text overlay is visible during Buffered Look Ahead playback.

When enabled, the overlay should show the current live buffer state using information already available to the buffered proxy/diagnostics. A simple text element is sufficient. At minimum it should show the current cached-ahead amount in a meaningful form such as bytes/MB and known/estimated playable seconds; cached segment count may also be shown.

The overlay is a debug/diagnostic aid, not a required normal-playback UI. It must be possible for the user to turn it on or off without changing buffer behavior, quality selection or any of the other playback modes. It should not require a diagnostic export to be active merely to display the current buffer state.

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
- Buffered Look Ahead exposes a user-configurable **buffer-state debug overlay visibility** setting.
- With the overlay enabled, playback displays a small live text indicator containing at least current cached-ahead storage and known/estimated playable buffered seconds.
- With the overlay disabled, no Buffered Look Ahead debug text is shown.
- Toggling overlay visibility does not change the configured buffer size, selected rendition, prefetch behavior or playback result.
- Overlay updates are lightweight enough that enabling them does not materially affect playback or itself cause buffering.
- The overlay is limited to Buffered Look Ahead unless a future requirement explicitly extends it elsewhere.
- Buffer-size, quality and overlay settings apply only to Buffered Look Ahead and do not modify Native Kodi, manual InputStream Adaptive or ABR playback modes.
- Startup, depletion/recovery, seeking/re-centering and cleanup continue to work under both quality behaviors and across different configured buffer sizes.
- Diagnostics record the quality behavior, selected representation, advertised bitrate/bandwidth and resolution.
- Automated tests cover at least two buffer sizes, automatic highest-bitrate selection, prompted selection, single-rendition playback, authenticated/relative variant URL handling, and overlay enabled/disabled behavior where practical.
- Target-device verification records the configured buffer size, selected quality behavior/representation, overlay state and observed cached bytes/seconds on the previously problematic stream.

## Authorization
Requested by the user on 2026-09-27 while HLS-5 target-device testing is still pending. The user requires Buffered Look Ahead Playback to have a user-configurable buffer size; a quality behavior setting that either automatically uses the highest available bitrate or prompts the user to select from the available bitrate/resolution variants; and an optional user-visible debug overlay showing current buffer state.

This task is recorded as actionable work but is not committed release scope unless the user explicitly commits/includes it in the next release under AGENTS.md.

## Evidence
Current 0.7.16 source in `resources/lib/buffered_hls.py` defines `DEFAULT_TARGET_SECONDS = 30.0` and `MAX_SESSION_BYTES = 384 * 1024 * 1024`. Current settings expose the playback-mode selector but no Buffered Look Ahead buffer-size, quality-behavior or overlay-visibility controls.

The buffered proxy already tracks values such as buffered seconds and cached segment counts for diagnostics, so HLS-6 can reuse that state for a lightweight on-screen indicator rather than inventing a separate buffer model.

The previous HLS-6 wording incorrectly introduced a maximum-bitrate ceiling. On 2026-09-27 the user corrected the quality requirement: Buffered Look Ahead should instead either automatically use the highest available bitrate or prompt the user to choose an available bitrate/resolution.

## Outcome and next action
Implement the user-configurable Buffered Look Ahead buffer size, the two requested quality behaviors (automatic highest available bitrate or prompt/select), and the optional buffer-state debug overlay. Preserve modes 0–2 unchanged and retain the buffered proxy's isolated architecture.
