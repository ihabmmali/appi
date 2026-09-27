---
id: DIAG-1
role: review
status: review
delivery: released
verification: partial
owner: ChatGPT build session 2026-09-26
base_commit: 8a9b1ad21b3944d8045e1d1abff2a2556c3035cc
artifact: https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.13.zip
---
# DIAG-1 — Export bounded playback diagnostics

## Objective
Add an optional Appi debug mode that can capture enough playback/network evidence to diagnose intermittent and repeated buffering without requiring the user to manually collect multiple Kodi logs.

When enabled, the add-on should gather a bounded diagnostic record around playback and stall events, then let the user export a compressed diagnostic bundle to a user-configurable Kodi/VFS source location. The primary consumer is the Appi development workflow, especially [HLS-1](HLS-1.md).

## Scope
Research and specify the minimum useful diagnostic dataset and Kodi APIs/hooks before implementation. The feature should cover HLS playback first and avoid changing normal playback behavior when debugging is disabled.

Candidate evidence to evaluate:
- Appi version, Kodi version/platform, selected playback engine/path and relevant playback/cache settings.
- Sanitized stream identity plus manifest/rendition structure, selected rendition, segment sequence/duration and timestamps.
- Per-request HTTP status, latency, transfer duration, bytes/estimated throughput, retries and failures where observable.
- Playback/stall timing and any observable buffer state, player state transitions, errors and inputstream/native-player messages.
- A bounded excerpt of relevant Kodi/Appi logs correlated by timestamp.
- A comparison-friendly session identifier and timestamps so a working and failing playback can be contrasted.

The export must be bounded by configurable or safe fixed limits (time, event count and/or size), must not grow indefinitely, and should minimize runtime overhead. Export should write one compressed archive to a location selected through Kodi-compatible storage/VFS handling, including local and supported network sources where Kodi permits writing.

Sensitive data must be sanitized before export. Do not include authentication tokens, cookies, credentials, full pre-authenticated URLs, subtitle contents, unrelated Kodi history, or other unnecessary personal data. Preserve enough non-secret URL/manifest identity (for example host/path classification and/or stable hashes) to correlate requests.

Open research questions include which buffer metrics and low-level segment timings Kodi exposes to a Python video add-on, whether Kodi log access is sufficiently scoped, and what measurements require Appi-side HTTP instrumentation versus player/inputstream logs.

## Acceptance
- Document the exact diagnostic fields available on the supported Kodi target and identify unavailable fields explicitly.
- Define a bounded capture model that can be enabled/disabled without materially affecting normal playback when disabled.
- Define automatic capture around playback/stall events plus an explicit user action to export the current/recent diagnostic session.
- Define sanitization/redaction rules that prevent secrets such as signed query parameters, credentials and cookies from entering the bundle.
- Define a compressed bundle format with a machine-readable summary/index and timestamp-correlated evidence suitable for development analysis.
- Allow the export destination to be selected from a writable Kodi-compatible source/location and report export failures clearly without losing the current capture.
- Demonstrate that one failing playback capture and one working playback capture contain enough common fields to support the comparison required by HLS-1.
- Record storage/performance limits and verify repeated debugging sessions cannot consume unbounded profile storage.

## Authorization
Requested by the user on 2026-09-24 as a proposed next-release change for troubleshooting the recurring buffering issue. This authorizes triage/planning records only; implementation, integration and publication remain separate assignments.

## Evidence
User report: some streams can begin buffering frequently despite no apparent bandwidth constraint and despite substantially increasing Kodi cache size. Existing [HLS-1](HLS-1.md) already requires manifest, segment-timing and Kodi/inputstream evidence.

The released 0.7.13 implementation successfully provides bounded session capture/export and stall detection, but its own availability map records per-segment HTTP timing, inputstream buffer level and representation/bitrate history as unavailable. On 2026-09-26 the user confirmed that a generated diagnostic package could detect stalls but still could not determine their cause. [DIAG-2](DIAG-2.md) tracks the required causal-telemetry expansion.

## Build session — 2026-09-26
- User authorization: all candidates committed to the next release; implementation, integration and publication explicitly authorized.
- Release branch: `release/0.7.13`; base: `8a9b1ad21b3944d8045e1d1abff2a2556c3035cc`.
- Planned paths: plugin.video.appi/resources/lib/diagnostics.py; app.py; subtitle_service.py; settings/tests.
- This worker owns the committed release sequence; review will be recorded as self-review unless independent evidence is added.

## Review evidence — 2026-09-26
- Added opt-in bounded playback-session capture with a maximum event/session retention policy and ZIP export through Kodi VFS.
- Stream identity stores scheme/host/extension plus hashes, not raw paths/query strings; credentials, cookies and subtitle contents are excluded.
- The exported availability map explicitly marks per-segment HTTP timing, inputstream buffer level and representation-bitrate history unavailable when Kodi Python does not expose them.
- Automated privacy regression verifies an authenticated signed URL does not leak credentials, query secrets or raw media path into the bundle.
- Verification is partial pending export/capture from one working and one repeatedly stalling stream on the target device.

## Outcome and next action
DIAG-1 established the initial reusable diagnostic export facility and remains the shipped 0.7.13 record. Its target-device use exposed an observability gap: stall detection alone is insufficient to distinguish server/CDN, throughput, buffer/read-ahead, ABR and playback-engine causes. Continue the diagnostic capability through [DIAG-2](DIAG-2.md) rather than rewriting the shipped DIAG-1 outcome.

## Publication — 0.7.13
- Published to `main` in merge commit `0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a` on 2026-09-26/27.
- Post-merge release verification: GitHub Actions run 36287058096 passed the full automated gate.
- Artifact: `plugin.video.appi-0.7.13.zip`; 0.7.8 remains the known-good fallback.
- Delivery is released; verification remains partial until the task's documented target-device checks are completed.
