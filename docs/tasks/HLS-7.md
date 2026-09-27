---
id: HLS-7
role: implementation
status: ready
delivery: unreleased
verification: failed
owner: unassigned
base_commit: unset
artifact: none
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
Observed on the target device:
- very long startup on one stream;
- unreliable fast-forward/seek;
- another stream initially spun and then produced no playback and no error;
- after several retries, that stream immediately produced a playback-failed error;
- leaving Recently Played and re-entering it changed the same stream back to spinning/no playback.

## Outcome and next action
Committed for the next release. Harden Buffered Look Ahead startup, seeking/re-centering, error propagation, repeated-attempt state reset, navigation/session lifecycle handling and cleanup, then verify it together with HLS-6.
