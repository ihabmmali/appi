---
id: HLS-12
role: implementation
status: review
delivery: released
verification: partial
owner: builder-publisher-2026-09-28
base_commit: 4a415f9eaeb48c77ef2fcaa895db90d7e66ab183
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.21.zip
---
# HLS-12 — Replace Buffered Look Ahead seek/resume with fresh buffer epochs

## Objective
Replace the repeatedly failing stateful seek/recovery logic with a simpler deterministic model.

For Buffered Look Ahead VOD, any manual seek or playback start at a saved non-zero resume point must be treated as a **new buffer epoch at the requested target position**. Appi must not try to preserve and recover the old pre-seek queue/session state.

## Scope
Implement the fresh-epoch random-access design only inside Buffered Look Ahead mode: epoch ownership, stale-work invalidation, cross-track target alignment, target-first fetching, contiguous target reserve, bounded failure and diagnostic evidence. Preserve the three non-buffered HLS playback modes and the user's selected rendition.

## Why this supersedes HLS-11
0.7.20 shipped an HLS-11 repair that coordinated track re-centering, reprioritized targets and made recovery misses retriable. It still times out on the target device.

The repeated failures across 0.7.19 and 0.7.20 show that further tuning of the existing recovery state machine is not an acceptable direction.

## Required design
When Kodi requests a discontinuous playback position or starts from a saved non-zero resume point:

1. Detect the target segment/time unambiguously.
2. Increment a buffer/session **epoch** so every prior prefetch job/result becomes stale.
3. Cancel or ignore all in-flight work from the prior epoch.
4. Clear old scheduling/recovery state that can affect the new target. Retained disk cache may be reused only if content identity and segment mapping are unquestionably valid.
5. Rebuild the selected video rendition and associated/default audio rendition around the target.
6. Prioritize the exact target segment(s), then fetch a small contiguous playable reserve forward from that position.
7. Do not report recovery complete until all required tracks have that contiguous reserve.
8. Only then allow normal look-ahead prefetch to continue.
9. If target preparation fails, terminate that epoch cleanly with a specific error; do not fall back into the previous session or a recurring timeout loop.

The implementation should favor deterministic teardown/rebuild over preserving complex mutable recovery state.

## Constraints
- Do not solve this by increasing the current 20-second recovery timeout.
- Do not automatically lower quality unless measured transfer evidence proves bandwidth is insufficient.
- Preserve the user's selected rendition/quality across seek/resume.
- Keep Native Kodi and InputStream Adaptive modes unchanged.
- Do not re-fetch the HLS master unnecessarily when existing parsed metadata is still valid, but correctness is more important than micro-optimization.
- Video and associated audio must move to the same playback epoch/target coherently.
- The simple buffering indicator should show that a new target is being prepared.
- Detailed debug telemetry should expose epoch ID, requested target, target segment, stale-job cancellation/ignore counts, and playable reserve when practical.

## Acceptance
- A known multi-variant HLS stream still starts and plays normally from time 0.
- Forward seek creates a new epoch and reliably resumes at the target.
- Backward seek creates a new epoch and reliably resumes at the target.
- Starting from a saved non-zero Kodi resume point uses the same fresh-epoch path and succeeds without first playing from time 0.
- Old pre-seek jobs/results cannot mutate the new epoch.
- Required video/audio tracks are aligned to the new target before playback resumes.
- Resume after a failed target preparation starts a genuinely new epoch; it cannot briefly play from stale state and then hit the same old timeout.
- Repeated seeks in quick succession leave only the newest epoch authoritative.
- Buffering timeout/error text identifies target preparation failure and does not suggest lower quality without throughput evidence.
- No indefinite spinner and no recurring timeout loop.
- Automated tests deliberately inject late completions from stale epochs and prove they are ignored.
- Automated tests cover forward seek, backward seek, saved-point start, repeated rapid seeks, audio/video alignment, stale job completion, target timeout and retry.
- Target-device acceptance must use the user's previously failing multi-variant HLS stream and demonstrate start, seek, resume-point start and repeated seek without timeout.

## Authorization
Created from failed target-device acceptance of published 0.7.20 on 2026-09-28. The user explicitly confirmed seek/resume remains broken and instructed that these Buffered Look Ahead repairs be committed for the next release. HLS-12 is therefore committed release scope and a release blocker.

## Evidence
Published 0.7.20 still times out in Buffered Look Ahead despite HLS-11's coordinated re-centering/recovery changes.

The user has repeatedly observed that initial sequential playback can work while random access fails, making seek/resume state management the persistent failure boundary.

Automated 0.7.21 candidate run `36381180991` passed fresh-epoch coverage for coordinated video/audio timeline alignment, cold non-zero resume, forward/backward/repeated seek behavior, timeout/retry and deliberately late stale-epoch completion. Final target-device acceptance on the previously failing multi-variant stream is still required.

Published in Appi 0.7.21 through PR #10 / merge `d9e0be64681fa2dbe9cc434f81375a9c0992a3e1`. Post-merge verification run `36381516837` and Pages deployment run `36381516378` passed. Published ZIP SHA-256: `0e8c615d40cf9f42e0345c61e11a7b244fc443c8858902d53fffda92c1935c81`. Delivery is released; target-device verification remains partial.

## Outcome and next action
Released in 0.7.21. Complete the remaining target-device acceptance documented above; any new defect or repair must be triaged as follow-up work rather than silently reopening this release scope.


Implementation session 2026-09-28: activated on `release/0.7.21` from base `4a415f9eaeb48c77ef2fcaa895db90d7e66ab183`; authorized scope is implementation, review, integration and publication of the committed next release.


## 0.7.21 post-seek observation
The user reports a clear delay after seeking before playback resumes. This may be expected behavior from the fresh-epoch reserve rebuild introduced by HLS-12, but the detailed overlay is currently broken, so the device cannot show whether the delay corresponds to healthy refill, provider stall, or retry.

Do not treat the delay alone as an HLS-12 regression without telemetry. HLS-16 must expose the new-epoch fill/recovery state, and HLS-19 must expose retry/recovery state if provider delay is involved.


## HLS-25 false-seek follow-up
0.7.23 source still treats every request whose segment index is not exactly `last_requested + 1` as a seek. Target-device evidence shows unexpectedly high seek-epoch counts without corresponding user seeks.

HLS-25 owns classification of duplicate/range/re-read requests so the HLS-12 fresh-epoch mechanism is invoked only for genuine timeline discontinuities. Preserve HLS-12 behavior for true forward/backward seek and cold non-zero resume.
