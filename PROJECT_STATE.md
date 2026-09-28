# Appi project state

Updated: 2026-09-28. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.21**. The experimental 0.8.0 archive is not the main baseline.
- Publication: PR #10, merge `d9e0be64681fa2dbe9cc434f81375a9c0992a3e1`. Final strengthened candidate run `36381180991` passed 94 tests (1 skipped), workflow validation, deterministic rebuild and package inspection; final pre-integration evidence run `36381370108` also passed with no generated artifact drift.
- Deterministic artifact commit: `26216385f185476b778f73b8dae5e7abfe73f339`. Published 0.7.21 ZIP SHA-256: `0e8c615d40cf9f42e0345c61e11a7b244fc443c8858902d53fffda92c1935c81`. Post-merge verification run `36381516837` and Pages deployment run `36381516378` passed. Install page: https://ihabmmali.github.io/appi/ .
- 0.7.21 ships the HLS-12/HLS-13/HLS-14/HLS-15 Buffered Look Ahead repair set. Automated evidence is positive; target-device acceptance on the user's problematic higher-bitrate HLS stream remains required. Keep **0.7.8** as the practical fallback until that acceptance is complete.
- **0.7.17 failed target-device startup acceptance** because its language lists contained empty option values; 0.7.18 corrected that crash trigger and target-device retest confirmed Kodi starts normally.

## Current work

- **0.7.21 is published.** Shipped scope: HLS-12, HLS-13, HLS-14 and HLS-15. All four remain review/partial until target-device acceptance.
- HLS-12 replaces stateful random-access recovery with fresh authoritative buffer epochs for seek and saved-position resume; automated tests cover stale completion rejection, timeline alignment, retry and repeated seek behavior.
- HLS-13 replaces the fixed 12-second/equal-share model with a shared capacity-driven reservoir: 50% startup target, 80% high-water, 60% low-water, 15% critical reserve, dynamic video/audio allocation, continuous refill, measured throughput and inactivity-based transfer timeout.
- HLS-14 replaces fullscreen-window control injection with a guarded modeless `WindowDialog` detailed overlay. Fire TV/Kodi visibility still requires device observation.
- HLS-15 shows actual active-epoch contiguous playable KB/MB and target during normal preparation/recovery without requiring detailed debug.
- Existing HLS modes 0–2 were intentionally left unchanged. Buffered mode does not automatically downgrade quality and reports measured throughput deficit when reserve is critical.
- AUDIO-1, HLS-10 and HLS-11 remain review records for the 0.7.20 behavior they shipped; HLS-12/HLS-14 supersede the unresolved Buffered Look Ahead seek/overlay directions in 0.7.21.
- PLAY-1 remains a backlog Trakt-error investigation. HLS-1 and UI-1 remain backlog investigations.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): no scope is currently committed. [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
