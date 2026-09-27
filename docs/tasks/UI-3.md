---
id: UI-3
role: implementation
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# UI-3 — Appi add-on artwork / icon

## Objective
Give Appi proper graphical add-on artwork so Kodi can display a recognizable Appi icon instead of relying on generic/default presentation.

## Scope
Integrate user-supplied artwork into the packaged Kodi add-on using Kodi-compatible asset paths and manifest metadata.

The user will supply the graphic. Do not generate or substitute permanent artwork without that asset unless the user explicitly requests it.

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
Requested by the user on 2026-09-27. The user stated that Appi needs a graphical icon and that they will supply the graphics. This task is recorded for planning, but implementation depends on receipt of the artwork and is not committed release scope unless the user explicitly commits/includes it in the next release under AGENTS.md.

## Evidence
The current `plugin.video.appi/addon.xml` contains add-on metadata but does not declare Appi artwork assets. No user-supplied artwork is present in this request.

## Outcome and next action
Wait for the user-supplied graphic, then integrate and package it according to Kodi add-on artwork conventions.
