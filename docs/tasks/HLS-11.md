---
id: HLS-11
role: implementation
status: ready
delivery: unreleased
verification: failed
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-11 — Repair Buffered Look Ahead seek and recovery timeout

## Objective
Make seeking and post-seek recovery reliable in Buffered Look Ahead mode after 0.7.19 fixed initial preparation/playback but target-device seeks still fail with Appi-generated timeout errors.

## Observed target-device behavior
- initial preparation is fast;
- the buffer fills quickly;
- ordinary playback is stable;
- seeking/fast-forwarding triggers an Appi timeout;
- the error may suggest trying a lower-quality stream even though the same quality prepared quickly and plays normally before the seek;
- after the seek failure, resuming consistently starts playback briefly;
- the normal **Appi buffering** indicator then appears;
- playback stutters and exits with **buffering failed / timeout**.

The lower-quality suggestion must not be treated as proof that bitrate is the cause.

## Scope
Repair only Buffered Look Ahead seek/recovery while preserving the working initial preparation/handoff path and playback modes 0–2.

Investigate:
- detection of non-sequential segment requests and the requested seek target;
- re-centering `last_served` and prefetch priority at the requested segment;
- coordination of video and associated audio tracks after a seek;
- whether stale/in-flight pre-seek downloads consume capacity or delay the seek target;
- behavior when the requested segment is outside the retained rolling buffer;
- the current 20-second recovery-reserve wait and whether the requested target can safely resume before a larger reserve is rebuilt;
- cancellation/reprioritization of obsolete prefetch work after a seek;
- repeated forward and backward seeks;
- post-timeout state, including why resume briefly plays, enters Appi buffering, stutters and times out again;
- exact source of each user-visible timeout and why a lower-quality recommendation is emitted.

Do not reduce selected quality merely to hide a seek-state defect. Quality fallback should only be suggested when diagnostics establish insufficient throughput/capacity.

## Acceptance
- Forward seeking from stable Buffered Look Ahead playback resumes reliably at the requested position.
- Backward seeking resumes reliably, including when old segments have been evicted and must be fetched again.
- The requested target segment is immediately prioritized after re-centering.
- Required video/audio tracks reach a coherent playable state after the seek.
- Stale pre-seek work does not starve the requested target or hold the session in an obsolete recovery state.
- Recovery waits are bounded but do not require more buffered media than needed to resume safely.
- A recovery timeout leaves the session in a clean deterministic state.
- Resuming after a timeout either returns to a healthy buffered session or fails cleanly; it must not briefly play, show Appi buffering, stutter and re-enter the same timeout loop.
- Repeated forward/backward seeks do not deadlock workers, leak session state, or require restarting Kodi.
- Error text identifies the actual failure and does not recommend lower quality unless measured evidence supports a bandwidth/quality limitation.
- The simple buffering/recovery indicator remains visible and truthful during refill.
- HLS-10 overlay behavior is independent; seek repair must not depend on the detailed overlay.
- Initial preparation and ordinary non-seek Buffered Look Ahead playback remain as reliable as observed in 0.7.19.
- Modes 0–2 remain unchanged.
- Automated tests cover forward seek outside cache, backward seek after eviction, repeated seeks, recovery timeout, resume-after-timeout, associated audio/video coordination and stale-prefetch reprioritization.
- Target-device verification reproduces the reported seek and resume-after-failure sequence on the same stream that starts and plays normally.

## Authorization
Reported by the user on 2026-09-27 while testing published Appi 0.7.19. This task is logged as a ready candidate and is not committed to a future release unless explicitly included under AGENTS.md.

## Evidence
0.7.19 source re-centres a track on a non-sequential segment request and waits for a recovery reserve with `RECOVERY_TIMEOUT = 20.0`.

On the target device the same stream prepares rapidly and plays well before seeking. A seek times out. Resuming then consistently plays briefly, displays **Appi buffering**, stutters and exits with a buffering-failed timeout. This points to seek/recovery state, target prioritization, or post-timeout cleanup rather than demonstrated insufficient stream bitrate.

## Outcome and next action
Instrument the requested segment, per-track re-centering, in-flight downloads, cached-ahead reserve and post-timeout state across the failing seek/resume sequence. Repair recovery so the target is prioritized and a timeout cannot leave the session in a recurring degraded state.
