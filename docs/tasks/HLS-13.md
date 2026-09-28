---
id: HLS-13
role: implementation
status: review
delivery: released
verification: partial
owner: builder-publisher-2026-09-28
base_commit: 4a415f9eaeb48c77ef2fcaa895db90d7e66ab183
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.21.zip
---
# HLS-13 — Implement true deep-reservoir Buffered Look Ahead playback

## Objective
Make Buffered Look Ahead deliver its intended advantage over ordinary HLS playback: prefetch enough of the selected rendition ahead of Kodi, then continuously maintain a deep playable reservoir so intermittent provider stalls do not interrupt playback.

The feature is intended for VOD HLS where provider delivery is bursty or intermittently stalls. It cannot violate throughput physics: if the provider's sustained average delivery rate remains below the selected rendition's consumption rate for long enough, any finite buffer will eventually drain. In that case Appi must report the measured limitation accurately rather than pretending a larger timeout can solve it.

## Scope
Replace Buffered Look Ahead's startup and steady-state cache policy with a capacity-driven producer/consumer reservoir, including shared video/audio capacity, high/low/critical watermarks, continuous refill, progress-aware transfer timeout and truthful reservoir/throughput telemetry. Integrate the reservoir with HLS-12 epochs without changing modes 0–2.

## Current 0.7.20 design problem
The current code does not use the configured buffer as a true startup reservoir.

- Playback readiness is gated by a fixed `DEFAULT_STARTUP_SECONDS = 12`, so playback can begin with only about 12 seconds cached even when the user configured hundreds of MB.
- After startup, each track receives an equal share of only 70% of the session byte capacity:
  `session.max_bytes * 0.70 / len(session.tracks)`.
- With a 128 MB buffer and separate video+audio tracks, the effective per-track budget is about 44.8 MB. That wastes capacity on low-bitrate audio while constraining high-bitrate video.
- Segment transfer currently uses a fixed 10-second wall-clock transfer timeout, which can abort a transfer that is still making progress but is slow.
- The result can favor lower-bitrate renditions even though the purpose of Buffered Look Ahead is to use available time/storage to protect a higher selected bitrate from intermittent delivery stalls.

## Required architecture
Treat Buffered Look Ahead as a producer/consumer reservoir, not a shallow proxy cache.

### Startup
- The user-selected rendition must remain fixed unless the user explicitly chooses another quality.
- Before handing playback to Kodi, Appi must fill a **meaningful fraction of the configured buffer capacity**, not merely a fixed 12-second reserve.
- Startup readiness should be derived from real contiguous playable media at the selected rendition and required associated audio.
- The startup target may be expressed as a configurable/derived high-water mark, but the configured MB value must materially determine how much protection is accumulated before playback starts.
- Audio should consume only the capacity it actually needs; remaining capacity should be available to video rather than statically split 50/50.

### Continuous refill
- Once playback starts, a producer must continuously fetch future segments as quickly as the provider safely allows until the reservoir reaches its high-water mark.
- Kodi should consume only local cached media whenever possible.
- As playback advances, consumed media may be evicted while new future media is fetched, maintaining a rolling reservoir.
- Use explicit high-water, low-water and critical-reserve concepts so the implementation knows whether it is full, draining, or at risk.
- A brief provider stall must consume reserve without interrupting Kodi.
- When provider delivery resumes above playback consumption, the reservoir must refill toward high-water.

### Fetch behavior
- Replace the current fixed total-transfer deadline with progress-aware transfer handling: a transfer that continues receiving data must not fail merely because 10 wall-clock seconds elapsed.
- Keep a bounded inactivity/no-progress timeout and explicit cancellation so genuinely stalled requests still terminate.
- Consider small bounded video-segment concurrency if needed to overcome per-request latency, but do not overload the provider or fetch duplicate segments.
- Keep authenticated/query-string semantics intact.

### Seek/resume integration
- Integrate with [HLS-12](HLS-12.md): a seek or saved-position resume creates a fresh buffer epoch at the new target.
- That new epoch must build its own contiguous startup reservoir before resuming playback.
- Old epoch downloads must not consume or corrupt the new reservoir.

