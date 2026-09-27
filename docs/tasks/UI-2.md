---
id: UI-2
role: implementation
status: review
delivery: released
verification: partial
owner: Codex release/0.7.17
base_commit: 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3
artifact: plugin.video.appi/plugin.video.appi-0.7.17.zip
---
# UI-2 — About / installed Appi version

## Objective
Add a simple user-visible **About** entry in Appi settings so the installed Appi version can be verified directly from Kodi without inspecting the ZIP, repository or add-on browser metadata.

## Scope
Add an About action/section in Appi settings that reads the installed add-on metadata at runtime rather than duplicating a hardcoded version string.

At minimum display:
- Appi name;
- installed Appi version.

Additional low-risk build information may be shown if it comes directly from packaged metadata and stays concise, but the primary requirement is reliable installed-version verification.

The value shown must reflect the actually installed package, including after upgrades and rollbacks.

## Acceptance
- Appi settings contains an obvious **About** entry.
- Opening About displays the currently installed Appi version.
- The displayed version is obtained from the installed add-on metadata/runtime API rather than a second manually maintained version constant.
- Installing a newer or older Appi package causes About to report that package's version without additional code changes.
- The feature works in the supported Kodi target and does not depend on a particular skin.
- Automated/smoke coverage verifies that the About action obtains the version from add-on metadata where practical.

## Authorization
Requested by the user on 2026-09-27 as a usability improvement. The user wants a simple About entry in settings to verify the current Appi version. On 2026-09-27 the user explicitly instructed that all currently tracked changes be committed for the next release. UI-2 is therefore committed release scope.

## Evidence

Published in 0.7.17 through PR #5, merge `18ffae9349b2d225b575cee6a276ea8dcd59143b`. Release/package run 36350783947, post-merge verification 36350856112 and Pages deployment 36350855315 passed. Deployed ZIP hash matched `77dd83244e01bae295d3118073d28b13b2a6d634576cf4ffae84fde14a49b0b1`.

2026-09-27 implementation/self-review (0.7.17 candidate): The settings About action obtains name/version from the installed Addon runtime metadata. Smoke coverage changes mocked installed metadata from 0.7.17 to 0.7.12 and verifies the displayed version changes accordingly. No second version constant is used.

73 unit/smoke/integration tests passed with Python 3.12, including real FFmpeg MPEG-TS and fMP4 decode at start, forward seek and backward seek; workflow validation and diff whitespace checks passed. `_effective_hls_mode`, `_configure_hls` and `_configure_mp4` are AST-identical to base 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3. Reviewed implementation commit: `842ef37c8deb6ce340946dbbafa29fbd8745ec0c`. This is self-review, not independent review.

The current packaged manifest, `plugin.video.appi/addon.xml`, declares Appi version `0.7.16`, while the current settings definition has no About/version action.

## Outcome and next action
Implemented, self-reviewed, integrated and published in 0.7.17. Target-device acceptance remains pending, so this task stays in review/partial verification. Retest the task's device/UI scenarios after installing 0.7.17; do not mark done from package availability alone.

## Implementation session — 2026-09-27
User authorized implementation, testing, integration and publication in this session. Base 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3. One worker owns the scoped source/settings/tests and shared release records; no concurrent worker changes observed. Target 0.7.17. Modes 0–2 must remain unchanged.
