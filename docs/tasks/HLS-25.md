---
id: HLS-25
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-25 — Make Buffered Look Ahead pause/resume consumer-safe

## Objective
Fix Appi 0.7.23 Buffered Look Ahead pause/resume correctness so pausing Kodi cannot destroy the active buffered session merely because Kodi stops consuming a localhost HLS response, and so duplicate/re-read requests after pause are not falsely treated as seeks.

This is a release-blocking correctness candidate. Do not solve it by increasing network, socket or recovery timeout values.

## Target-device failure
On Appi 0.7.23, pausing Buffered Look Ahead playback — including while browsing/searching/selecting subtitles — can still produce:

1. playback pauses normally;
2. Appi reports `Buffered stream failed (TimeoutError). Please retry playback.`;
3. after resume, video/audio may play briefly;
4. playback then stops silently.

Previous device evidence showed a healthy contiguous reserve around 100+ MB and hundreds of seconds ahead before this failure. This is therefore not to be treated as a buffer-capacity/high-water problem.

## Confirmed source defect A — Kodi-side socket timeout is fatal
`BufferedHlsSession.start()` installs a localhost HTTP server and sets:

```python
self.connection.settimeout(30)
```

The request handler's outer `handle()` suppresses `BrokenPipeError`, `ConnectionResetError` and `TimeoutError`, but the active `do_GET()` request has its own exception handling.

Inside `do_GET()`:
- `BrokenPipeError` and `ConnectionResetError` are treated as harmless request termination;
- `TimeoutError` is **not** included in that local-consumer exception branch;
- a write timeout from `self.wfile.write(...)` therefore falls into the generic exception branch;
- the generic branch calls `session.fail('Buffered stream failed (TimeoutError)...')`;
- the manager observes `session.error` and stops the active buffered session.

During pause Kodi may legitimately stop consuming a response long enough to trigger the local socket timeout. That must be a cancelled/stalled **consumer request**, not a provider/session failure.

### Required repair A
- Classify errors by stage: upstream/provider read/fetch versus localhost/Kodi write.
- A Kodi-side disconnect, broken pipe, reset or write timeout while serving cached media must not call `session.fail()`.
- Release file handles, pins and per-request state safely.
- Retain the Buffered Look Ahead session so Kodi may reconnect/re-request after pause.
- Record a bounded diagnostic event for the cancelled consumer request.
- Do not hide genuine upstream/provider inactivity timeouts; those remain governed by the HLS-19 recovery policy.
- Do not merely increase the 30-second socket timeout. Semantic pause safety is required regardless of pause duration.
- Preserve the default unlimited pause-retention policy.

## Confirmed source defect B — duplicate/re-read requests become false seeks
`_Track._serve_segment()` currently determines discontinuity using:

```python
expected = self.last_requested + 1
is_seek = index != expected
```

Any request that is not exactly the next index is therefore treated as a seek and creates a fresh HLS-12 epoch.

That includes legitimate Kodi behavior such as:
- re-requesting the current segment;
- retrying a recently served segment;
- reading the same resource again with a Range request;
- resuming on a nearby HLS boundary after pause.

The localhost handler currently calls `session.serve_file(resource_id)` — which enters `_serve_segment()` — **before** it parses the HTTP `Range` header. A same-resource range re-read can therefore be falsely classified as a seek before the track layer even knows it was a range request.

High epoch counts observed on-device without equivalent user seeks are consistent with this defect.

### Required repair B
Introduce explicit request classification rather than `index != last_requested + 1`.

At minimum distinguish:
- sequential next segment;
- duplicate same-segment request;
- recent re-read/retry;
- HTTP range re-read of the same resource;
- adjacent resume request;
- genuine forward discontinuity;
- genuine backward discontinuity;
- cold non-zero resume.

Requirements:
- duplicate/current/recently-served re-reads normally remain in the current epoch;
- range re-reads of the same resource never create a seek epoch;
- pause/resume without a user position change retains the same epoch;
- only meaningful timeline discontinuities create a fresh HLS-12 epoch;
- true forward/backward seeks and cold resume retain the existing fresh-epoch behavior;
- stale-epoch safety and selected rendition behavior remain intact.

The HTTP layer may need to pass request/range context into the track-serving path rather than classifying the request without that information.

## Diagnostics
For every localhost consumer timeout/error or discontinuous media request, record enough bounded telemetry to establish cause without exposing authenticated URLs:

- stage: provider-read/provider-write/local-file-read/Kodi-write;
- exception type and safe message/category;
- resource kind, track, index and sequence;
- HTTP range request presence/range class;
- player state: playing/paused/buffering/stopped/unknown;
- epoch ID and reason;
- previous `last_requested` and `last_served`;
- newly requested index;
- request classification: sequential/duplicate/range-reread/recent-reread/adjacent/discontinuity/cold-resume;
- contiguous reserve and total cached bytes;
- whether the session was retained or terminated;
- explicit termination reason when terminated.

## Preservation constraints
Do not change:
- HLS-13 startup/high/low/critical reservoir policy;
- HLS-22 producer concurrency defaults solely to address pause;
- HLS-24 exact-segment release behavior;
- selected rendition/quality;
- HLS modes 0–2.

This is a correctness fix around local consumer lifecycle and request classification.

## Acceptance
- Pause for 5–10 seconds and resume successfully.
- Pause for more than 30 seconds and resume successfully.
- Pause for several minutes while browsing/selecting subtitles and resume successfully.
- No `Buffered stream failed (TimeoutError)` merely because Kodi stopped consuming a localhost response while paused.
- No Buffered Look Ahead session teardown from a paused-client socket timeout/disconnect.
- Duplicate/re-read media requests after pause do not create false seek epochs.
- HTTP range re-reads of the same resource do not create seek epochs.
- Pause/resume with unchanged playback position stays in the same epoch.
- Genuine manual forward and backward seeks still create fresh epochs and work.
- Cold non-zero resume still uses the correct fresh-epoch path.
- Playback remains on the selected rendition.
- Existing reservoir/startup/high-water/low-water behavior is unchanged.
- Modes 0–2 remain unchanged.
- Automated tests inject a Kodi-side write timeout and prove the session remains alive.
- Automated tests distinguish provider-side media timeout from Kodi-side write timeout.
- Automated request-sequence tests cover duplicate, same-index range read, recent re-read, sequential next, true forward seek and true backward seek.
- Target Fire TV acceptance is mandatory, including a several-minute subtitle-search pause.

## Authorization
Reported by the user on 2026-09-29 from Appi 0.7.23 target-device testing, with source-level findings supplied by another diagnostic thread in the same project. The user explicitly instructed that this be treated as a candidate correctness fix / release blocker, not a timeout-tuning feature.

HLS-25 is a ready release-blocking candidate and is not committed to release scope until explicitly selected under AGENTS.md.

## Evidence
Current 0.7.23 source confirms both key boundaries:
- localhost connections use a 30-second socket timeout, while `do_GET()` treats `TimeoutError` through the fatal generic `session.fail()` path rather than the harmless Kodi-consumer disconnect path;
- `_Track._serve_segment()` defines seek as any index other than `last_requested + 1`, and Range processing occurs only after `serve_file()` has already invoked that classification.

The healthy pre-pause reserve observation argues strongly against buffer-capacity depletion as the cause of this failure.

## Outcome and next action
Implement stage-aware local-consumer exception handling and request-aware discontinuity classification. Prove pause safety independently from provider recovery and prove true seeks still use HLS-12 fresh epochs.
