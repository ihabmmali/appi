---
id: HLS-10
role: research
status: active
delivery: unreleased
verification: pending
owner: builder-publisher-2026-09-27
base_commit: 24ac0358640864a0129d97b638ca37c616f6612b
artifact: none
---
# HLS-10 — Repair Buffered Look Ahead detailed debug overlay

## Objective
Make the optional detailed Buffered Look Ahead debug overlay actually appear during successful playback on the target Kodi/Fire TV environment.

The user initially observed no detailed debug overlay on a stream that appeared to play successfully, but later noted that this item may not have been HLS (or may have been a single-rendition HLS). Because Appi only invokes Buffered Look Ahead when the stream probe classifies the selected URL as HLS, the absence of an overlay on a non-HLS item is expected. The overlay defect must therefore be confirmed on a known buffered HLS session before implementation.

## Scope
First verify the detailed overlay on a stream positively identified as HLS, preferably the same multi-variant master that exposes multiple resolution choices and is known to enter Buffered Look Ahead. Only if the overlay remains invisible on that confirmed buffered session should this proceed as an implementation repair.

Investigate:
- whether the service sees `buffered_debug_overlay=true`;
- whether the active session remains available and ready while playing;
- whether `BufferOverlay.update()` receives `debug=True` and `playing=True`;
- whether Kodi window 12005 is the correct visible target;
- `addControl()`, `setLabel()`, layering, coordinates and control lifetime;
- safe teardown at playback end, mode change and setting disable.

Do not require diagnostics export to be enabled.

## Acceptance
- Confirm the test item is classified as HLS and that mode 3 actually invokes the buffered proxy.
- A non-HLS item is not evidence of overlay failure because Buffered Look Ahead is bypassed.
- A single-rendition HLS item is still a valid buffered-overlay test if Appi classifies it as HLS.
- Disabled means no detailed metrics.
- Enabled means live metrics are visibly rendered during successful Buffered Look Ahead playback.
- Show at least cached-ahead MB and buffered seconds.
- The service reads the configured setting reliably for the next playback without a Kodi restart.
- Any overlay creation/update failure is logged with the specific failing Kodi GUI operation or lifecycle gate.
- Overlay updates remain lightweight and do not affect playback.
- Startup/preparation UI and buffering behavior remain unchanged.
- Target-device verification confirms enabled and disabled behavior.

## Authorization
Reported by the user on 2026-09-27 while testing published Appi 0.7.19. Subsequent testing introduced uncertainty about whether the no-overlay stream actually traversed Buffered Look Ahead. This remains an investigation-first task because the earlier no-overlay observation is not yet conclusive, but on 2026-09-27 the user explicitly instructed that all current candidates be committed. HLS-10 is therefore committed release scope.

## Evidence
Implementation/research session opened on branch `release/0.7.20` from base `24ac0358640864a0129d97b638ca37c616f6612b`; user authorization includes implementation, integration and publication of the committed next-release scope.

The setting exists and the persistent service re-reads it. The service calls `BufferOverlay.update()` for a ready buffered session while playing; `buffered_ui.py` injects a label into Kodi window 12005. Appi's playback path invokes `buffered_hls.request_playback()` only when the selected stream is classified as HLS and mode 3 is active. Therefore the earlier no-overlay observation is inconclusive until repeated on a known HLS buffered session.

## Outcome and next action
Committed for the next release. Repeat the overlay test on a known multi-variant HLS stream with Buffered Look Ahead active. If the overlay is still absent, instrument and repair the runtime overlay path without changing the buffering engine.
