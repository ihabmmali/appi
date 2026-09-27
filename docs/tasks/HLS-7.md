---
id: HLS-7
role: implementation
status: review
delivery: released
verification: failed
owner: Codex release/0.7.17
base_commit: 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3
artifact: plugin.video.appi/plugin.video.appi-0.7.17.zip
---
# HLS-7 — Stabilize Buffered Look Ahead startup, seeking and failure handling

## Objective
Make Buffered Look Ahead Playback robust enough for normal target-device use.

The 0.7.16 target-device test failed acceptance: one stream took a very long time to start and fast-forward/seek was unreliable; another initially spun for a while and then produced neither playback nor an error. After several retries, that same stream began failing immediately with a playback-failed error. Leaving Recently Played and re-entering it changed the behavior back to spinning/no playback.

## Scope
Repair only the isolated Buffered Look Ahead path. Preserve playback modes 0–2 unchanged.

Cover startup state handling, bounded waits, visible failure instead of silent spinning, seek/fast-forward re-centering, cancellation, cleanup, session replacement, repeated-attempt state reset, navigation-driven lifecycle reset, upstream errors, and recovery when a requested segment is outside the current prefetched window.

Coordinate with HLS-6 so the simple startup/buffering indicator reflects filling/recovery state and the optional detailed overlay can expose buffer metrics.

## Acceptance
- Reproduce the long-startup, unreliable seek, silent no-playback, immediate-playback-failed, and post-navigation return-to-spinning scenarios where possible.
- Startup has a bounded timeout/failure policy.
- Failure produces a clear Appi/Kodi message and cleans up the buffered session.
- Successful startup begins consistently once its required initial buffer state is satisfied.
- Fast-forward/seek re-centres buffering correctly and either resumes or fails explicitly within a bounded time.
- Repeated seeks do not deadlock workers or strand stale state.
- A failed or cancelled buffered session does not prevent the next item from starting.
- Repeated attempts of the same failing stream do not leave stale proxy/session state that changes later attempts unless the upstream failure itself persists and is clearly reported.
- Leaving and re-entering Appi folders such as Recently Played does not unpredictably change buffered-session failure behavior; any lifecycle reset is explicit and safe.
- Stop/cancel terminates active buffered work and removes temporary session data.
- Upstream playlist/segment/network failures are captured in diagnostics and surfaced deterministically.
- Modes 0–2 remain functionally unchanged and pass regression tests.
- Automated tests cover delayed startup, timeout/error, seek/re-centre, repeated seek, repeated attempts, navigation/session reset and session replacement.
- Target-device verification repeats the reported scenarios and records startup time, seek behavior, retry/navigation behavior, any failure message and buffer-state telemetry.

## Authorization
Reported by the user on 2026-09-27 after testing 0.7.16. The user explicitly instructed that all tracked changes be committed for the next release. HLS-7 is committed release scope.

## Evidence

Published in 0.7.17 through PR #5, merge `18ffae9349b2d225b575cee6a276ea8dcd59143b`. Release/package run 36350783947, post-merge verification 36350856112 and Pages deployment 36350855315 passed. Deployed ZIP hash matched `77dd83244e01bae295d3118073d28b13b2a6d634576cf4ffae84fde14a49b0b1`.

2026-09-27 implementation/self-review (0.7.17 candidate): Source review found unbounded/stacked startup and recovery delays, repeated VOD playlist rebuilds, no HTTP range handling, and unconditional player-stop cleanup that could terminate a replacement session. Repair adds asynchronous startup preparation, explicit cancel/error responses, unique expiring control mailboxes, token-bound player cleanup, stable VOD playlists and segment identities, media URL extensions, HTTP range handling and bounded demand recovery. Tests exercise repeated failures then a good stream, replacement plus a stale stop, cancelled preparation plus a good retry, cached-segment immediate return, missing seek failure, repeated forward/backward seeks, and real TS/fMP4 decode/seek. Exact Fire TV symptoms were not reproduced on the user's device; these are code-level failure mechanisms and local verification, not a confirmed provider/device root cause.

73 unit/smoke/integration tests passed with Python 3.12, including real FFmpeg MPEG-TS and fMP4 decode at start, forward seek and backward seek; workflow validation and diff whitespace checks passed. `_effective_hls_mode`, `_configure_hls` and `_configure_mp4` are AST-identical to base 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3. Reviewed implementation commit: `842ef37c8deb6ce340946dbbafa29fbd8745ec0c`. This is self-review, not independent review.

Observed on the target device:
- very long startup on one stream;
- unreliable fast-forward/seek;
- another stream initially spun and then produced no playback and no error;
- after several retries, that stream immediately produced a playback-failed error;
- leaving Recently Played and re-entering it changed the same stream back to spinning/no playback.

## Outcome and next action
Implemented, self-reviewed, integrated and published in 0.7.17. Target-device acceptance remains pending, so this task stays in review/partial verification. Retest the task's device/UI scenarios after installing 0.7.17; do not mark done from package availability alone.

## Implementation session — 2026-09-27
User authorized implementation, testing, integration and publication in this session. Base 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3. One worker owns the scoped source/settings/tests and shared release records; no concurrent worker changes observed. Target 0.7.17. Modes 0–2 must remain unchanged.


## 0.7.18 target-device retest
The 0.7.18 repair prevents the 0.7.17 Kodi startup crash, but Buffered Look Ahead still fails functional acceptance on the target Fire TV.

Observed:
- preparation window appears with **Filling buffer** but can show no meaningful progress;
- Kodi spinner then appears and playback fails after a few seconds;
- repeated attempts can eventually succeed;
- on another episode, preparation jumps to roughly 90% and then times out with **Unable to prepare stream**;
- regular playback works on the same episode/file.

This means the shipped HLS-7 repair is not accepted on the target device. [HLS-8](HLS-8.md) owns the current preparation/readiness/handoff failure.
