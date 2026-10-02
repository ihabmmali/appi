# Appi project state

Updated: 2026-10-01. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.24**. The experimental 0.8.0 archive is not the main baseline.
- Publication: PR #14, merge `cda54a246c5d440116dfe05717da0392e62f13f8`. Final exact-candidate gate run `36763721939` passed 108 tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/index inspection and packaging.
- Published 0.7.24 ZIP SHA-256: `6eee9e80e0a0e0766c62ea199052113fdf75b5fab0bf1eb25da2c0b06823451d`. GitHub Pages deployment run `36763934374` succeeded. Install page: https://ihabmmali.github.io/appi/ .
- The published index intentionally keeps **0.7.23**, **0.7.22**, **0.7.21**, **0.7.14**, **0.7.12** and **0.7.8** visible alongside 0.7.24.
- Keep **0.7.8** as the historical known-good fallback while newer Buffered Look Ahead behavior completes target-device acceptance.

## Current work

- **0.7.24 is published.** Shipped scope: HLS-25, HLS-26 and META-1. Delivery is released; all three remain review/partial because their documented target-device acceptance checks are still outstanding.
- HLS-25 successfully removed the previously observed fatal pause TimeoutError/session teardown on Fire TV, but target-device verification is now failed because video continuity after resume is still unreliable. Audio commonly continues while video freezes/catches up and can occasionally remain frozen.
- HLS-26 re-reads the debug-overlay setting from current Kodi settings in the persistent service. OFF is authoritative by source/tests; target-device OFF-before-playback and ON→OFF checks remain pending. The accepted Back-to-dismiss behavior remains unchanged when ON.
- META-1 surfaces optional runtime through Kodi's native duration tag and locally derived season episode counts. Target-device presentation acceptance remains pending.
- Existing HLS modes 0–2, reservoir thresholds, producer concurrency and HLS-24 exact-segment release behavior remain intentionally unchanged.
- HLS-27 is a next-release **release-blocking candidate** to diagnose and repair video-only pause/resume resynchronization. The leading source hypothesis is false fresh-epoch creation when post-pause video resumes more than one segment beyond Appi's expected index; actual player-position and per-track request telemetry must prove this before repair.
- HLS-19 remains failed/under review from prior target-device extended-pause evidence; 0.7.24 confirms the local-consumer fatal timeout was improved, but end-to-end pause/resume remains unresolved.
- PLAY-1, HLS-1 and UI-1 remain backlog investigations. [NEXT_RELEASE.md](NEXT_RELEASE.md) is reset with no product scope committed. [KNOWN_ISSUES.md](KNOWN_ISSUES.md) remains the canonical task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
