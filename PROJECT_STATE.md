# Appi project state

Updated: 2026-10-14. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.26**. The experimental 0.8.0 archive is not the baseline.
- Publication: [PR #18](https://github.com/ihabmmali/appi/pull/18), merge `cd69c96a12afa3ad185a5e82270de621d78d474b`. Final exact-candidate verification/package run `38654303815` passed 115 tests (1 skipped), workflow checker, deterministic package and ZIP/index/hash inspection.
- Published 0.7.26 ZIP SHA-256: `030a8a332fd22332a6bcb6555b1d3346e1330a533ce84ebe30c64a3b0a27a456`. GitHub Pages deployment `38654402568` initiated; check completion. Install page: https://ihabmmali.github.io/appi/ .
- The published index intentionally keeps **0.7.25**, **0.7.24**, **0.7.23**, **0.7.22**, **0.7.21**, **0.7.14**, **0.7.12** and **0.7.8** visible alongside 0.7.26.
- Retain **0.7.8** as historical known-good fallback during Buffered Look Ahead device acceptance.

## Current work

- **0.7.26 is published.** Reopened HLS-28's subtitle compatibility bridge ships with automated verification, but still awaits Kodi/Fire TV same-media subtitle selector and buffering acceptance. 0.7.25 remains visible for rollback.
- HLS-27 measures Kodi playback position across pause/resume and the first per-track post-resume requests, suppressing false video-request epochs only when a nearby segment timeline is consistent with an unchanged playhead. True user seeks and non-zero cold resume retain fresh seek epochs. This is an automated/source-level correctness change, not yet proven to eliminate all Fire TV video freezes.
- HLS-28 failed on 0.7.25 in Fire TV same-media testing. 0.7.26 offers a lazy optional external WebVTT track bridge for the selected variant, independently of the A/V reservoir; native playlist request diagnostics remain. Device-visible language choices and cue timing are not yet verified, and live/fMP4/encrypted/non-WebVTT sidecars are not supported.
- SUB-1 improves nested/local custom-directory subtitle capture, on-AV-change final copying, atomic saved-file persistence and redacted capture/restore diagnostics. Intermittent provider-specific recurrence still requires device testing.
- HLS modes 0–2 and HLS-13 reservoir thresholds, HLS-22 concurrency and HLS-24 exact-segment recovery remain intentionally unchanged. HLS-25 nonfatal localhost-consumer timeout handling remains intact.
- No next release scope is committed. HLS-28 remains in review/partial for target-device testing; PLAY-1, HLS-1 and UI-1 remain backlog investigations. KNOWN_ISSUES remains the canonical task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
