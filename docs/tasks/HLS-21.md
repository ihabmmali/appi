---
id: HLS-21
role: research
status: review
delivery: released
verification: partial
owner: builder-publisher-0.7.22
base_commit: fd0bd5b08228c34b09de684f7b4b1f865a09e2d2
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.22.zip
---
# HLS-21 — Prove whether Buffered Look Ahead timeouts are true reservoir depletion

## Objective
Determine exactly why Buffered Look Ahead playback on 0.7.21 sometimes freezes, reports a timeout, briefly resumes/catches up, and then exits.

Do not assume that "timeout" means the configured buffer is too small. Prove whether the active epoch's **contiguous playable reserve** actually drains to zero before failure, or whether another condition blocks the next required media despite cached bytes still existing.

## Scope
Add bounded Buffered Look Ahead failure telemetry and causal classification only. Capture the preceding reservoir/track/transfer timeline, persist it before teardown, and distinguish true depletion from required-track starvation, holes, throughput deficit, recovery-with-progress and lifecycle termination. Do not alter modes 0–2.

## Target-device symptom
The user reports repeated failures with this sequence:
1. video/audio freezes while subtitles continue progressing;
2. playback may resume briefly, sometimes appearing to run unusually fast/catch up;
3. Appi shows a Buffered Look Ahead failure / timeout notification;
4. a few seconds later playback stops completely.

This is distinct from initial startup failure and should be correlated with HLS-19's runtime recovery path.

## Competing hypotheses
At minimum distinguish:

### A. True reservoir exhaustion / insufficient capacity
The contiguous playable reserve falls from high/low-water through critical to ~0 before the next required media arrives.

Evidence would support:
- provider stalls longer than the configured reserve can absorb;
- larger capacity or a higher fill/high-water threshold would increase tolerance;
- HLS-19 recovery still needs to prevent terminal failure while the provider is temporarily unavailable.

### B. Sustained provider throughput deficit
The reservoir drains because measured provider throughput remains below selected rendition consumption for long enough.

A larger buffer delays failure but does not solve an indefinitely sustained deficit.

### C. Contiguous-hole failure
Total cached bytes remain substantial, but the exact next required video or audio segment is missing. Because playable reserve is contiguous, one hole can reduce usable reserve to zero even with many later segments already cached.

In this case, increasing total capacity alone is not the correct fix; the missing next segment must be prioritized/retried.

### D. Recovery-policy timeout
The required segment/reserve is rebuilding, but the hard-coded/current recovery window expires before recovery completes. Appi then returns a 503 / terminal error path even though recovery would have succeeded with a longer or retry-based policy.

### E. Track-coherence issue
One required track (for example audio) is depleted or missing while another still has significant buffered media, making the combined playable reserve collapse.

## Required failure snapshot
Maintain a lightweight rolling telemetry window while Buffered Look Ahead is active, independent of the optional debug overlay.

On buffer depletion, recovery timeout, proxy 503/502, or session termination, persist at least the previous 30–60 seconds plus the failure event, including:
- active epoch ID/reason;
- configured capacity;
- startup/high/low/critical thresholds;
- combined contiguous playable bytes and seconds;
- per-required-track contiguous bytes/seconds;
- total cached bytes on disk;
- next requested segment index/sequence per track;
- whether each exact next segment is cached, fetching, failed, or absent;
- queued/prefetched segment count;
- selected rendition bitrate;
- measured provider throughput;
- recent individual segment latency/download duration/bytes/status;
- current retry attempt / recovery elapsed time when HLS-19 exists;
- Kodi player/caching/paused/playing state when available;
- failure/retirement reason.

Sampling should be frequent enough near critical/recovery state to establish ordering. A 2-second sample cadence alone may be too coarse; use a tighter in-memory ring buffer in critical/recovery state if practical, while keeping overhead low.

## Classification output
When a failure occurs, diagnostics should derive a concise classification such as:
- `reservoir_exhausted`;
- `sustained_throughput_deficit`;
- `next_segment_hole`;
- `recovery_timeout_with_progress`;
- `required_track_starvation`;
- `session_lifecycle_termination`;
- `unknown`.

The classification must include the underlying numeric evidence rather than being a guess.

## Acceptance
- A reproduced timeout failure can be assigned to one of the above classes or explicitly remain unknown with missing evidence identified.
- The diagnostic pack shows whether contiguous reserve reached zero before the timeout.
- It separately shows total cached bytes so "cache contains data" is not confused with playable reserve.
- It shows whether the exact next video/audio segment was available.
- It shows reserve trajectory and provider throughput leading into failure.
- It can prove or disprove "buffer too small" for a specific failure.
- If larger capacity is tested, compare the same stream/quality and show whether time-to-depletion scales with additional reserve.
- No changes to the proven 0.7.21 buffering algorithm are made merely to collect evidence.
- HLS-19 uses this evidence to choose recovery behavior; HLS-18 may expose capacity/watermark tuning but must not be used as a blind workaround.

## Authorization
Created from the user's 2026-09-28 target-device observation of repeated runtime failures: A/V freezes while subtitles continue, playback may briefly catch up, Appi reports a timeout, then playback exits. The user specifically requested confirmation whether the timeout is caused by the look-ahead buffer emptying before refill can catch up, which would imply insufficient reserve for that stall pattern.

On 2026-09-28 the user explicitly instructed that all current candidates, diagnostics or otherwise, be committed for the next release. HLS-21 is committed next-release scope as the investigation/diagnostic evidence task supporting HLS-19.

## Evidence
The 0.7.22 implementation records a rolling bounded timeline of playable bytes/seconds, total cache, selected bitrate, measured provider throughput, epoch/reason, recovery state and per-required-track cursor/contiguous reserve/next-segment state. Failure snapshots also retain recent transfer evidence and classify session lifecycle termination, required-track starvation, next-segment holes, recovery timeout with progress, sustained throughput deficit, reservoir exhaustion or unknown.

Automated coverage in the 0.7.22 candidate asserts numeric timeline persistence and classification output. Release gate run `36515421099` passed all 100 unit/smoke tests (1 skipped); the run stopped afterward only because older task records lacked required template headings. Target-device reproduction remains required to determine which classification applies to the user's real failure.

## Outcome and next action
Instrument and classify the next runtime timeout before changing buffer-size defaults or reservoir behavior. Preserve the working 0.7.21 producer/consumer algorithm while determining the true failure boundary.


## HLS-16 observability dependency
The user noted that this root-cause question would have been straightforward to diagnose had the detailed debug overlay already been working. HLS-16 is therefore a practical dependency for efficient HLS-21 target-device validation.

The persisted rolling failure snapshot remains required because the overlay can disappear when playback exits, but the live overlay should expose the same critical metrics during reproduction so reserve exhaustion versus segment-hole/recovery-timeout behavior can be recognized immediately.


## 0.7.22 candidate evidence
0.7.22 candidate persists a bounded pre-failure timeline, recent transfer evidence and causal classification with per-required-track contiguous reserve/next-segment state. Automated numeric snapshot/classification coverage passed; a real target-device failure is still required to identify the user's actual cause.

Final package gate run `36515744781` passed all 100 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild and ZIP/index inspection. Candidate artifact commit: `971d29d4145411e0c78703326246b770c82d95c3`; ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`.


## 0.7.22 publication
Published in Appi 0.7.22 through PR #11 / merge `92131c95c1d047eb7a683e8e5e2e6abe10e1a518`. Final publication gate run `36626983906` passed 100 tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/index inspection and packaging. GitHub Pages deployment run `36627135052` succeeded. Published ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`. Delivery is released; documented target-device acceptance remains review/partial.
