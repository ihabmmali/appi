---
id: HLS-22
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-22 — Optimize Buffered Look Ahead producer throughput

## Objective
Determine why Appi's Buffered Look Ahead producer appears to fill substantially more slowly than FFmpeg can ingest the same HLS stream through the same network/VPN path, then remove Appi-side transport bottlenecks without changing the proven reservoir algorithm.

This is explicitly a candidate for the release **after** the currently committed release. It is not part of the current release scope.

## Scope
Benchmark and optimize only the Buffered Look Ahead producer/transport layer in a future release. Preserve the proven reservoir thresholds/accounting, rendition selection, seek epochs, HLS-19 recovery behavior and playback modes 0–2. Any transport concurrency, connection reuse or scheduling change must be evidence-driven and settings-backed where behavior-affecting.

This task remains explicitly excluded from Appi 0.7.22.

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

The user explicitly requested that this be tracked as a **candidate for the release after the one currently being implemented**. HLS-22 is therefore a future-release candidate and is explicitly excluded from the currently committed release.

## Evidence
User-observed A/B evidence: FFmpeg can ingest the same HLS media substantially faster than Appi appears to fill its look-ahead reservoir on the same network/VPN path. Current Appi source uses synchronous per-resource Python HTTP fetches from one prefetch worker per track, which makes connection/request overhead and bounded future-segment concurrency valid hypotheses to measure in the next release cycle. No implementation or target-device optimization result is claimed yet.

## Outcome and next action
After the current committed release is completed, benchmark Appi's producer against FFmpeg on the same stream, then optimize the transport layer only where measurements justify it.
