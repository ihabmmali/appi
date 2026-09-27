# Appi project state

Updated: 2026-09-27. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.17**. The experimental 0.8.0 archive is not the main baseline.
- Publication: [PR #5](https://github.com/ihabmmali/appi/pull/5), merge `18ffae9349b2d225b575cee6a276ea8dcd59143b`. Release/package run 36350783947, post-merge verification 36350856112 and Pages deployment 36350855315 passed.
- Deployed ZIP downloaded and verified: SHA-256 `77dd83244e01bae295d3118073d28b13b2a6d634576cf4ffae84fde14a49b0b1`. Install page: https://ihabmmali.github.io/appi/ .
- Current usable playback fallback: **0.7.12**. Historical fallback **0.7.8** remains available. 0.7.15/0.7.16 archives are retained for release evidence; they are not additional index entries.
- **0.7.17 failed target-device startup acceptance:** Kodi crashes almost immediately after installation, without an error dialog. The empty language-list option is a concrete native settings-parser crash trigger; LANG-2 is reopened for the scoped 0.7.18 hotfix. **Other target-device acceptance is pending.** 0.7.16 Buffered Look Ahead failed device acceptance. 0.7.17 repairs startup/seek/retry lifecycle and adds settings/UI; automated tests and local real-decoder checks do not establish that the user's provider/Fire TV symptoms are fixed.

## Current work

- **0.7.18 hotfix candidate:** LANG-2 native-settings crash correction is implemented; 76 local tests pass. Publish and verify the scoped correction, then confirm Kodi launches on the target device.

- Shipped committed scope: HLS-7, HLS-6, LANG-2, UI-2 and UI-3. All remain review/partial until required device observations are recorded.
- Buffered mode has cancellable preparation, explicit bounded failures, session-token cleanup, stable playlists, range/media-extension support, configurable MB capacity, highest/prompt quality and normal/debug buffer indicators. Modes 0–2 retain their previous configuration paths.
- Language lists migrate legacy preferences; About reads the installed runtime version; the approved Appi icon is packaged unchanged.
- Local verification: 73 tests passed, including real TS/fMP4 decode and forward/backward seeks, HTTP transfer integrity, repeated failure/cancel/retry, capacity/quality and previous playback/subtitle behavior. Self-review recorded in the tasks.
- Next: repeat failed device scenarios on 0.7.17 and record results; confirm language lists, About and icon display. HLS-5 remains the historical 0.7.16 buffering record; HLS-7 owns its failed device acceptance follow-up.
- HLS-4 and DIAG-2 retain their separate outstanding device acceptance checks. HLS-1 and UI-1 remain backlog investigations.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): no new implementation scope committed. [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
