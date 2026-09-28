---
id: UI-4
role: implementation
status: review
delivery: unreleased
verification: partial
owner: GPT-5.6 Sol release/0.7.19
base_commit: c7a344ae2afa1160adb7daf522092c89b46105bf
artifact: artwork/appi-icon-selected.png
---
# UI-4 — Integrate revised Appi artwork

## Objective
Package the user's latest Appi artwork revision in the next release.

The approved handoff at `artwork/appi-icon-selected.png` was updated on 2026-09-27 after UI-3 had already shipped an earlier icon. The current handoff must replace the older packaged `plugin.video.appi/resources/icon.png`.

## Scope
- Copy the latest approved handoff artwork into the packaged Kodi add-on icon path.
- Preserve the new flat/low-color design exactly; do not reintroduce gradients or alter the composition.
- Keep the existing manifest artwork reference valid.
- Ensure release/repository packaging contains the new icon.
- Avoid unrelated artwork or UI changes.

## Acceptance
- `plugin.video.appi/resources/icon.png` is byte-identical to the current approved `artwork/appi-icon-selected.png` unless a format conversion is technically required and explicitly documented.
- The final release ZIP contains the revised icon at the manifest-declared path.
- Kodi displays the revised flat-color Appi icon after install/update, accounting for normal Kodi artwork caching behavior.
- No unintended crop, scaling distortion, gradient reconstruction or color-band-inducing processing is introduced.
- Package/repository tests verify source handoff, packaged icon and archived icon consistency.
- Existing Appi functionality is unchanged.

## Authorization
The user stated on 2026-09-27 that the artwork has been updated and uploaded to GitHub, then explicitly instructed that all changes be committed to the next release. UI-4 is therefore committed release scope.

## Evidence

2026-09-27 implementation session: assigned to GPT-5.6 Sol on `release/0.7.19` from base `c7a344ae2afa1160adb7daf522092c89b46105bf`. User authorization covers implementation, integration and publication of the committed next-release scope. Source/test changes are isolated on the release branch; HLS-8 preserves playback modes 0–2.

The packaged source icon now uses blob `08016a229ed053e000deffad659a2b94bd64acfc`, exactly matching `artwork/appi-icon-selected.png`. Release/package run 36370407423 passed and generated the 0.7.19 ZIP. A final archive-level test now compares the icon bytes inside the generated ZIP directly with the approved handoff asset.
Current repository tree shows `artwork/appi-icon-selected.png` at blob `08016a229ed053e000deffad659a2b94bd64acfc` while `plugin.video.appi/resources/icon.png` remains blob `0909423e26a8b2329c1ace2bfa70cdf9d4274ad6`. The handoff and packaged icon therefore differ and the latest artwork is not yet delivered.

## Outcome and next action
Implementation is in review. Automated byte-identity verification covers source and the final ZIP; target-device acceptance remains to confirm Kodi displays the revised flat icon after normal artwork-cache refresh behavior.
