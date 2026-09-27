---
id: DIAG-2
role: research
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# DIAG-2 — Causal HLS playback telemetry

## Objective
Extend Appi playback diagnostics so a diagnostic package can explain why a playback stall occurred, not merely detect that one occurred.

The capture must preserve a full-session, timestamp-correlated history of playback engine/mode, HLS representation selection, playlist/segment activity, network timing, buffer/read-ahead state where observable, and stall intervals. The resulting bundle should allow development analysis to distinguish CDN/server segment stalls, insufficient throughput, Kodi cache/read-ahead behavior, ABR decisions and Appi playback-engine problems.

This task is the successor to the released [DIAG-1](DIAG-1.md) facility and directly supports [HLS-1](HLS-1.md).

## Scope
Extend the existing bounded diagnostic session model rather than replacing it. Collection must remain active across the entire playback session and must survive playback-mode changes, including switching to/from Adaptive, without resetting or discarding prior evidence.

Capture or derive, where technically accessible:
- Playback engine and quality mode over time, including every mode transition and switch to InputStream Adaptive/ABR.
- Selected HLS representation over time: resolution, advertised bandwidth/bitrate, codecs and a sanitized/stable identifier for the variant URL.
- ABR representation changes, including old/new rendition and timestamp.
- Master/media playlist refreshes, media-sequence values, segment sequence numbers and target/segment durations where available.
- Per-segment HTTP timing: request start, response/start latency, download duration, bytes, calculated effective Mbps, HTTP status, retry count, timeout and error details.
- Kodi/player playable buffer, queue depth or equivalent read-ahead metric over time where exposed.
- Configured Kodi cache capacity/settings separately from observed playable buffered duration/depth.
- Stall start/end timestamps correlated against segment requests, playlist refreshes, rendition changes and buffer history.
- A rolling pre-stall history long enough to show whether playable buffer was progressively draining before the stall.
- Session metadata sufficient to compare a failing run with a working run without exposing authentication material.

The diagnostic must specifically attempt to determine whether Kodi had substantial playable media already buffered before a stall, versus a shallow HLS/player read-ahead queue that drained to zero even though the configured cache capacity was large.

Where Kodi/InputStream Adaptive does not expose a required metric directly, research the least invasive supported observation point: Kodi JSON-RPC/info labels/log events, InputStream Adaptive diagnostics/logging, Appi-side proxy/instrumentation, manifest/segment request wrapping, or derived estimates. The bundle must distinguish directly observed values from inferred/estimated ones.

Preserve DIAG-1 privacy requirements: redact credentials, signed query parameters, cookies and other secrets. Variant and segment URLs may be represented by sanitized host/path classifications and stable hashes while retaining enough identity to correlate repeated requests.

## Acceptance
- One diagnostic session remains continuous from playback start to end/stop/error even if playback mode or engine changes mid-session.
- Every engine/mode transition is timestamped, including switches to Adaptive.
- For multi-variant HLS, the bundle records the selected representation over time with resolution, advertised bandwidth/bitrate, codec and sanitized variant identity where accessible.
- Actual ABR rendition changes are recorded as timestamped transitions rather than inferred only from the initial setting.
- Playlist refreshes and segment sequence numbers are recorded sufficiently to reconstruct the media-fetch timeline where technically accessible.
- Each observable segment request records request start, first-response latency, download duration, size, effective Mbps, HTTP status and retry/timeout/error outcome.
- Stall start/end events are timestamp-correlated with the segment/network, rendition and buffer histories.
- The capture retains enough pre-stall history to determine whether buffer depth was steadily draining before each stall.
- The bundle separately reports configured cache capacity/settings and actual/estimated playable buffered duration or queue depth; it must not treat configured bytes as proof that media was actually buffered.
- The analysis output explicitly classifies whether evidence supports: server/CDN segment delay, sustained insufficient throughput, shallow/empty Kodi read-ahead despite configured cache, ABR transition behavior, Appi playback-engine behavior, or insufficient evidence.
- For each required field that cannot be observed on the supported Kodi target, the diagnostic records the limitation and the attempted observation source instead of silently omitting it.
- A short-lived playback mode is still represented correctly; telemetry must not depend on remaining in a mode for a long sampling interval.
- A target-device failing-stream capture and a comparable working-stream capture are sufficient to answer whether Kodi had substantial playable media buffered immediately before the stall.
- Diagnostic overhead, retention limits and bundle size remain bounded and are measured so debugging does not itself materially cause stalls.
- Existing DIAG-1 sanitization/privacy guarantees remain covered by regression tests.

## Authorization
Requested by the user on 2026-09-26 as an improvement to Appi playback diagnostics after reviewing a diagnostic package that detected stalls but lacked enough causal evidence. This thread is authorized to record and commit the planning changes; implementation, integration and publication remain separate assignments.

## Evidence
The released DIAG-1 record states that per-segment HTTP timing, inputstream buffer level and representation-bitrate history were unavailable in the initial implementation. The user's 2026-09-26 diagnostic review confirmed this gap in practice: a stall was detected, but the package could not establish whether the cause was CDN/server delay, throughput, cache/read-ahead depth, ABR behavior or Appi playback-engine behavior.

The user specifically requires diagnostics to determine whether large configured Kodi cache capacity corresponds to actual playable media buffered before a stall, or whether HLS playback maintains only a shallow read-ahead queue that can drain to zero.

No implementation or target-device verification has yet been performed for DIAG-2.

## Outcome and next action
Assign a research/architecture worker to map the exact observability available from Kodi and InputStream Adaptive, then define the capture points and schema before implementation. The implementation should extend the existing DIAG-1 session/export pipeline and preserve a single timeline across mode changes.
