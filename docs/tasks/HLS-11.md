---
id: HLS-11
role: implementation
status: active
delivery: unreleased
verification: failed
owner: builder-publisher-2026-09-27
base_commit: 24ac0358640864a0129d97b638ca37c616f6612b
artifact: none
---
# HLS-11 — Repair multi-variant HLS seek, resume-point and recovery timeout

## Objective
Make random-access playback reliable for known multi-variant HLS streams in Buffered Look Ahead mode. On 0.7.19 these streams load and play well from the beginning, but manual seeking and starting from a saved/resume playback point fail with Appi-generated timeout/recovery errors.

## Observed target-device behavior
- the tested streams clearly expose multiple HLS resolution/bitrate choices, confirming a multi-variant HLS master;
- from time 0, initial preparation is fast, the buffer fills quickly and ordinary playback is stable;
- seeking/fast-forwarding away from the sequential playback position triggers an Appi timeout;
- starting/resuming the same kind of stream from a previously saved playback point also fails, indicating the defect is not limited to an in-session seek;
- the error may suggest trying a lower-quality stream even though the same quality prepared quickly and plays normally before the seek;
- after the seek failure, resuming consistently starts playback briefly;
- the normal **Appi buffering** indicator then appears;
- playback stutters and exits with **buffering failed / timeout**.

The lower-quality suggestion must not be treated as proof that bitrate is the cause.

## Scope
Repair only Buffered Look Ahead random-access/recovery behavior for HLS while preserving the now-demonstrated working time-0 preparation/handoff path and playback modes 0–2.

Investigate:
- detection of non-sequential segment requests and the requested seek target;
- cold start at a non-zero Kodi resume/bookmark position, before normal sequential segment history has been established;
- re-centering `last_served` and prefetch priority at the requested segment;
- coordination of selected video and associated/default audio tracks after a seek or resume-point start, especially for multi-variant masters;
- whether stale/in-flight pre-seek downloads consume capacity or delay the seek target;
- behavior when the requested segment is outside the retained rolling buffer;
- the current 20-second recovery-reserve wait and whether the requested target can safely resume before a larger reserve is rebuilt;
- cancellation/reprioritization of obsolete prefetch work after a seek;
- repeated forward and backward seeks;
- post-timeout state, including why resume briefly plays, enters Appi buffering, stutters and times out again;
- exact source of each user-visible timeout and why a lower-quality recommendation is emitted.

Do not reduce selected quality merely to hide a seek-state defect. Quality fallback should only be suggested when diagnostics establish insufficient throughput/capacity.

## Acceptance
- A known multi-variant HLS master plays successfully from time 0 as a regression baseline.
- Forward seeking from that stable Buffered Look Ahead playback resumes reliably at the requested position.
- Backward seeking resumes reliably, including when old segments have been evicted and must be fetched again.
- Starting the same known HLS item from a saved non-zero Kodi resume point succeeds without first playing from time 0.
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
- Target-device verification uses at least one positively identified multi-variant HLS master and covers: start from time 0, manual forward seek, manual backward seek, fresh playback from a saved non-zero resume point, and the post-timeout resume sequence.

## Authorization
Reported by the user on 2026-09-27 while testing published Appi 0.7.19. On 2026-09-27 the user explicitly instructed that all current candidates be committed. HLS-11 is therefore committed release scope and a release blocker.

## Evidence
Implementation/research session opened on branch `release/0.7.20` from base `24ac0358640864a0129d97b638ca37c616f6612b`; user authorization includes implementation, integration and publication of the committed next-release scope.

0.7.19 source re-centres a track on a non-sequential segment request and waits for a recovery reserve with `RECOVERY_TIMEOUT = 20.0`.

On the target device, streams that expose multiple resolution choices—clear evidence of multi-variant HLS masters—prepare rapidly and play well from time 0. Manual seeks fail, and starting/resuming from an existing non-zero playback point also fails. After a seek timeout, resuming consistently plays briefly, displays **Appi buffering**, stutters and exits with a buffering-failed timeout. This isolates the remaining problem to random-access/recovery state much more strongly than to initial bandwidth, master parsing or rendition selection.

## Outcome and next action
Committed for the next release. Instrument the requested segment, per-track re-centering, selected rendition/audio association, in-flight downloads, cached-ahead reserve and post-timeout state across both an in-session seek and a cold start from a saved non-zero resume point. Repair recovery so the target is prioritized and a timeout cannot leave the session in a recurring degraded state.