### Observability
- Track and expose actual:
  - contiguous playable seconds ahead;
  - cached bytes ahead;
  - selected rendition nominal bitrate where known;
  - measured provider throughput;
  - buffer fill/drain trend;
  - high/low/critical-water state.
- The simple startup UI should show meaningful fill progress toward the actual reservoir target.
- Detailed debug overlay is handled by HLS-14 but must consume these metrics.

## Acceptance
- A known high-bitrate multi-variant HLS rendition that suffers intermittent provider stalls can be selected explicitly and played after a deeper initial fill without the stalls reaching Kodi, provided measured long-term provider throughput is sufficient to replenish the consumed reserve.
- Lower-bitrate success is not sufficient evidence; target-device acceptance must include the higher rendition that motivated Buffered Look Ahead.
- Increasing configured buffer MB materially increases the actual contiguous playable reserve available to the selected video rendition.
- A 128 MB buffer is not statically divided equally between video and audio; capacity allocation reflects actual track consumption.
- Playback does not start after an arbitrary 12 seconds when substantially more configured reservoir can and should be built.
- The reservoir continuously refills toward high-water during playback.
- Synthetic/provider test with intermittent stalls but average throughput above rendition bitrate plays through without interruption after initial fill.
- Synthetic test with sustained average throughput below rendition bitrate shows predictable reserve depletion and produces an evidence-based message; Appi must not claim buffering can sustain an impossible rate indefinitely.
- Active but slow transfers are not killed solely by a 10-second total wall-clock limit.
- No automatic quality downgrade is used to make the test pass.
- HLS-12 seek/resume fresh epochs use the same reservoir rules.
- Native Kodi and InputStream Adaptive modes remain unchanged.
- Automated tests verify byte-capacity use, dynamic video/audio allocation, high/low-water refill, intermittent-stall masking, sustained-deficit behavior, progress-aware transfer timeout and no duplicate downloads.
- Target-device diagnostics record actual high-water bytes/seconds and measured throughput for both the working lower rendition and the problematic higher rendition.

## Authorization
Created from target-device findings on published 0.7.20 on 2026-09-28. The user explicitly confirmed the buffering algorithm is defective and instructed that these Buffered Look Ahead repairs be committed for the next release. HLS-13 is therefore committed release scope and a release blocker.

## Evidence
Current 0.7.20 source uses a 12-second startup reserve and, after startup, caps each track at 70% of configured capacity divided equally by track count. A 128 MB two-track session therefore gives the video track roughly 44.8 MB of forward cache budget even though audio normally needs far less.

The user reports that lowering the selected buffered rendition makes playback work, while that same lower rendition already works in ordinary InputStream Adaptive mode. The intended Buffered Look Ahead value therefore remains unproven for the higher bitrate.

Automated 0.7.21 candidate run `36381180991` passed shared-capacity/deep-reservoir, high/low-water hysteresis, cached-reserve stall masking, measured sustained-deficit reporting and slow-but-progressing transfer coverage. The deterministic package uses capacity-driven startup/refill with no automatic quality downgrade. The problematic higher-bitrate target-device stream still requires acceptance.

Published in Appi 0.7.21 through PR #10 / merge `d9e0be64681fa2dbe9cc434f81375a9c0992a3e1`. Post-merge verification run `36381516837` and Pages deployment run `36381516378` passed. Published ZIP SHA-256: `0e8c615d40cf9f42e0345c61e11a7b244fc443c8858902d53fffda92c1935c81`. Delivery is released; target-device verification remains partial.

## Outcome and next action
Released in 0.7.21. Complete the remaining target-device acceptance documented above; any new defect or repair must be triaged as follow-up work rather than silently reopening this release scope.


Implementation session 2026-09-28: activated on `release/0.7.21` from base `4a415f9eaeb48c77ef2fcaa895db90d7e66ab183`; authorized scope is implementation, review, integration and publication of the committed next release.


## 0.7.21 target-device evidence
The user reports that Buffered Look Ahead **appears to work well now on 0.7.21**. This is positive target-device evidence for the deep-reservoir redesign.

Do not overstate this as full acceptance unless the remaining documented high-bitrate/seek/resume scenarios are explicitly confirmed. The important distinction is that the core buffering behavior is now materially improved on-device, while the detailed overlay remains a separate failed UI path.
