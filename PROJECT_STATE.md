# Appi project state

Updated: 2026-09-27. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.20**. The experimental 0.8.0 archive is not the main baseline.
- Publication: PR #8, merge `6e6db9bec185ec6b5eea664d27cb7b94f4efa2ef`. Corrected release/package run `36375784976` and final candidate gate `36376091435` passed; deterministic artifact commit `1ca52ad0b55a3f3e19acd8e4b288d8d13fe57ab4`.
- Published 0.7.20 ZIP SHA-256: `41e1bdec7229d1a0a3d8787427ac9c434fb773e302c7d8f5bae428de0de7755f`. Post-merge verification run `36376270017` and Pages deployment run `36376269821` passed. Install page: https://ihabmmali.github.io/appi/ .
- 0.7.20 is published. Buffered Look Ahead seek/resume has now **failed target-device acceptance** because it still times out. ISA audio and detailed-overlay acceptance remain separately tracked. Keep **0.7.8** as the practical fallback until those checks are completed.
- **0.7.17 failed target-device startup acceptance:** its new language lists contained empty option values that are a concrete native Kodi settings-parser crash trigger. 0.7.18 replaces those values with a non-empty `none` sentinel and safely normalizes/migrates the setting. **Target-device retest confirms 0.7.18 no longer crashes Kodi at startup.** Playback implementation is unchanged from 0.7.17.

## Current work

- **0.7.20 is published.** Shipped scope: AUDIO-1, HLS-10 and HLS-11. Automated candidate, post-merge and Pages checks passed; all three tasks remain review/partial until target-device acceptance.
- AUDIO-1 candidate repair leaves the established ISA handoff unchanged and makes preferred-audio selection stable/revalidated and non-mutating for No preference/no-match/already-selected cases. Automated verification passed; audible Fire TV acceptance remains pending.
- HLS-10 source review confirms the setting/service path. 0.7.20 adds exact non-fatal GUI-operation logging without changing the unproven fullscreen window target; known-HLS Fire TV visibility remains pending.
- HLS-11 shipped in 0.7.20 but failed target-device acceptance: seek/resume still times out. HLS-12 is the successor candidate and replaces stateful recovery with a fresh buffer epoch at every seek/resume target.
- HLS-8 is shipped/review-partial: the original 0.7.18 preparation/handoff regression has positive device evidence, while focused successor tasks own the remaining overlay and seek defects.
- LANG-3, HLS-9 and UI-4 are shipped in 0.7.19. LANG-3 target-device verification is now failed because ISA audio is broken; AUDIO-1 owns restoring audio before language-selection acceptance can resume.
- PLAY-1 remains a backlog Trakt-error investigation. HLS-1 and UI-1 remain backlog investigations.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): HLS-12 is a release-blocking candidate; no new scope is committed yet. [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
