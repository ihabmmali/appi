---
id: UI-6
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# UI-6 — Force Kodi to refresh the approved Appi icon

## Objective
Ensure Kodi displays the approved flat Appi artwork rather than an older cached icon after updating the add-on.

## Current evidence
The exact 0.7.21 artifact commit contains:
- `artwork/appi-icon-selected.png` blob `08016a229ed053e000deffad659a2b94bd64acfc`;
- `plugin.video.appi/resources/icon.png` with the same blob and size.

The release builder packages source files from `plugin.video.appi` directly and does not substitute another icon. `addon.xml` still references the stable path `resources/icon.png`.

Because the approved bytes are already present in the 0.7.21 source while the target device still shows an older graphic, the leading explanation is Kodi texture/artwork caching keyed to the unchanged resource path rather than a source-level artwork revert.

## Scope
- Preserve the approved flat PNG bytes exactly.
- Publish the approved icon under a new resource filename, for example `resources/icon-v2.png`.
- Update `addon.xml` to reference that new filename so Kodi sees a new artwork resource key.
- Keep the old file only if required for compatibility; do not let the manifest continue pointing to it.
- Add package-level verification that the manifest-referenced icon inside the generated ZIP is byte-identical to `artwork/appi-icon-selected.png`.
- Do not touch playback or buffering code.

## Acceptance
- The manifest references a new artwork path rather than the previously cached `resources/icon.png`.
- The new manifest-referenced PNG is byte-identical to the approved flat artwork.
- The final release ZIP contains that exact file at the referenced path.
- Installing/updating on the target Fire TV displays the approved flat icon without requiring manual cache clearing.
- No gradient, recolor, scaling or composition change is introduced.
- Package tests verify handoff -> source asset -> ZIP member identity.

## Authorization
Reported by the user on 2026-09-28 after installing 0.7.21: Kodi appears to show the very first Appi graphic again. This is logged as a ready candidate and is not committed until explicitly included under AGENTS.md.

## Outcome and next action
Force an artwork cache miss by versioning the icon resource path while preserving the approved artwork bytes.
