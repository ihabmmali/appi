---
id: HLS-24
role: implementation
status: active
delivery: unreleased
verification: pending
owner: builder-publisher-2026-09-29
base_commit: ff256d99b7097dcea3787c3a86582bec29354972
artifact: none
---
# HLS-24 — Stop Buffered Look Ahead from starving Kodi during recovery

## Objective
Fix the published 0.7.22 Buffered Look Ahead regression where Appi's proxy/recovery path degrades a stream that plays cleanly through Manual fixed-quality / InputStream Adaptive mode.

The buffered path must not withhold an already available exact next segment from Kodi while waiting to rebuild a larger look-ahead reserve.

This is a release-blocking candidate for the next release.

## Target-device A/B evidence
On 2026-09-29 the user tested the same provider stream on the same Fire TV, network and VPN:

### Buffered Look Ahead mode
- video/audio freezes;
- subtitles continue for several seconds;
- `Appi buffering` appears;
- video may catch up rapidly;
- normal playback returns briefly;
- playback then stops silently.

A screenshot captured the recovery state at approximately `6.5 MB / 8.8 MB` while A/V was frozen.

### Manual fixed-quality mode
The same stream played normally with no stuttering or playback failure.

Manual mode preserves the provider master URL and delegates HLS transport/rendition handling to InputStream Adaptive using `stream_selection_type=ask-quality`. Buffered mode instead replaces the provider URL with Appi's localhost proxy and Appi's own segment producer/recovery implementation.

This A/B result strongly localizes the degradation to the Buffered Look Ahead path rather than an intrinsically unstable provider stream, VPN, or Fire TV decoder.

## Confirmed 0.7.22 recovery design problem
For an uncached requested segment, `_Track._serve_segment()` calls `session.recover_segment(...)` before returning the segment file to Kodi.

`recover_segment()` currently:
1. retries/fetches the exact requested segment;
2. once that requested segment is cached, continues blocking;
3. waits for the entire configured recovery reserve via `_wait_reservoir(...)`;
4. only after the larger reserve target is reached does the exact requested segment return to the local HTTP handler and Kodi.

If the recovery reserve does not reach target before the overall recovery deadline, Appi raises `RecoveryExhausted`, marks the session failed, and the proxy returns HTTP 504.

Therefore the recovery-reserve target is currently a hard gate in front of exact media delivery. This can cause Appi itself to extend an A/V freeze even after the specific segment Kodi needs has become available.

The 0.7.22 automated retry test did not exercise this real wait because it mocked `_wait_reservoir()` to return success.

## Required repair
Separate **required-segment delivery** from **background reservoir restoration**.

### Required-segment delivery
When Kodi requests an uncached segment:
- prioritize the exact requested segment;
- apply HLS-19 transient retry handling to that segment;
- as soon as that exact segment is safely cached, return it to Kodi immediately;
- do not wait for the larger recovery reserve before serving it.

### Reservoir restoration
After serving the required segment:
- continue refill in the background toward the configured recovery reserve and normal watermarks;
- keep recovery telemetry active until the reserve is healthy;
- prioritize each newly requested exact segment if Kodi catches up to the refill edge;
- do not fail the whole session merely because the reserve target has not yet been rebuilt while required media is still being delivered successfully.

## Progress-aware failure semantics
- Recovery timeout must measure genuine lack of required-media progress, not simply elapsed wall-clock time since recovery began.
- Successful requested-segment deliveries reset/extend the no-progress basis as appropriate.
- Terminal failure is justified only when the next required media cannot be delivered within the configured no-progress/retry policy, or a deterministic non-retryable condition occurs.
- Do not emit HTTP 504/502 while Appi is still successfully delivering required media.
- Preserve explicit stop/cancel/seek epoch semantics.

All behavior-affecting timing parameters remain settings-backed.

## Relationship to HLS-22
The clean Manual/ISA A/B also strengthens HLS-22.

Even after HLS-24 fixes blocking recovery coordination, determine whether Appi's producer drains unnecessarily because its own HTTP segment acquisition is slower than ISA/FFmpeg. HLS-22 owns persistent connection reuse, TTFB/request overhead and bounded segment concurrency.

HLS-24 must fix the correctness defect even if HLS-22 later makes refill substantially faster.

