---
id: HLS-9
role: implementation
status: review
delivery: unreleased
verification: partial
owner: GPT-5.6 Sol release/0.7.19
base_commit: c7a344ae2afa1160adb7daf522092c89b46105bf
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

2026-09-27 implementation session: assigned to GPT-5.6 Sol on `release/0.7.19` from base `c7a344ae2afa1160adb7daf522092c89b46105bf`. User authorization covers implementation, integration and publication of the committed next-release scope. Source/test changes are isolated on the release branch; HLS-8 preserves playback modes 0–2.

The 0.7.19 candidate manifest removes `optional="true"` from `inputstream.adaptive`. Release/package run 36370407423 passed source/package generation and produced the deterministic ZIP at artifact commit `f25cfffb099eaa43f3865c5ac2a227d4958a7a2d`. A final archive-level regression assertion now opens that generated ZIP and verifies the dependency remains required inside its archived `addon.xml`.
Current 0.7.18 `plugin.video.appi/addon.xml` declares:
`<import addon="inputstream.adaptive" version="21.0.0" optional="true"/>`
while Appi has manual InputStream Adaptive and adaptive bitrate playback modes.

## Outcome and next action
Implementation is in review. Automated source/package verification is passing; the final review gate will exercise the new archive-level assertion. Target-device acceptance remains to confirm Kodi resolves InputStream Adaptive during a clean Appi install/update and reports a clear dependency failure if it cannot.
