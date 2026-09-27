---
id: UI-2
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
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
The current packaged manifest, `plugin.video.appi/addon.xml`, declares Appi version `0.7.16`, while the current settings definition has no About/version action.

## Outcome and next action
Committed for the next release. Implement a simple settings About action that reports the runtime-installed Appi version from add-on metadata.