## Diagnostics
For every depletion/recovery episode record:
- exact requested track/index/sequence;
- whether that segment was cached, fetching, failed or absent;
- request wait start;
- retries/errors;
- exact-segment-ready timestamp;
- first-byte-served-to-Kodi timestamp;
- contiguous reserve at those moments;
- recovery target;
- subsequent refill trajectory;
- final result: recovered, continuing-low-reserve, no-progress exhaustion, seek superseded, or non-retryable failure.

A diagnostic report should make it obvious if an exact segment sat cached while Kodi was still being blocked on reserve rebuild.

## Acceptance
- Reproduce the failing provider stream in 0.7.22 Buffered Look Ahead and record the A/B baseline against Manual/ISA.
- Same stream/selected rendition plays continuously in Buffered mode without the freeze -> catch-up -> silent-stop cycle under conditions where Manual/ISA is stable.
- Once an exact requested segment becomes available, Kodi receives it without waiting for the full recovery-reserve target.
- A low recovery reserve alone does not terminate playback if requested media continues to arrive.
- No HTTP 504 is returned solely because the configured recovery reserve was not fully rebuilt while media progress continued.
- Background refill still attempts to rebuild the configured reserve.
- HLS-13's startup/high/low/critical reservoir policy remains unchanged.
- HLS-19 retry controls remain effective.
- HLS modes 0-2 remain unchanged.
- Real tests must exercise the non-mocked recovery-reserve wait path.
- Automated fault injection covers:
  - target segment arrives quickly while future refill is slow;
  - repeated exact requested segments are delivered while reserve remains below target;
  - true no-progress exhaustion;
  - eventual refill to healthy reserve;
  - seek superseding an active recovery.
- Target Fire TV acceptance is mandatory.

## Authorization
Created from the user's repeated 0.7.22 target-device failure report and same-stream A/B test on 2026-09-29. The user explicitly stated that the buffering mechanism is degrading playback rather than solving the problem and that the issue needs to be solved.

On 2026-09-29 the user explicitly instructed that everything tracked so far be committed for the next release. HLS-24 is committed next-release scope and remains release-blocking.

## Outcome and next action
Repair the exact-segment/recovery-reserve coupling first, then compare the same stream against Manual/ISA. Use HLS-21/HLS-22 telemetry to determine whether Appi producer throughput also contributes to depletion.


## 0.7.23 implementation evidence
Implementation session `builder-publisher-2026-09-29` uses base `ff256d99b7097dcea3787c3a86582bec29354972`.

The candidate separates ordinary sequential media delivery from reservoir restoration. `recover_segment()` still applies HLS-19 retry/no-progress bounds to the exact requested segment, but once that segment is safely cached it emits exact-ready telemetry and returns it immediately for normal sequential playback. It no longer calls `_wait_reservoir()` before serving that media. Producer threads continue filling in the background and the session clears recovery state only when the configured recovery reserve is restored (or all required remaining media is cached).

Discontinuous seek/cold-resume requests deliberately retain the HLS-12 fresh-epoch reserve gate. New telemetry records exact-segment-ready and first-byte-served boundaries with requested track/index/sequence and reserve state, making it possible to prove that cached required media is not held behind a larger reserve target. Tests cover sequential depleted-media release without invoking the reserve wait; target Fire TV reproduction/A-B acceptance remains mandatory.


## Scope
For 0.7.23, change only Buffered Look Ahead recovery delivery semantics needed to stop starving Kodi: retry the exact requested media under existing bounded recovery policy, release an available sequential segment immediately, continue look-ahead refill asynchronously, and retain the fresh-epoch reserve gate for discontinuous seek/cold resume. Do not alter HLS modes 0–2.


## Evidence
Published 0.7.22 target-device A/B evidence shows the same stream freezing/catching up/stopping in Buffered Look Ahead while Manual fixed-quality/ISA plays normally. Source inspection confirmed `recover_segment()` withheld an already downloaded sequential segment behind `_wait_reservoir()`, which could turn low reserve into a 504. Candidate implementation commit `65868eabc584c2d60bffca8804060b84683e32a1` releases that exact segment immediately for sequential playback while retaining seek/cold-resume reserve gating. Automated unit/smoke tests passed in run `36661239740`; tracker validation, packaging, and target-device acceptance are still pending at this checkpoint.
