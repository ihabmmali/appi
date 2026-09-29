---
id: HLS-16
role: implementation
status: review
delivery: unreleased
verification: failed
owner: builder-publisher-0.7.22
base_commit: fd0bd5b08228c34b09de684f7b4b1f865a09e2d2
artifact: 971d29d4145411e0c78703326246b770c82d95c3
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
Created from failed target-device acceptance of HLS-14 on published Appi 0.7.21 on 2026-09-28. On 2026-09-28 the user explicitly instructed that all current candidates, diagnostics or otherwise, be committed for the next release. HLS-16 is committed next-release scope and should be treated as an early diagnostic dependency for HLS-19/HLS-21.

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


## Diagnostic dependency priority
The user correctly noted that the repeated HLS-21 timeout diagnosis would have been much easier if the detailed overlay had already been functional. HLS-16 is therefore not cosmetic-only work: it is a diagnostic dependency for HLS-19/HLS-21 target-device validation.

The repaired overlay should be available early enough in the next development cycle to observe:
- contiguous playable reserve versus total cached bytes;
- per-track starvation;
- provider throughput versus selected bitrate;
- recovery state/elapsed time/retry count;
- seek epoch refill progress.

Do not delay HLS-16 until after HLS-19/HLS-21 validation if doing so would force another blind diagnostic cycle.


## 0.7.22 candidate evidence
0.7.22 candidate replaces the primary overlay renderer with bundled modeless WindowXMLDialog and retains a logged WindowDialog compatibility fallback. Automated overlay tests verify the target renderer, numeric live text and non-fatal fallback. Target Fire TV visibility remains pending.

Final package gate run `36515744781` passed all 100 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild and ZIP/index inspection. Candidate artifact commit: `971d29d4145411e0c78703326246b770c82d95c3`; ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`.
