---
id: HLS-26
role: implementation
status: review
delivery: released
verification: partial
owner: builder-publisher-2026-09-30
base_commit: e359459e1e3734e1c60608632b2213fe33bc92e7
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.24.zip
---
# HLS-26 — Make the Buffered debug overlay setting authoritative and non-blocking

## Objective
Fix Appi 0.7.23 so the Buffered Look Ahead debug overlay is shown **only** when its setting is enabled.

Preserve the current user-accepted **Back-to-dismiss** behavior unless there is a well-documented Kodi mechanism that is demonstrably skin-independent and allows passive on-video statistics without interfering with the normal playback OSD/navigation.

Do not replace the current renderer with an experimental or skin-specific workaround merely to make the overlay coexist with Kodi's OSD.

This is a successor to HLS-23 target-device verification. The multiline formatting introduced in 0.7.23 is acceptable and should be preserved.

## Scope
Repair the authoritative runtime setting boundary only. Preserve the current multiline renderer and user-accepted Back-to-dismiss behavior; do not introduce a new focus/window mechanism or alter buffering/recovery behavior.

## 0.7.23 target-device evidence
The user reports:

- the former rogue simple `Appi buffering` message is gone;
- the full debug display is now correctly formatted across multiple lines;
- nevertheless, the full debug display appears and remains persistent regardless of whether the debug-display setting is ON or OFF;
- while the debug display is active, pressing the Fire TV center/select button does not bring up Kodi's normal playback controls/OSD (settings, subtitles, seek timeline, etc.);
- pressing Back/Exit closes the Appi debug display;
- immediately after the Appi display is closed, Kodi's normal playback navigation/OSD behavior returns;
- after dismissing the overlay with Back, it does not return during that playback session; replaying the item is required to see it again.

The user can tolerate using Back to dismiss an enabled diagnostic overlay if necessary, but the selection switch must be authoritative: OFF means no debug overlay.

## Current source behavior
0.7.23 source appears correct at the pure renderer-call boundary:
- `subtitle_service.run()` reads `_enabled('buffered_debug_overlay', False)` on each service loop and passes it to `overlay.update(...)`;
- `status_text()` returns an empty string when `debug=False`;
- `BufferOverlay.update()` closes an existing renderer when text is empty.

Therefore the target-device always-on behavior is not explained by the intended 0.7.23 control flow and requires device-level setting/lifecycle instrumentation.

The primary renderer is `xbmcgui.WindowXMLDialog`. Although shown modelessly with `show()`, it is still a Kodi GUI window. The target-device observation that Back closes it and restores normal playback OSD behavior strongly indicates that this window participates in Kodi's input/window stack and is not truly input-transparent.

## Mandatory setting-gate repair
The debug setting is the authoritative master switch.

When OFF:
- do not create or show any Appi debug overlay window;
- if one already exists, close it promptly;
- do not recreate it on later status updates;
- no detailed buffer text may appear during normal playback, refill, recovery, seek, pause or resume.

Instrument the setting boundary on the target device:
- raw stored setting value;
- parsed/effective boolean value;
- whether the value changed since the previous poll;
- whether Kodi emitted a settings-changed event if available;
- whether a renderer existed at the time;
- create/update/close decision.

If the long-running service's `xbmcaddon.Addon` object does not reliably observe runtime setting changes on the target device, refresh/re-read the setting through a target-device-proven mechanism rather than assuming the existing object is live.

Do not require Kodi or Appi restart merely to turn the overlay OFF.

## Overlay interaction policy
The existing Back-to-dismiss interaction is the **default preservation path**, not merely a last-resort fallback.

Do not change the renderer solely to make Kodi's normal playback OSD work concurrently unless the proposed mechanism is:
- documented in Kodi's supported/public behavior rather than relying on an undocumented window-stack trick;
- skin-independent;
- demonstrably non-focus-stealing/non-intercepting on the target Fire TV;
- compatible with normal playback navigation across the supported Kodi environment.

If all of those conditions are met, a passive renderer may be considered after evidence/review.

Otherwise retain the current interaction:
- setting OFF = no overlay at all;
- setting ON = display the diagnostic overlay;
- Back dismisses it for the remainder of the current playback session;
- after dismissal, Kodi's normal OSD/navigation remains available;
- dismissal does not stop playback or buffering;
- if the setting is still ON, a new playback session may show the overlay again.

Do not pursue experimental attachment to skin controls, skin-specific XML targets, undocumented window IDs, focus hacks, key remapping, or another custom-window mechanism merely to avoid the Back press.

The user's priority is **strict adherence to the debug-display setting**, not simultaneous Appi-overlay/Kodi-OSD visibility.

