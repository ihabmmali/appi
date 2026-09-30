# Appi project state

Updated: 2026-09-29. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.22**. The experimental 0.8.0 archive is not the main baseline.
- Publication: PR #11, merge `92131c95c1d047eb7a683e8e5e2e6abe10e1a518`. Final publication gate run `36626983906` passed 100 tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/index inspection and packaging.
- Final artifact commit: `6f78d101be5069d79f3a4328cb6a90a2df9cd47f`. Published 0.7.22 ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`. Pages deployment run `36627135052` succeeded. Install page: https://ihabmmali.github.io/appi/ .
- The published index intentionally keeps **0.7.21** and **0.7.8** visible alongside 0.7.22; 0.7.14 and 0.7.12 are also retained.
- Keep **0.7.8** as the historical known-good fallback while newer Buffered Look Ahead behavior completes target-device acceptance.
- **0.7.17 failed target-device startup acceptance** because its language lists contained empty option values; 0.7.18 corrected that crash trigger and target-device retest confirmed Kodi starts normally.

## Current work

- **0.7.22 is published.** Shipped scope: HLS-16, HLS-17, HLS-18, HLS-19, HLS-20, HLS-21, UI-5, UI-6 and DOWNLOAD-1. Delivery is released; task verification remains review/partial where documented Fire TV/provider checks are still outstanding.
- HLS-19 now owns transient depleted-segment recovery inside Appi under configurable retry/timeout bounds and separates paused/buffering/stopped lifecycle handling. Initial 0.7.22 device observation says buffering appears better, but more testing is required; stall and long-pause acceptance remain pending.
- HLS-18 exposes advanced Buffered Look Ahead thresholds/timers while retaining the proven 0.7.21 defaults. HLS-17 clarifies startup target versus configured capacity without changing the reservoir policy.
- HLS-20 instruments reservoir-ready through Kodi AV start and preloads known key/map dependencies. HLS-21 records a bounded pre-failure reservoir/track/transfer timeline and evidence-based classification for future real-device failures.
- HLS-16 changes the detailed overlay's primary renderer to a bundled modeless `WindowXMLDialog` with a logged compatibility fallback. Fire TV visibility still needs target-device confirmation.
- UI-5 displays installed version directly in the About settings pane. UI-6 references the same approved flat icon bytes through a new resource path to bypass Kodi artwork caching.
- DOWNLOAD-1 generates FFmpeg remux scripts using explicit first-video/first-audio mapping, `-c copy` and `-threads 0`, while preserving safe quoting and atomic partial-file handling.
- Existing HLS modes 0–2 remain intentionally unchanged.
- HLS-22 is the next-cycle candidate to benchmark Appi producer throughput against FFmpeg/ISA on the same stream/network/VPN and investigate connection reuse/request overhead/bounded concurrency without changing the reservoir policy. The same-stream Manual/ISA success now makes Appi producer overhead a likely contributor rather than merely a performance opportunity. It is **not committed** to a release yet.
- HLS-23 is a next-cycle candidate from 0.7.22 target-device testing: the overlay can appear while disabled and detailed telemetry overflows horizontally. OFF must suppress all BufferOverlay text, and enabled debug telemetry must use a bounded multiline screen-safe layout.
- HLS-24 is a next-cycle **release-blocking candidate**: the same provider stream plays perfectly in Manual/ISA but Buffered Look Ahead freezes, briefly catches up and silently stops. Source review shows 0.7.22 can withhold an already recovered exact segment until the full recovery reserve is rebuilt, then fail with HTTP 504. Required-segment delivery must be decoupled from background refill.
- PLAY-1, HLS-1 and UI-1 remain backlog investigations.
- [NEXT_RELEASE.md](NEXT_RELEASE.md) has been reset: no next-release scope or version is currently committed. [KNOWN_ISSUES.md](KNOWN_ISSUES.md) remains the canonical task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
