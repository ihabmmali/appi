---
id: HLS-10
role: implementation
status: ready
delivery: unreleased
verification: failed
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-10 — Repair Buffered Look Ahead detailed debug overlay

## Objective
Make the optional detailed Buffered Look Ahead debug overlay actually appear during successful playback on the target Kodi/Fire TV environment.

Appi 0.7.19 prepares and plays Buffered Look Ahead streams successfully in the user's current test, and the simple startup/preparation windows work. Enabling the optional detailed debug overlay produces no visible overlay.

## Scope
Repair only the detailed overlay display path. Do not destabilize Buffered Look Ahead preparation/handoff/playback or the simple startup/buffering UI.

Investigate:
- whether the service sees `buffered_debug_overlay=true`;
- whether the active session remains available and ready while playing;
- whether `BufferOverlay.update()` receives `debug=True` and `playing=True`;
- whether Kodi window 12005 is the correct visible target;
- `addControl()`, `setLabel()`, layering, coordinates and control lifetime;
- safe teardown at playback end, mode change and setting disable.

Do not require diagnostics export to be enabled.

## Acceptance
- Disabled means no detailed metrics.
- Enabled means live metrics are visibly rendered during successful Buffered Look Ahead playback.
- Show at least cached-ahead MB and buffered seconds.
- The service reads the configured setting reliably for the next playback without a Kodi restart.
- Any overlay creation/update failure is logged with the specific failing Kodi GUI operation or lifecycle gate.
- Overlay updates remain lightweight and do not affect playback.
- Startup/preparation UI and buffering behavior remain unchanged.
- Target-device verification confirms enabled and disabled behavior.

## Authorization
Reported by the user on 2026-09-27 while testing published Appi 0.7.19. This task is a ready candidate and is not committed to a future release unless explicitly included under AGENTS.md.

## Evidence
The setting exists and the persistent service re-reads it. The service calls `BufferOverlay.update()` for a ready session while playing; `buffered_ui.py` injects a label into Kodi window 12005. The target device nevertheless renders nothing when the setting is enabled.

## Outcome and next action
Instrument the runtime overlay path and repair the first failing gate or GUI operation without changing the buffering engine.
