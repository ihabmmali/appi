---
id: HLS-16
role: implementation
status: ready
delivery: unreleased
verification: failed
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-16 — Replace invisible Buffered Look Ahead debug overlay with a target-device-proven renderer

## Objective
Make the optional detailed Buffered Look Ahead telemetry visibly render on the target Fire TV/Kodi environment.

0.7.20's direct fullscreen-window control injection failed. 0.7.21 replaced that path with a modeless `xbmcgui.WindowDialog`, but the overlay is still invisible on the target device even while Buffered Look Ahead itself works.

A third repair must therefore be evidence-driven and may replace the GUI mechanism entirely.

## Scope
- Capture whether `BufferOverlay._create()`, `WindowDialog.show()`, and subsequent `setLabel()` calls actually execute on the target device.
- Confirm whether the dialog exists but is behind fullscreen video, immediately loses visibility/focus, is closed by Kodi playback-window transitions, or never paints.
- Do not preserve `WindowDialog` merely because unit tests can instantiate it.
- Evaluate a renderer that is actually visible above fullscreen video on the supported Kodi/Fire TV build. A small custom `WindowXMLDialog`/overlay window, Kodi-native overlay surface, or another documented persistent GUI mechanism is acceptable if target-device proven.
- Keep rendering isolated from buffer-fetch threads and lightweight.
- Continue consuming HLS-13 metrics: buffered bytes, contiguous seconds, buffer state, selected bitrate, measured provider throughput and epoch ID.
- Do not modify the working deep-buffer algorithm merely to make telemetry visible.

## Acceptance
- With Detailed buffer debug overlay enabled during a confirmed Buffered Look Ahead HLS session, visible telemetry appears over normal fullscreen playback on the target Fire TV.
- At minimum show actual cached-ahead MB and contiguous playable seconds.
- Also show buffer state; selected bitrate and provider throughput should be shown when known.
- The telemetry updates while playback continues and does not steal playback controls/focus.
- Disabling the setting removes the overlay.
- Playback stop/error reliably removes the overlay.
- Overlay creation/update failures are logged explicitly.
- The renderer survives the transition from preparation UI to fullscreen video.
- Target-device acceptance is mandatory; mocked GUI creation alone is not sufficient evidence.
- HLS-13 buffering performance is unchanged.

## Authorization
Created from failed target-device acceptance of HLS-14 on published Appi 0.7.21 on 2026-09-28. This is a ready candidate and is not committed to a future release until explicitly included under AGENTS.md.

## Evidence
The 0.7.21 modeless `WindowDialog` renderer passes automated lifecycle tests but remains invisible on the user's Fire TV during confirmed Buffered Look Ahead playback. Meanwhile the user reports the buffering itself appears to work well, isolating the remaining issue to the rendering/UI path.

## Outcome and next action
Instrument the actual target-device GUI lifecycle and replace the renderer with one demonstrated to remain visible above fullscreen video.


## Seek/recovery observability
Target-device observation on 0.7.21: after a seek there is a noticeable delay before playback resumes. This is plausibly HLS-12 rebuilding the new epoch reserve, but the current invisible overlay prevents confirmation.

The repaired overlay must therefore make seek behavior observable in real time. During a seek/recenter it should show, where available:
- epoch/reason = seek or cold-resume;
- requested target time/segment;
- currently buffered KB/MB for the new epoch;
- target recovery reserve;
- playable seconds ahead;
- whether the state is filling, recovering, stalled or ready;
- retry count/status when HLS-19 is active.

This is diagnostic visibility only; do not change the working seek/reservoir algorithm merely to shorten the observed delay without evidence.


## HLS-21 failure classification
When HLS-21 metrics are available, the repaired overlay should make the critical distinction visible during a stall: **contiguous playable reserve** versus total cached bytes, plus whether the next required video/audio segment is missing. This helps the user tell a genuinely empty reservoir from a cache that contains unusable non-contiguous data.
