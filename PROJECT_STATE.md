# Appi project state

Updated: 2026-09-26. Short current summary; start with [AGENTS.md](AGENTS.md) for worker routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.14**. The experimental 0.8.0 archive is not the main baseline.
- **Target-device status:** 0.7.14 also failed manual HLS selection playback on the target device in the same way as 0.7.13. The 0.7.14 child-URL/query repair did not restore playback.
- **Current usable fallback:** **0.7.12**. Its proven manual path passes the original master URL to InputStream Adaptive with `ask-quality`.
- Historical known-good fallback retained in the repository: **0.7.8**.
- Install page: https://ihabmmali.github.io/appi/
- Publication and verification history: [RELEASE_NOTES.md](RELEASE_NOTES.md). Package availability and automated tests do not establish device acceptance.

## Current work

- **0.7.14 is published** from merge commit `4eb272c0da19b716906e4909366f6d6ba4173874`; post-merge automated verification passed in run 36290741628.
- **0.7.15 is committed and active:** HLS-4 is reopened to restore the 0.7.12 InputStream Adaptive `ask-quality` manual-selection path; publication is explicitly authorized by the user.
- DIAG-2 remains delivered in 0.7.14 and in review/partial verification for its separate target-device telemetry checks.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): HLS-4 is committed release-blocking scope; HLS-1 and UI-1 remain backlog investigations.
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.
- Lifecycle pilot 0.1 is established in [LIFECYCLE.md](LIFECYCLE.md). [Pilot evaluation](docs/workflows/PILOT.md) records what still needs real-world validation.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) holds project goals, constraints and current implementation; [CHANGELOG.md](CHANGELOG.md) records implemented changes. Detailed requirements and evidence live in individual task records. Read only relevant history.

Source establishes implemented behavior, accepted requirements establish intended behavior, and recorded checks establish verified behavior. Reconcile contradictions rather than treating this summary as conclusive.
