# Appi project state

Updated: 2026-09-27. Short current summary; start with [AGENTS.md](AGENTS.md) for worker routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.16**. The experimental 0.8.0 archive is not the main baseline.
- **Target-device status:** 0.7.16 preserves the 0.7.15/0.7.12 manual-selection architecture and adds Buffered Look Ahead Playback. Automated verification passed, but the new buffered mode still requires target-device testing to determine whether it eliminates the reported intermittent stalls; newer manual playback also remains pending device acceptance.
- **Current usable fallback:** **0.7.12**. Its proven manual path passes the original master URL to InputStream Adaptive with `ask-quality`.
- Historical known-good fallback retained in the repository: **0.7.8**.
- Install page: https://ihabmmali.github.io/appi/
- Publication and verification history: [RELEASE_NOTES.md](RELEASE_NOTES.md). Package availability and automated tests do not establish device acceptance.

## Current work

- **0.7.16 is published** from merge commit `af6791128009e5e9afd408221d8427c2baed65e1`; release/package run 36296897848, final candidate gate 36297078894, post-merge verification 36297143439 and Pages deployment 36297143062 passed. Package SHA-256 is `ecb310e42b016cf968b27e2af4d25ed6f1b106b888a9c0da387bde4bde595138`.
- HLS-4 is delivered in 0.7.15 but remains in review/partial verification pending the user's target-device manual-selection test.
- DIAG-2 remains delivered in 0.7.14 and in review/partial verification for its separate target-device telemetry checks.
- HLS-5 is delivered in 0.7.16 and remains in review/partial verification pending target-device buffering tests. The three pre-existing playback modes were source-audited and regression-tested as compatibility constraints.
- HLS-6 is a ready next-release candidate to add a user-configurable Buffered Look Ahead buffer size, a quality choice between Highest available bitrate and Prompt for quality, and an optional live buffer-state debug overlay; it is not yet committed release scope.
- UI-2 is a ready candidate for a settings About/version display. UI-3 tracks add-on icon artwork; the user-selected design is now stored at `artwork/appi-icon-selected.png` for future integration. Neither is committed release scope.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): reset to draft planning; HLS-6 is a candidate and no new release scope is committed. HLS-1 and UI-1 remain backlog investigations.
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.
- Lifecycle pilot 0.1 is established in [LIFECYCLE.md](LIFECYCLE.md). [Pilot evaluation](docs/workflows/PILOT.md) records what still needs real-world validation.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) holds project goals, constraints and current implementation; [CHANGELOG.md](CHANGELOG.md) records implemented changes. Detailed requirements and evidence live in individual task records. Read only relevant history.

Source establishes implemented behavior, accepted requirements establish intended behavior, and recorded checks establish verified behavior. Reconcile contradictions rather than treating this summary as conclusive.
