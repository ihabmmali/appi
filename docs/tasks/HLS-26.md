---
id: HLS-26
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-26 — Make the Buffered debug overlay setting authoritative and non-blocking

## Objective
Fix Appi 0.7.23 so the Buffered Look Ahead debug overlay is shown **only** when its setting is enabled, and investigate/replace the current dialog renderer if necessary so an enabled overlay does not prevent Kodi's normal playback OSD/navigation from opening.

This is a successor to HLS-23 target-device verification. The multiline formatting introduced in 0.7.23 is acceptable and should be preserved.

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

## Passive-overlay investigation
The overlay should ideally remain visible while allowing Kodi's standard playback OSD to function normally.

Before another WindowXMLDialog iteration:
1. prove whether `WindowXMLDialog` can be made non-focusable/non-intercepting for this use on the target device;
2. if not, evaluate a renderer that attaches passive controls to the active fullscreen-video window rather than opening a separate dialog/window;
3. keep the renderer isolated from buffering and playback logic;
4. do not steal focus, remap Select/Back, or consume the normal playback OSD/navigation actions.

Do not assume a renderer is suitable because mocked Python tests can create it. Fire TV target-device input behavior is required evidence.

If Kodi's Python GUI API cannot provide a genuinely passive persistent overlay reliably across supported skins/devices, the acceptable fallback is:
- setting OFF = no overlay at all;
- setting ON = display the diagnostic overlay;
- Back may dismiss it for the remainder of the current playback session;
- dismissal must not stop playback or buffering;
- the limitation/workaround must be explicit.

The user has stated that this fallback interaction is acceptable provided the ON/OFF setting itself works correctly.

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

Preferred:
- With debug ON, Fire TV center/select still opens Kodi's normal playback OSD and its settings/subtitles/timeline controls remain usable.
- The debug overlay does not become the active/focused navigation window.

Acceptable fallback if Kodi cannot provide a passive custom overlay:
- debug ON may use the current dialog renderer;
- Back dismisses it for the current playback session;
- Kodi OSD/navigation works after dismissal;
- this limitation is documented;
- OFF must still remain completely silent.

## Preservation constraints
Do not change:
- Buffered Look Ahead reservoir/recovery behavior;
- HLS-25 pause/resume repair semantics;
- producer concurrency;
- selected rendition;
- HLS modes 0-2.

## Authorization
Created from Appi 0.7.23 Fire TV target-device feedback on 2026-09-29. The user explicitly requires the setting switch to work as intended and reports that the current overlay window blocks normal playback navigation while active.

HLS-26 is a ready candidate and is not committed to release scope until explicitly selected under AGENTS.md.

## Evidence
0.7.23 source contains an apparent master gate, but target-device behavior contradicts it. The current renderer is a `WindowXMLDialog`; pressing Back removes that window and immediately restores Kodi's normal playback OSD/navigation, providing strong evidence that the renderer itself is participating in the GUI input stack.

## Outcome and next action
First prove and repair target-device setting propagation so OFF is absolute. Then determine whether a truly passive renderer is viable; if not, retain the user-accepted Back-to-dismiss behavior only for explicitly enabled debug sessions.
