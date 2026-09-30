---
id: HLS-22
role: implementation
status: review
delivery: unreleased
verification: partial
owner: builder-publisher-2026-09-29
base_commit: ff256d99b7097dcea3787c3a86582bec29354972
artifact: none
---
# HLS-22 — Optimize Buffered Look Ahead producer throughput

## Objective
Determine why Appi's Buffered Look Ahead producer appears to fill substantially more slowly than FFmpeg can ingest the same HLS stream through the same network/VPN path, then remove Appi-side transport bottlenecks without changing the proven reservoir algorithm.

This task is committed scope for Appi 0.7.23. The optimization remains below the reservoir policy and must not alter modes 0–2.

## Scope
Benchmark and optimize only the Buffered Look Ahead producer/transport layer in Appi 0.7.23. Preserve the proven reservoir thresholds/accounting, rendition selection, seek epochs, HLS-19 recovery behavior and playback modes 0–2. Any transport concurrency, connection reuse or scheduling change must be evidence-driven and settings-backed where behavior-affecting.

This task was excluded from Appi 0.7.22 and is included in the 0.7.23 release scope.

## User evidence
The user tested the same media using FFmpeg and observed that FFmpeg could download the entire stream dramatically faster than Appi appears to fill its look-ahead reservoir under the same network and VPN conditions.

That comparison demonstrates that provider/network capacity may be substantially higher than Appi's observed fill rate and makes Appi's producer implementation a concrete performance boundary to investigate.

## Current Appi producer behavior
0.7.21 uses one prefetch thread per track. Each track:
1. finds the next missing segment;
2. downloads that resource synchronously;
3. waits for completion;
4. advances to the next missing segment.

Media transfer currently uses Python `urllib.request.urlopen()` per resource. The implementation has no explicit reusable HTTP connection pool and no bounded multi-segment video fetch queue.

Track balancing also prevents one required track from getting more than the configured prefetch-lead threshold ahead of the slowest required track.

## Hypotheses to test
At minimum compare:

### A. Per-request connection/TTFB overhead
Appi may spend substantial time establishing individual HTTP/TLS requests for sequential HLS segments. Measure connection/TTFB separately from payload-transfer time.

### B. Lack of persistent HTTP connection reuse
Determine whether a persistent connection/session materially improves aggregate segment ingest rate for the target provider.

### C. Lack of bounded segment concurrency
Test a small bounded number of simultaneous future-segment transfers while preserving in-order playable-reserve accounting and avoiding duplicate fetches/provider overload.

### D. Track-balancing interaction
Determine whether audio/video balancing or the prefetch-lead limiter is unnecessarily constraining video producer throughput when the other required track is already sufficiently protected.

### E. Header/client behavior
Compare relevant request headers and HTTP behavior with FFmpeg only if A-D do not explain the throughput difference. Do not impersonate another client merely to bypass provider policy.

## Preservation constraints
This task must not redesign the working HLS-13 reservoir policy.

Preserve:
- configured capacity semantics;
- startup/high/low/critical watermark behavior;
- contiguous playable-reserve accounting;
- selected rendition/quality behavior;
- epoch/seek ownership;
- HLS-19 recovery semantics;
- modes 0-2.

The optimization is below the reservoir: make the producer capable of filling/refilling it faster.

## Configurability rule
Any new behavior-affecting transport parameter introduced by this work must follow the project rule established in ARCHITECTURE.md and be settings-backed rather than hard-coded.

Examples include, if adopted:
- maximum concurrent segment fetches;
- connection-pool size;
- request pipeline depth;
- per-host concurrency limit;
- transport retry/backoff tuning.

Defaults must be conservative, validated, and chosen from measured target-device/provider behavior.

## Required measurements
For the same stream/rendition and as nearly identical conditions as practical, record:
- FFmpeg aggregate ingest Mbps;
- Appi aggregate ingest Mbps;
- selected rendition nominal Mbps;
- average and percentile request/TTFB latency;
- payload transfer Mbps excluding request setup;
- requests/segments per second;
- connection reuse count where observable;
- active concurrent fetch count;
- reservoir fill rate in MB/s;
- startup target fill time;
- refill time from low-water to high-water.

Use the same VPN/network path and same authenticated/pre-authorized media URL where possible.

## Candidate implementation directions
Only after measurement supports them:
- persistent HTTP connection/session reuse;
- bounded parallel future-segment downloads;
- lower-overhead request scheduling;
- target-priority fetching that keeps the next required segment authoritative while later segments may download concurrently.

Concurrent work must commit completed media into contiguous playable order. A faster producer must never make later cached segments count as playable through a missing earlier segment.

