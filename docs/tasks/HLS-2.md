---
id: HLS-2
role: research
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-2 — Explicit adaptive bitrate HLS mode

## Objective
Make adaptive/variable-bitrate HLS playback an explicit and understandable Appi playback mode rather than relying on the ambiguous label "Automatic - Kodi default".

Current source behavior distinguishes three cases:
- "Automatic - Kodi default" leaves HLS handling to Kodi and does not explicitly select InputStream Adaptive.
- "Ask quality before playback" uses InputStream Adaptive with manual quality selection.
- "Limit maximum bitrate" uses InputStream Adaptive with `stream_selection_type=adaptive` and a configured maximum bandwidth.

The user reports that the existing maximum-bitrate mode appears to select the highest rendition below the configured ceiling and then remain on that rendition. That observation must be treated as runtime evidence to verify, not assumed to be true ABR.

The desired behavior is an explicit Adaptive Bitrate (ABR) mode that can actually move among variants during playback when supported, optionally constrained by a user-selected maximum bitrate/resolution.

## Scope
Research and verify current InputStream Adaptive behavior on the supported Kodi target before changing labels or playback semantics.

Define a user-facing HLS mode model that clearly separates:
- Kodi/native automatic handling.
- Manual fixed rendition selection.
- Ceiling-based fixed/initial rendition selection, if that is what the current maximum-bitrate path actually does.
- True adaptive bitrate selection that can change representations during playback.
- Optional ABR ceilings such as maximum bitrate and, if supported/useful, resolution.

Avoid implying seamless bitrate switching unless device evidence confirms the installed InputStream Adaptive version performs it for the provider's multi-variant HLS manifests.

Coordinate with [HLS-1](HLS-1.md) because ABR behavior may affect the repeated-stall investigation, and with [DIAG-1](DIAG-1.md) so diagnostics can record selected rendition/variant changes when observable.

## Acceptance
- Confirm which current Appi mode/path is used for each HLS quality choice and document it against the actual source.
- Reproduce the user's observation for "Limit maximum bitrate": determine whether it chooses the highest rendition below the ceiling only once or continues to adapt dynamically.
- Verify whether the supported InputStream Adaptive version dynamically changes HLS representations during playback under changing throughput/buffer conditions.
- Distinguish startup rendition selection from runtime adaptation; do not call a mode ABR unless representation changes are observed or otherwise verifiably supported.
- If dynamic switching is supported, expose an explicitly named Adaptive Bitrate / Variable Bitrate mode.
- Allow ABR to operate without an unnecessarily low fixed cap, while supporting an optional user maximum bitrate and preserving per-title/show overrides.
- Keep "Ask quality before playback" as a distinct manual/fixed-rendition path.
- Clearly distinguish Kodi-native automatic playback, ceiling-limited fixed/initial selection, and true InputStream Adaptive ABR in settings/help text.
- Define fallback behavior when InputStream Adaptive is unavailable or the manifest contains only one rendition.
- Verify startup rendition choice and up/down switching with a controlled multi-variant HLS test or equivalent observable evidence.
- Record whether switching introduces discontinuities, stalls or resolution oscillation on the target device.
- Ensure HLS-1 diagnostics can identify whether a stall occurred during a representation switch when that information is available.

## Authorization
Requested by the user on 2026-09-24 after asking whether current Automatic mode already performs variable bitrate adaptation. The user subsequently reported that the existing maximum-bitrate mode appears to choose the highest rendition below the ceiling rather than dynamically varying bitrate. This triage thread is authorized to record and plan the task; implementation, integration and publication remain separate assignments.

## Evidence
Current Appi source in `resources/lib/app.py` shows `hls_mode == 0` returns without selecting InputStream Adaptive, while the maximum-bitrate path explicitly sets `inputstream.adaptive.stream_selection_type` to `adaptive` and supplies `chooser_bandwidth_max`.

User device observation on 2026-09-24: "Limit maximum bitrate" appears to select the highest stream quality lower than the configured maximum limit and then use that rendition. This suggests the current user-visible behavior may be ceiling-based rendition selection rather than true runtime ABR, but direct instrumentation/controlled testing is still required.

Kodi/InputStream Adaptive runtime representation-switch behavior on the target device remains to be verified directly.

## Outcome and next action
Do not assume the current maximum-bitrate path already satisfies the ABR requirement. A research worker should reproduce the user's observation, determine whether runtime representation switching occurs, and then recommend the smallest source/UI change needed to expose genuinely adaptive playback if supported.
