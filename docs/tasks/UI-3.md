---
id: UI-3
role: implementation
status: review
delivery: released
verification: partial
owner: Codex release/0.7.17
base_commit: 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3
artifact: plugin.video.appi/plugin.video.appi-0.7.17.zip
---
# UI-3 — Appi add-on artwork / icon

## Objective
Give Appi proper graphical add-on artwork so Kodi can display a recognizable Appi icon instead of relying on generic/default presentation.

## Scope
Integrate user-supplied artwork into the packaged Kodi add-on using Kodi-compatible asset paths and manifest metadata.

The user selected the first generated Appi design on 2026-09-27. The selected handoff asset is stored at `artwork/appi-icon-selected.png`. Do not substitute a different permanent design unless the user explicitly requests it.

When the asset is supplied:
- preserve the source artwork as appropriate for packaging;
- produce any required Kodi-sized/format-compatible derivative without changing the intended design;
- place the final icon in the standard add-on resources/package location;
- declare the asset in `addon.xml` as required by the supported Kodi version;
- ensure repository packaging/release scripts include it.

A fanart/background asset is outside current scope unless the supplied graphics or a later request explicitly includes one.

## Acceptance
- User-supplied Appi artwork is incorporated without unintended cropping, distortion or design changes.
- Kodi displays the Appi icon in the add-on browser and other standard places where Kodi renders add-on artwork.
- The packaged ZIP contains the referenced artwork at the exact path declared by the manifest.
- Installation/update does not fail if Kodi caches an older icon; document any normal Kodi artwork-cache refresh behavior encountered during verification.
- Existing add-on metadata and functionality remain unchanged apart from the intended artwork.
- Package/repository validation confirms there are no missing asset references.

## Authorization
Requested by the user on 2026-09-27. The user stated that Appi needs a graphical icon and that they will supply the graphics. The artwork dependency is satisfied. On 2026-09-27 the user explicitly instructed that all currently tracked changes be committed for the next release. UI-3 is therefore ready and committed release scope.

## Evidence

Published in 0.7.17 through PR #5, merge `18ffae9349b2d225b575cee6a276ea8dcd59143b`. Release/package run 36350783947, post-merge verification 36350856112 and Pages deployment 36350855315 passed. Deployed ZIP hash matched `77dd83244e01bae295d3118073d28b13b2a6d634576cf4ffae84fde14a49b0b1`.

2026-09-27 implementation/self-review (0.7.17 candidate): The approved artwork is copied byte-for-byte to resources/icon.png and declared in addon.xml. Package inspection verifies the exact referenced path and byte equality with artwork/appi-icon-selected.png. No crop, distortion or design change. Kodi rendering/cache behavior still needs target-device observation.

73 unit/smoke/integration tests passed with Python 3.12, including real FFmpeg MPEG-TS and fMP4 decode at start, forward seek and backward seek; workflow validation and diff whitespace checks passed. `_effective_hls_mode`, `_configure_hls` and `_configure_mp4` are AST-identical to base 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3. Reviewed implementation commit: `842ef37c8deb6ce340946dbbafa29fbd8745ec0c`. This is self-review, not independent review.

The current `plugin.video.appi/addon.xml` contains add-on metadata but does not declare Appi artwork assets. On 2026-09-27 the user selected the first generated Appi design; a 512×512 PNG handoff copy is now stored at `artwork/appi-icon-selected.png`. It is repository artwork only at this stage and has not yet been wired into the packaged add-on.

## Outcome and next action
Implemented, self-reviewed, integrated and published in 0.7.17. Target-device acceptance remains pending, so this task stays in review/partial verification. Retest the task's device/UI scenarios after installing 0.7.17; do not mark done from package availability alone.

## Implementation session — 2026-09-27
User authorized implementation, testing, integration and publication in this session. Base 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3. One worker owns the scoped source/settings/tests and shared release records; no concurrent worker changes observed. Target 0.7.17. Modes 0–2 must remain unchanged.
