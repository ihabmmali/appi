---
id: HLS-14
role: implementation
status: active
delivery: unreleased
verification: failed
owner: builder-publisher-2026-09-28
base_commit: 4a415f9eaeb48c77ef2fcaa895db90d7e66ab183
artifact: none
---
# HLS-14 — Make the detailed Buffered Look Ahead overlay actually visible

## Objective
Repair the detailed debug overlay after confirmed target-device testing on 0.7.20 showed that enabling it still renders nothing during Buffered Look Ahead playback.

## Scope
This is now a confirmed display defect, not an investigation into whether Buffered Look Ahead was active.

- Capture the operation-specific logs added by HLS-10 on the target Kodi/Fire TV build.
- Determine whether the failure is the chosen Kodi window, control insertion, visibility/layer ordering, control lifetime or service/session gating.
- Replace the current display mechanism if necessary rather than preserving window 12005 without evidence.
- Prefer a robust skin-independent overlay mechanism. A small transparent custom Kodi window/dialog is acceptable if direct control injection is unreliable.
- Do not alter buffering behavior to fix the overlay.
- Consume the real buffer metrics produced by HLS-13 when available.

## Acceptance
- On a confirmed Buffered Look Ahead HLS session, enabling Detailed buffer debug overlay visibly shows live metrics.
- At minimum show cached-ahead MB and contiguous playable seconds.
- If available, also show selected bitrate, measured throughput and buffer state (filling/full/draining/critical).
- Disabling it removes the overlay.
- Overlay remains visible during fullscreen playback on the target Fire TV skin.
- Overlay creation/update failure is explicit in logs and does not affect playback.
- Overlay update rate is lightweight and does not materially reduce prefetch throughput.
- Target-device verification includes a screenshot/observation of the visible overlay on a known multi-variant HLS stream.

## Authorization
Created from confirmed 0.7.20 target-device failure on 2026-09-28. The user explicitly confirmed the detailed debug overlay still renders nothing and instructed that these Buffered Look Ahead repairs be committed for the next release. HLS-14 is therefore committed release scope.

## Evidence
HLS-10 shipped additional logging in 0.7.20 but preserved the existing fullscreen-window target. The user has now confirmed that Detailed buffer debug overlay still does nothing while Buffered Look Ahead mode is active.

## Outcome and next action
Committed for the next release. Use the HLS-10 logs to identify the failing GUI path, then replace it with a target-device-proven overlay mechanism.


Implementation session 2026-09-28: activated on `release/0.7.21` from base `4a415f9eaeb48c77ef2fcaa895db90d7e66ab183`; authorized scope is implementation, review, integration and publication of the committed next release.
