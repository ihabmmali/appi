# Appi project state

Updated: 2026-09-26. Short current summary; start with [AGENTS.md](AGENTS.md) for worker routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.13**. The experimental 0.8.0 archive is not the main baseline.
- **Target-device status:** 0.7.13 has failed manual HLS playback acceptance. The manual chooser displays incorrect rendition information and selecting any listed rendition fails playback.
- **Current user rollback:** **0.7.12** for usable playback while HLS-4 is repaired.
- Historical known-good fallback retained in the repository: **0.7.8**.
- Install page: https://ihabmmali.github.io/appi/
- Publication and verification history: [RELEASE_NOTES.md](RELEASE_NOTES.md). Package availability and automated tests do not establish device acceptance.

## Current work

- **Next release is committed:** HLS-4 (release-blocking manual HLS repair) and DIAG-2 (causal playback diagnostics). HLS-4 should be repaired using 0.7.12 behavior as the working comparison.
- **0.7.13 remains published** from merge commit `0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a`; automated release verification passed, but subsequent target-device playback testing failed for the manual HLS path.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): **HLS-4 and DIAG-2 are committed scope for the next release**; HLS-1 and UI-1 remain backlog investigations.
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.
- Lifecycle pilot 0.1 is established in [LIFECYCLE.md](LIFECYCLE.md). [Pilot evaluation](docs/workflows/PILOT.md) records what still needs real-world validation.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) holds project goals, constraints and current implementation; [CHANGELOG.md](CHANGELOG.md) records implemented changes. Detailed requirements and evidence live in individual task records. Read only relevant history.

Source establishes implemented behavior, accepted requirements establish intended behavior, and recorded checks establish verified behavior. Reconcile contradictions rather than treating this summary as conclusive.
