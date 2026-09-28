# Appi project state

Updated: 2026-09-27. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.19**. The experimental 0.8.0 archive is not the main baseline.
- Publication: PR #7, merge `f495858b2e8c1f146802c04b8533334ee8b36b79`. Release/package run 36370407423 passed and produced the deterministic 0.7.19 artifact at commit `f25cfffb099eaa43f3865c5ac2a227d4958a7a2d`.
- Published 0.7.19 ZIP SHA-256: `1bee04f63b79a4654ff0dcf8e8db94ee89e709d16091722f38283c1b01bf2f4d`. Install page: https://ihabmmali.github.io/appi/ .
- 0.7.19 has positive target-device evidence for initial Buffered Look Ahead preparation/playback, but seek/recovery remains broken; **0.7.12** remains the usable fallback for reliable non-buffered playback. Historical fallback **0.7.8** remains available.
- **0.7.17 failed target-device startup acceptance:** its new language lists contained empty option values that are a concrete native Kodi settings-parser crash trigger. 0.7.18 replaces those values with a non-empty `none` sentinel and safely normalizes/migrates the setting. **Target-device retest confirms 0.7.18 no longer crashes Kodi at startup.** Playback implementation is unchanged from 0.7.17.

## Current work

- **0.7.19 is published.** Initial Buffered Look Ahead preparation/playback now appears to work on the target Fire TV and the simple startup windows display.
- HLS-10 is a ready candidate because the optional detailed buffer debug overlay remains invisible when enabled.
- HLS-11 is a ready candidate because seeking in Buffered Look Ahead times out. After the failure, resume consistently plays briefly, displays **Appi buffering**, stutters and exits with a buffering-failed timeout.
- HLS-8 is shipped/review-partial: the original 0.7.18 preparation/handoff regression has positive device evidence, while focused successor tasks own the remaining overlay and seek defects.
- LANG-3, HLS-9 and UI-4 are shipped in 0.7.19; their canonical records retain any outstanding target-device acceptance.
- PLAY-1 remains a backlog Trakt-error investigation. HLS-1 and UI-1 remain backlog investigations.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): HLS-10 and HLS-11 are candidates; no new implementation scope is committed. [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
