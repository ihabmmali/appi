# Appi project state

Updated: 2026-09-29. Start with [AGENTS.md](AGENTS.md) for role routing.

## Current baseline

- Repository: https://github.com/ihabmmali/appi ; default branch: main.
- Current published packaged add-on: **0.7.23**. The experimental 0.8.0 archive is not the main baseline.
- Publication: PR #12, merge `9520fcc984b3f5796e840f217574bf0569dbb1f9`. Final exact-candidate gate run `36662004552` passed 103 tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/index inspection and packaging.
- Published 0.7.23 ZIP SHA-256: `029e2a33b52f235746ce79f8e6140f569addefb549fcebf757c786a5171ca6ff`. GitHub Pages deployment run `36662108681` succeeded. Install page: https://ihabmmali.github.io/appi/ .
- The published index intentionally keeps **0.7.22**, **0.7.21** and **0.7.8** visible alongside 0.7.23; 0.7.14 and 0.7.12 are also retained.
- Keep **0.7.8** as the historical known-good fallback while newer Buffered Look Ahead behavior completes target-device acceptance.

## Current work

- **0.7.23 is published.** Shipped scope: HLS-22, HLS-23 and HLS-24. Delivery is released; all three remain review/partial because their documented Fire TV/provider acceptance checks are still outstanding.
- HLS-24 releases an exact sequential segment immediately after bounded recovery succeeds instead of holding Kodi behind the larger recovery-reserve rebuild. Background refill continues; seek/cold-resume fresh-epoch reserve gating remains intact.
- HLS-22 adds settings-backed bounded producer concurrency (default 2, range 1–4) while preserving duplicate suppression, stale-epoch cancellation and contiguous playable-reserve accounting. Same-stream target-device throughput comparison against FFmpeg/ISA is still required.
- HLS-23's multiline telemetry is confirmed readable on Fire TV, but its target-device verification is now failed: the full overlay remains visible regardless of the setting and its WindowXMLDialog blocks Kodi's normal playback OSD until Back dismisses it.
- Existing HLS modes 0–2 and the established HLS-13 reservoir thresholds/accounting remain intentionally unchanged.
- HLS-26 is a next-cycle candidate to make the debug-overlay OFF setting absolute and investigate a truly passive renderer. Back-to-dismiss is an acceptable fallback only when debug was explicitly enabled.
- HLS-25 is a next-cycle **release-blocking candidate** after 0.7.23 pause/resume failure. Kodi-side localhost write timeout/disconnect must not poison the session, and duplicate/range/re-read segment requests must not create false seek epochs. Do not address this by increasing timeouts or changing reservoir size.
- HLS-19 verification is now failed on target device because its extended-pause acceptance still fails in 0.7.23 despite healthy reserve.
- META-1 is a next-cycle candidate to surface optional movie/episode runtime through Kodi metadata and show locally derived episode counts on season folders.
- PLAY-1, HLS-1 and UI-1 remain backlog investigations. No next-release product scope is currently committed; [NEXT_RELEASE.md](NEXT_RELEASE.md) is reset for the next planning cycle. [KNOWN_ISSUES.md](KNOWN_ISSUES.md) remains the canonical task index.

## Context on demand

[ARCHITECTURE.md](ARCHITECTURE.md) explains current source and resource limits. [RELEASE_NOTES.md](RELEASE_NOTES.md) holds delivery/check evidence. [CHANGELOG.md](CHANGELOG.md) records implemented changes. Canonical requirements and acceptance evidence live in `docs/tasks/`.

Source establishes implemented behavior, requirements establish intended behavior, and checks establish verified behavior. Publication does not imply target-device acceptance.
