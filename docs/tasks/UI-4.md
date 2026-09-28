---
id: UI-4
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
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
Current repository tree shows `artwork/appi-icon-selected.png` at blob `08016a229ed053e000deffad659a2b94bd64acfc` while `plugin.video.appi/resources/icon.png` remains blob `0909423e26a8b2329c1ace2bfa70cdf9d4274ad6`. The handoff and packaged icon therefore differ and the latest artwork is not yet delivered.

## Outcome and next action
Committed for the next release. Replace the packaged icon with the current approved handoff and verify the release ZIP contains the exact revised artwork.
