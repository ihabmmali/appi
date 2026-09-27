---
id: HLS-8
role: implementation
status: ready
delivery: unreleased
verification: failed
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-8 — Repair 0.7.18 Buffered Look Ahead preparation and runtime failure

## Objective
Repair Buffered Look Ahead Playback after target-device testing of 0.7.18 showed that preparation/fill and Kodi handoff remain unreliable even though the Kodi startup crash is fixed.

## Observed target-device behavior
- Preparation window appears and says **Filling buffer**, but one attempt shows no meaningful progress.
- Kodi's spinner then appears and playback fails after a few seconds.
- After several retries, one attempt eventually plays, but no buffer indication is visible during playback.
- On a different episode, preparation jumps to roughly 90% and then times out with **Unable to prepare stream**.
- Regular/non-buffered playback works on that same episode/file.

## Scope
Investigate and repair only the Buffered Look Ahead path, preserving modes 0–2.

Focus on:
- preparation progress computation;
- actual contiguous playable reserve versus displayed percentage;
- readiness race between background prefetch, localhost playlist readiness and Kodi handoff;
- timeout behavior near apparent completion;
- deterministic retry behavior after failed preparation;
- cleanup/session reset after failure;
- keeping the simple startup/buffering indicator visible and truthful until playback is ready or a clear failure is shown;
- exposing the configured detailed buffer overlay during successful buffered playback.

Progress must reflect playback readiness rather than only bytes/tasks scheduled.

## Acceptance
- Reproduce or instrument sufficiently to explain the no-progress failure and near-90%-then-timeout failure.
- Preparation progress advances from actual playable-buffer readiness and does not misleadingly approach completion when playback is not ready.
- Kodi is not handed the localhost stream until the required initial contiguous playable reserve is available.
- Successful preparation starts playback consistently without an unexplained intermediate spinner.
- Failed preparation produces a bounded clear error and fully cleans the buffered session.
- Retrying the same item after failure behaves deterministically and does not require several attempts before working.
- A file that plays normally can also play in Buffered Look Ahead unless a buffered-specific limitation is explicitly detected and reported.
- The simple startup/buffering indicator remains visible through preparation/recovery until playback begins or fails.
- If the detailed overlay is enabled, successful playback shows current buffered state after startup.
- Modes 0–2 remain unchanged and pass regression tests.
- Automated tests cover stalled preparation, near-complete timeout, readiness/handoff ordering, retry after failure, cleanup and successful indicator transition.
- Target-device verification repeats both reported episodes and records preparation progress, actual buffered bytes/seconds, handoff time, playback result and timeout/error.

## Authorization
Reported by the user on 2026-09-27 while testing 0.7.18. This task is recorded as ready planning work but is not committed release scope unless explicitly included under AGENTS.md.

## Evidence
Regular playback works on at least one file where Buffered Look Ahead reaches roughly 90% preparation and then times out, isolating the observed failure to the buffered path.

## Outcome and next action
Assign a focused Buffered Look Ahead repair worker to instrument preparation readiness/progress, fix handoff and timeout behavior, and verify retries and successful playback on the target device.
