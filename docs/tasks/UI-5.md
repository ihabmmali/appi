---
id: UI-5
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# UI-5 — Remove redundant nested About action and show installed version directly

## Objective
Simplify Appi settings so the About category immediately shows the installed Appi version instead of requiring the user to click a second nested About item.

## Current behavior
The settings definition currently has:
- an `About` category; and
- inside that category, another `About` action button.

That action opens a dialog displaying `ADDON.getAddonInfo('version')`, producing an unnecessary second click.

## Scope
- Keep a single About category/entry in the settings navigation.
- When the user opens About, show the installed Appi version directly in the settings pane without another About action.
- Continue deriving the displayed version from installed add-on metadata rather than maintaining an unrelated hardcoded version constant.
- If Kodi's settings schema requires a stored display value, synchronize it from `ADDON.getAddonInfo('version')` before opening settings and render it read-only.
- Do not add another modal dialog or nested menu solely to reveal the version.

## Acceptance
- Opening Appi Settings > About immediately exposes the installed version.
- No second About button/action must be clicked.
- The displayed version matches the actually installed package after upgrade or rollback.
- The field is read-only/non-editable.
- Behavior is skin-independent on the supported Kodi target.
- UI-2's requirement to derive version from installed metadata remains satisfied.

## Authorization
Requested by the user on 2026-09-28 after observing that the current About category contains another About item that must be clicked to see the version. On 2026-09-28 the user explicitly instructed that all current candidates be committed for the next release. UI-5 is committed next-release scope.

## Evidence
Current `resources/settings.xml` defines `<category id="about"...>` containing `<setting id="about" type="action"...>`. Current `app.py` handles that action by opening a dialog containing `ADDON.getAddonInfo('version')`.

## Outcome and next action
Replace the nested action with a direct read-only installed-version display in the About settings pane.