## Acceptance
- Establish an objective Appi-vs-FFmpeg ingest-rate baseline on the same stream/rendition.
- Identify the dominant Appi-side transport bottleneck or explicitly show that Appi is not the limiting factor.
- If Appi is slower, materially improve producer fill/refill throughput without changing the HLS-13 reservoir behavior.
- Startup target and refill watermarks remain behaviorally equivalent when using the same settings.
- No duplicate downloads or out-of-order playable-reserve accounting.
- Required audio/video coherence is preserved.
- Seek/resume epochs cancel or ignore stale concurrent work correctly.
- HLS-19 recovery continues to prioritize the exact next required media.
- Automated tests cover concurrency/order/cancellation/duplicate suppression if concurrency is introduced.
- Target-device verification compares before/after startup fill time and low-to-high refill time.
- Any new transport tuning parameters are exposed through settings with documented defaults.

## Authorization
Requested by the user on 2026-09-28 after observing that FFmpeg can ingest the same stream much faster than Appi's buffer appears to fill on the same network/VPN connection.

On 2026-09-29 the user explicitly instructed that everything tracked so far be committed for the next release, including the debug-display defect. HLS-22 is now committed next-release scope. It remains constrained to optimize producer transport without changing the proven reservoir policy.

## Evidence
User-observed A/B evidence: FFmpeg can ingest the same HLS media substantially faster than Appi appears to fill its look-ahead reservoir on the same network/VPN path. Current Appi source uses synchronous per-resource Python HTTP fetches from one prefetch worker per track, which makes connection/request overhead and bounded future-segment concurrency valid hypotheses to measure in the next release cycle. No implementation or target-device optimization result is claimed yet.

## Outcome and next action
After the current committed release is completed, benchmark Appi's producer against FFmpeg on the same stream, then optimize the transport layer only where measurements justify it.


## 0.7.22 same-stream ISA evidence
The user tested the exact stream that fails in Buffered Look Ahead using Manual fixed-quality mode. Manual mode delegates the provider master URL to InputStream Adaptive and plays without stutter or failure.

This materially strengthens the HLS-22 hypothesis: Appi's own proxy/producer transport may be creating depletion that ISA does not experience. Benchmark against both FFmpeg and the stable Manual/ISA control case. Keep HLS-24's recovery-gating correctness repair separate; faster producer transport must not be used to hide a serving-path deadlock/block.


## 0.7.23 implementation evidence
Implementation session `builder-publisher-2026-09-29` uses base `ff256d99b7097dcea3787c3a86582bec29354972`.

The candidate adds settings-backed bounded producer concurrency with a conservative default of two future segment fetches per active track (range 1–4). Each worker claims a distinct segment index before download; the existing per-resource condition still suppresses duplicate network fetches, stale epoch completion remains ignored, and playable-reserve accounting remains contiguous through the first missing segment. Transfer telemetry now records concurrent-fetch count and session status exposes configured/active/peak producer concurrency alongside existing request latency and payload-throughput measurements.

This is an Appi-side transport optimization supported by the user's FFmpeg/ISA A/B evidence and deterministic concurrency tests. It does **not** claim the provider-specific FFmpeg-vs-Appi target-device throughput comparison is complete; startup/refill before/after measurement on the Fire TV remains required for full acceptance. Persistent HTTP connection reuse is not claimed in this candidate.


## 0.7.23 self-review
Self-review completed by the builder/publisher thread against the exact release candidate. This is a self-review, not an independent review.

Automated release run `36661752457` passed 103 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/hash/index inspection and packaging. Deterministic candidate artifact commit: `640b06e9ee2a464ad1c8e6af4b18b528b5fd5d1e`. Candidate ZIP SHA-256: `029e2a33b52f235746ce79f8e6140f569addefb549fcebf757c786a5171ca6ff`.

Code review confirms bounded per-track concurrency is isolated to Buffered Look Ahead, the default is settings-backed at two workers (range 1–4), workers claim distinct future indices, per-resource duplicate suppression remains intact, stale epoch completion remains ignored, and contiguous reserve accounting still stops at the first missing segment. Existing playback modes 0–2 are untouched.

Verification remains **partial** because the acceptance criteria explicitly require same-stream Fire TV/provider measurements against FFmpeg/ISA, including startup/refill timing and effective aggregate ingest rate. Persistent HTTP connection reuse was investigated as a hypothesis but is not implemented or claimed in this release. The release therefore ships the bounded-concurrency improvement without claiming the full provider-specific throughput investigation is complete.
