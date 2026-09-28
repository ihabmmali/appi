---
id: HLS-10
role: research
status: review
delivery: released
verification: failed
owner: builder-publisher-2026-09-27
base_commit: 24ac0358640864a0129d97b638ca37c616f6612b
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.20.zip
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

Source review confirms the persistent service re-reads `buffered_debug_overlay` and passes ready active-session status into `BufferOverlay.update()`; the overlay still targets fullscreen video window 12005. Because the earlier invisible-overlay observation may not have traversed Buffered Look Ahead, there is insufficient device evidence to change that target. Candidate implementation `4c5363e3220dc16507b308e6ccfa8bbec4eb6d40` guards and logs the exact Window/ControlLabel/addControl/setLabel/removeControl operation while keeping failures non-fatal. Release/package run `36375784976` passed the overlay regression test plus the complete automated suite. Confirmed HLS Fire TV visibility remains pending.

Published through PR #8 / merge `6e6db9bec185ec6b5eea664d27cb7b94f4efa2ef`. Post-merge verification run `36376270017` passed and Pages deployment run `36376269821` completed successfully. Delivery is `https://ihabmmali.github.io/appi/plugin.video.appi-0.7.20.zip`; the verified generated ZIP SHA-256 is `41e1bdec7229d1a0a3d8787427ac9c434fb773e302c7d8f5bae428de0de7755f`. Publication does not establish target-device acceptance.

## Outcome and next action
0.7.20 is published, but target-device verification failed: the detailed overlay remains invisible during confirmed Buffered Look Ahead playback. Preserve this evidence; HLS-14 owns the actual display repair.


## 0.7.20 confirmed target-device failure
The user has now confirmed the detailed debug overlay is still invisible while using Buffered Look Ahead mode itself. The earlier uncertainty about whether the test item bypassed Buffered Look Ahead is therefore resolved.

The 0.7.20 logging-only follow-up did not satisfy the functional requirement. HLS-10 remains released but failed verification. [HLS-14](HLS-14.md) owns the actual overlay implementation repair.
