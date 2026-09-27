# Appi project state

Updated: 2026-09-27. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.18**. The experimental 0.8.0 archive is not the main baseline.
- Publication: [PR #6](https://github.com/ihabmmali/appi/pull/6), merge `22bf3ba0e59ee5cf045836aa3d8256be3cc684e0`. Release/package run 36351377864, post-merge verification 36352524841 and Pages deployment 36352524365 passed.
- Published ZIP SHA-256: `0a0a739e8f8eca85c0268d46027c060b57b185b2b8ec4464b3ebb72289181447`. Install page: https://ihabmmali.github.io/appi/ .
- Current usable playback fallback remains **0.7.12** until 0.7.18 receives target-device startup acceptance. Historical fallback **0.7.8** remains available.
- **0.7.17 failed target-device startup acceptance:** its new language lists contained empty option values that are a concrete native Kodi settings-parser crash trigger. 0.7.18 replaces those values with a non-empty `none` sentinel and safely normalizes/migrates the setting. Playback implementation is unchanged from 0.7.17.

## Current work

- **0.7.18 is published and repository verification passed.** Target-device acceptance is still pending: confirm Kodi remains running on startup after installing 0.7.18, then confirm both language lists open and No preference works.
- Shipped 0.7.17 scope remains HLS-7, HLS-6, LANG-2, UI-2 and UI-3. Their separate device acceptance items remain review/partial where documented.
- Buffered mode has cancellable preparation, explicit bounded failures, session-token cleanup, stable playlists, range/media-extension support, configurable MB capacity, highest/prompt quality and normal/debug buffer indicators. Modes 0–2 retain their previous configuration paths.
- HLS-4 and DIAG-2 retain their separate outstanding device acceptance checks. HLS-1 and UI-1 remain backlog investigations.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): no new implementation scope committed. [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
