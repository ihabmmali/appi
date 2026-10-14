# Appi project state

Updated: 2026-10-14. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.25**. The experimental 0.8.0 archive is not the baseline.
- Publication: [PR #16](https://github.com/ihabmmali/appi/pull/16), merge `9de26765b4af163974162ebb76f43e14a1001a5c`. Final exact-candidate verification/package run `38063374015` passed 112 tests (1 skipped), workflow checker, deterministic package and ZIP/index/hash inspection.
- Published 0.7.25 ZIP SHA-256: `a46637a96b15ae01e75df3a59b0558d993f54c2f4c43506406a91036ba77d1c0`. GitHub Pages deployment `38063465450` succeeded. Install page: https://ihabmmali.github.io/appi/ .
- The published index intentionally keeps **0.7.24**, **0.7.23**, **0.7.22**, **0.7.21**, **0.7.14**, **0.7.12** and **0.7.8** visible alongside 0.7.25.
- Retain **0.7.8** as historical known-good fallback during Buffered Look Ahead device acceptance.

## Current work

- **0.7.25 is published.** Shipped scope: HLS-27, HLS-28 and SUB-1. Their delivery is released, but verification remains review/partial pending target Fire TV acceptance.
- HLS-27 measures Kodi playback position across pause/resume and the first per-track post-resume requests, suppressing false video-request epochs only when a nearby segment timeline is consistent with an unchanged playhead. True user seeks and non-zero cold resume retain fresh seek epochs. This is an automated/source-level correctness change, not yet proven to eliminate all Fire TV video freezes.
- HLS-28 target-device verification has failed on 0.7.25. The same media exposes its provider/built-in HLS subtitle streams in every other playback mode, but none are available in Buffered Look Ahead. Proxy transport works in automated tests, so the next diagnostic boundary is Kodi discovery of the rewritten master versus presentation of the requested subtitle rendition.
- SUB-1 improves nested/local custom-directory subtitle capture, on-AV-change final copying, atomic saved-file persistence and redacted capture/restore diagnostics. Intermittent provider-specific recurrence still requires device testing.
- HLS modes 0–2 and HLS-13 reservoir thresholds, HLS-22 concurrency and HLS-24 exact-segment recovery remain intentionally unchanged. HLS-25 nonfatal localhost-consumer timeout handling remains intact.
- HLS-28 is reopened as a next-release candidate after failed 0.7.25 Fire TV subtitle-track acceptance. PLAY-1, HLS-1 and UI-1 remain backlog investigations. NEXT_RELEASE has no new committed scope. KNOWN_ISSUES remains the canonical task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
