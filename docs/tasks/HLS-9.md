---
id: HLS-9
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-9 — Make InputStream Adaptive a prerequisite dependency

## Objective
Ensure InputStream Adaptive is installed as an Appi prerequisite because supported Appi playback modes explicitly use it.

## Scope
Appi currently declares `inputstream.adaptive` in `addon.xml` with `optional="true"`, while manual InputStream Adaptive and ABR modes depend on it.

Change packaging/dependency metadata so a compatible InputStream Adaptive add-on is treated as a required prerequisite for Appi installation/update rather than an optional component discovered only when playback is attempted.

Retain graceful runtime diagnostics for unexpected disabled/broken dependency states, but do not rely on runtime detection as the primary installation mechanism.

## Acceptance
- `addon.xml` declares a compatible `inputstream.adaptive` dependency as required rather than optional.
- Fresh Appi installation causes Kodi to install/resolve InputStream Adaptive through the normal dependency mechanism where available.
- Upgrade packaging retains the dependency declaration.
- Manual InputStream Adaptive and ABR modes never silently proceed without the prerequisite.
- Native Kodi and Buffered Look Ahead behavior remain otherwise unchanged.
- If the required dependency is unavailable/incompatible, installation or dependency resolution fails clearly instead of producing a later ambiguous playback failure.
- Package/ZIP tests inspect the final archived `addon.xml`, not only source.
- Target-device verification confirms InputStream Adaptive is present/resolved after a clean Appi installation or upgrade.

## Authorization
Requested by the user on 2026-09-27: if InputStream Adaptive is used, it must be a prerequisite dependency. On 2026-09-27 the user explicitly instructed that all tracked changes be committed to the next release. HLS-9 is therefore committed release scope.

## Evidence
Current 0.7.18 `plugin.video.appi/addon.xml` declares:
`<import addon="inputstream.adaptive" version="21.0.0" optional="true"/>`
while Appi has manual InputStream Adaptive and adaptive bitrate playback modes.

## Outcome and next action
Committed for the next release. Make InputStream Adaptive a required packaged dependency and verify dependency resolution on the target Kodi installation.
