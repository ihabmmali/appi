---
id: STARTUP-1
role: implementation
status: review
delivery: unreleased
verification: partial
owner: ChatGPT hotfix 0.7.18
base_commit: a0b9eacb23b4816df7ac4c0f60e9c51fb7d1eb79
artifact:
---
# STARTUP-1 — Repair Kodi startup crash introduced by 0.7.17

## Objective
Restore Kodi startup stability after installing Appi 0.7.17. The user reports Kodi exits/crashes almost immediately on startup, before opening Appi, preventing normal rollback or add-on management.

## Scope
Treat this as a release-blocking regression. Minimize changes outside code that runs automatically through Appi's `xbmc.service` extension. Preserve 0.7.17 feature behavior once Appi is actively used wherever possible.

## Acceptance
- Appi's always-running service performs no add-on settings migration during Kodi startup.
- Buffer overlay GUI objects are not created until an active Buffered Look Ahead session actually needs them.
- Existing playback modes and the 0.7.17 buffered implementation remain otherwise unchanged.
- Automated regression coverage prevents unconditional settings migration or eager buffer-overlay construction from returning to service startup.
- Release/package checks pass for 0.7.18.
- Target-device acceptance requires Kodi on the user's Fire TV to remain running after startup with Appi 0.7.18 installed.

## Authorization
On 2026-09-27 the user reported the 0.7.17 startup crash and explicitly instructed repair plus publication/release of 0.7.18.

## Evidence
Hotfix branch `fix/0.7.18-startup-crash` created from published baseline `a0b9eacb23b4816df7ac4c0f60e9c51fb7d1eb79`.

Source inspection isolated the relevant 0.7.17 startup delta in `resources/lib/subtitle_service.py`: unconditional `languages.migrate_preferences(ADDON)` and eager `BufferOverlay()` construction were newly executed by the Kodi service before the user entered Appi. The hotfix removes the startup settings mutation and constructs the overlay lazily only when a buffered session is ready. A regression test asserts those startup side effects remain absent.

Target-device verification is still required; code inspection cannot prove which Kodi-native interaction caused the process exit without a crash log.

## Outcome and next action
Implementation/self-review complete on the hotfix branch; package and publish as 0.7.18 after repository checks pass, then verify Kodi startup on Fire TV.