## Layout
Preserve the successful HLS-23 multiline layout:
- bounded within the screen;
- multiple logical lines;
- no horizontal overflow;
- readable on the target Fire TV.

Do not regress back to a single long line.

## Acceptance
Mandatory:
- With the setting OFF before playback starts, no Appi debug overlay is ever created or displayed.
- Switching OFF while the overlay is visible closes it promptly and it remains absent.
- Changing the setting does not require restarting Kodi or replaying media.
- The former simple `Appi buffering` message remains absent when debug is OFF.
- Multiline screen-safe formatting remains correct.
- Automated tests cover raw/effective OFF, ON->OFF transition and no recreation after OFF.
- Target Fire TV acceptance is mandatory.

Interaction acceptance:
- The existing Back-to-dismiss behavior is acceptable and should be preserved unless a documented, skin-independent passive-overlay mechanism is proven.
- With debug ON, Back may dismiss the overlay for the remainder of the current playback session.
- After dismissal, Kodi OSD/navigation must work normally.
- A new playback session may show the overlay again if the setting remains ON.
- OFF must remain completely silent.
- Simultaneous visibility of Appi debug telemetry and Kodi's normal playback OSD is **not** a release requirement unless a documented skin-independent mechanism is found.

## Preservation constraints
Do not change:
- Buffered Look Ahead reservoir/recovery behavior;
- HLS-25 pause/resume repair semantics;
- producer concurrency;
- selected rendition;
- HLS modes 0-2.

## Authorization
Created from Appi 0.7.23 Fire TV target-device feedback on 2026-09-29. The user explicitly requires the setting switch to work as intended and reports that the current overlay window blocks normal playback navigation while active.

On 2026-09-30 the user explicitly instructed that all current candidates be committed for the next release. HLS-26 is committed next-release scope, with strict debug-switch gating as the mandatory requirement and the documented Back-to-dismiss preservation policy unchanged.

## Evidence
0.7.23 source contains an apparent master gate, but target-device behavior contradicts it. The current renderer is a `WindowXMLDialog`; pressing Back removes that window and immediately restores Kodi's normal playback OSD/navigation, providing strong evidence that the renderer itself is participating in the GUI input stack.

## Outcome and next action
First prove and repair target-device setting propagation so OFF is absolute and ON is the only state that permits the overlay to appear. Preserve the current Back-to-dismiss behavior. Only consider a different renderer if a documented, skin-independent, target-device-proven Kodi mechanism exists; otherwise do not spend another iteration redesigning the overlay window.


## 2026-09-30 interaction-policy clarification
The user explicitly clarified that OSD coexistence is secondary. Unless there is a **well-documented and skin-independent** Kodi method for persistent passive on-video statistics, keep the existing press-Back-to-dismiss behavior.

The mandatory requirement is strict adherence to the debug-display switch:
- OFF: never display debug statistics;
- ON: display the debug statistics;
- while ON, Back may dismiss the display for the remainder of that playback session.

Do not make a speculative renderer replacement part of acceptance.

## 0.7.24 implementation evidence
Source implementation: `4cfd2939567113d34e73ecb97d3c5fed9d7089bd`. Automated coverage: `94c62ee25271b13a13b78038f344bcf51e8d0ffc`.

The persistent service now reads `buffered_debug_overlay` through a fresh `xbmcaddon.Addon()` instance, records raw/effective transition state and makes OFF suppress/close the renderer. The renderer itself is unchanged, preserving the accepted Back-to-dismiss interaction.

Release gate run `36763219643` passed all 108 unit/smoke tests (1 skipped). Packaging was blocked only by task-record Scope validation. Fire TV OFF-before-playback and ON-to-OFF acceptance remain pending.

## 0.7.24 self-review
Self-review completed against artifact commit `dec2cb5f491aba7568e2f6d7ba28be91ba247369`. Release run `36763427233` passed 108 unit/smoke tests (1 skipped), tracker validation and deterministic package inspection. Automated coverage proves fresh settings reads and OFF/ON/OFF boolean propagation at the service boundary.

No renderer replacement or focus workaround was introduced. Verification remains partial because OFF-before-playback and ON→OFF behavior must still be confirmed on the target Fire TV; Back-to-dismiss remains the accepted ON-state interaction.

## 0.7.24 publication evidence
Released through PR #14 / merge `cda54a246c5d440116dfe05717da0392e62f13f8`. Final exact-candidate gate `36763721939` passed 108 tests (1 skipped), workflow validation, deterministic rebuild, ZIP/hash/index inspection and packaging. GitHub Pages deployment `36763934374` succeeded. Published artifact SHA-256: `6eee9e80e0a0e0766c62ea199052113fdf75b5fab0bf1eb25da2c0b06823451d`.

Delivery is released. Verification remains partial/review until this task's documented target-device acceptance checks are completed.
