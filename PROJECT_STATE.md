# Appi project state

Updated: 2026-09-27. Short current summary; start with [AGENTS.md](AGENTS.md) for worker routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.15**. The experimental 0.8.0 archive is not the main baseline.
- **Target-device status:** 0.7.15 restores the exact 0.7.12 manual-selection architecture and passed automated verification, but target-device manual HLS acceptance is still pending. 0.7.14 and 0.7.13 both failed that device test.
- **Current usable fallback:** **0.7.12**. Its proven manual path passes the original master URL to InputStream Adaptive with `ask-quality`.
- Historical known-good fallback retained in the repository: **0.7.8**.
- Install page: https://ihabmmali.github.io/appi/
- Publication and verification history: [RELEASE_NOTES.md](RELEASE_NOTES.md). Package availability and automated tests do not establish device acceptance.

## Current work

- **0.7.15 is published** from merge commit `2ba3ba2dc78519f55e6c01c0372a17f31b310fba`; release/package verification passed in run 36291375057, post-merge verification passed in 36291431201, and Pages deployment passed in 36291430966.
- HLS-4 is delivered in 0.7.15 but remains in review/partial verification pending the user's target-device manual-selection test.
- DIAG-2 remains delivered in 0.7.14 and in review/partial verification for its separate target-device telemetry checks.
- **0.7.16 is committed and active:** HLS-5 adds an isolated Buffered Look Ahead Playback mode with a disk-backed local HLS proxy; the existing native/manual/adaptive paths are compatibility-frozen by the task.
- [NEXT_RELEASE.md](NEXT_RELEASE.md): HLS-5 is committed as the sole new 0.7.16 scope; HLS-1 and UI-1 remain backlog investigations.
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md): full task index.
- Lifecycle pilot 0.1 is established in [LIFECYCLE.md](LIFECYCLE.md). [Pilot evaluation](docs/workflows/PILOT.md) records what still needs real-world validation.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) holds project goals, constraints and current implementation; [CHANGELOG.md](CHANGELOG.md) records implemented changes. Detailed requirements and evidence live in individual task records. Read only relevant history.

Source establishes implemented behavior, accepted requirements establish intended behavior, and recorded checks establish verified behavior. Reconcile contradictions rather than treating this summary as conclusive.
