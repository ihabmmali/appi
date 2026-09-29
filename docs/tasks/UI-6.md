---
id: UI-6
role: implementation
status: review
delivery: released
verification: partial
owner: builder-publisher-0.7.22
base_commit: fd0bd5b08228c34b09de684f7b4b1f865a09e2d2
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.22.zip
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
Reported by the user on 2026-09-28 after installing 0.7.21: Kodi appears to show the very first Appi graphic again. On 2026-09-28 the user explicitly instructed that all current candidates be committed for the next release. UI-6 is committed next-release scope.

## Evidence
The 0.7.22 implementation keeps the approved flat icon bytes unchanged and introduces a new manifest resource path, `resources/icon-v2.png`, to force Kodi texture-cache invalidation. The new resource blob SHA is exactly `08016a229ed053e000deffad659a2b94bd64acfc`, identical to the previous approved `resources/icon.png` blob. Automated release coverage asserts that the manifest no longer references the old path and that the packaged icon bytes match `artwork/appi-icon-selected.png`.

## Outcome and next action
Force an artwork cache miss by versioning the icon resource path while preserving the approved artwork bytes.


## 0.7.22 candidate evidence
0.7.22 candidate changes the manifest artwork path to resources/icon-v2.png without transforming the approved PNG. Source and destination Git blob SHA are both 08016a229ed053e000deffad659a2b94bd64acfc. Automated package byte equality passed; actual Kodi texture-cache refresh remains a device check.

Final package gate run `36515744781` passed all 100 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild and ZIP/index inspection. Candidate artifact commit: `971d29d4145411e0c78703326246b770c82d95c3`; ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`.


## 0.7.22 publication
Published in Appi 0.7.22 through PR #11 / merge `92131c95c1d047eb7a683e8e5e2e6abe10e1a518`. Final publication gate run `36626983906` passed 100 tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/index inspection and packaging. GitHub Pages deployment run `36627135052` succeeded. Published ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`. Delivery is released; documented target-device acceptance remains review/partial.
