---
id: DIAG-1
role: research
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
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
User report: some streams can begin buffering frequently despite no apparent bandwidth constraint and despite substantially increasing Kodi cache size. Existing [HLS-1](HLS-1.md) already requires manifest, segment-timing and Kodi/inputstream evidence, but collection is currently manual/not yet specified.

No implementation or device verification has been performed for DIAG-1.

## Outcome and next action
Keep DIAG-1 separate from HLS-1: DIAG-1 should establish a reusable diagnostic export facility; HLS-1 should use its evidence to diagnose the specific repeated-stall problem. Assign a research worker to map Kodi observability and finalize the capture schema before implementation.
