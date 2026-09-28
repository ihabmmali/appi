# Appi project state

Updated: 2026-09-27. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.19**. The experimental 0.8.0 archive is not the main baseline.
- Publication: PR #7, merge `f495858b2e8c1f146802c04b8533334ee8b36b79`. Release/package run 36370407423 passed and produced the deterministic 0.7.19 artifact at commit `f25cfffb099eaa43f3865c5ac2a227d4958a7a2d`.
- Published 0.7.19 ZIP SHA-256: `1bee04f63b79a4654ff0dcf8e8db94ee89e709d16091722f38283c1b01bf2f4d`. Install page: https://ihabmmali.github.io/appi/ .
- 0.7.19 has positive target-device evidence for initial Buffered Look Ahead playback, but seek/recovery remains broken and InputStream Adaptive playback is silent. The user has reverted to **0.7.8** as the current practical fallback because the same media has working audio there.
- **0.7.17 failed target-device startup acceptance:** its new language lists contained empty option values that are a concrete native Kodi settings-parser crash trigger. 0.7.18 replaces those values with a non-empty `none` sentinel and safely normalizes/migrates the setting. **Target-device retest confirms 0.7.18 no longer crashes Kodi at startup.** Playback implementation is unchanged from 0.7.17.

## Current work

- **0.7.20 release candidate is verified on `release/0.7.20`.** Corrected release/package run `36375784976` passed and produced deterministic artifact commit `1ca52ad0b55a3f3e19acd8e4b288d8d13fe57ab4` with ZIP SHA-256 `41e1bdec7229d1a0a3d8787427ac9c434fb773e302c7d8f5bae428de0de7755f`. 0.7.19 remains published until integration completes.
- AUDIO-1 candidate repair leaves the established ISA handoff unchanged and makes preferred-audio selection stable/revalidated and non-mutating for No preference/no-match/already-selected cases. Automated verification passed; audible Fire TV acceptance remains pending.
- HLS-10 source review confirms the setting/service path. 0.7.20 adds exact non-fatal GUI-operation logging without changing the unproven fullscreen window target; known-HLS Fire TV visibility remains pending.
- HLS-11 candidate repair coordinates cold-resume/seek re-centering across active media tracks, prioritizes the target, and keeps bounded recovery misses retriable instead of poisoning the session. Automated verification passed; target-device seek/resume remains pending.
- HLS-8 is shipped/review-partial: the original 0.7.18 preparation/handoff regression has positive device evidence, while focused successor tasks own the remaining overlay and seek defects.
- LANG-3, HLS-9 and UI-4 are shipped in 0.7.19. LANG-3 target-device verification is now failed because ISA audio is broken; AUDIO-1 owns restoring audio before language-selection acceptance can resume.
- PLAY-1 remains a backlog Trakt-error investigation. HLS-1 and UI-1 remain backlog investigations.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): 0.7.20 candidate scope is AUDIO-1, HLS-10 and HLS-11; automated gate passed and target-device acceptance remains distinct. [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
