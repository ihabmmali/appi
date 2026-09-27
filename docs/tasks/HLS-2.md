---
id: HLS-2
role: review
status: review
delivery: released
verification: failed
owner: ChatGPT build session 2026-09-26
base_commit: 8a9b1ad21b3944d8045e1d1abff2a2556c3035cc
artifact: https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.13.zip
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

Coordinate with [HLS-1](HLS-1.md) because ABR behavior may affect the repeated-stall investigation, and with [DIAG-2](DIAG-2.md) so diagnostics can record selected rendition/variant changes when observable. The 0.7.13 manual-selector regression is tracked separately in [HLS-4](HLS-4.md).

## Acceptance
- Confirm which current Appi mode/path is used for each HLS quality choice and document it against the actual source.
- Reproduce the user's observation for "Limit maximum bitrate": determine whether it chooses the highest rendition below the ceiling only once or continues to adapt dynamically.
- Verify whether the supported InputStream Adaptive version dynamically changes HLS representations during playback under changing throughput/buffer conditions.
- Distinguish startup rendition selection from runtime adaptation; do not call a mode ABR unless representation changes are observed or otherwise verifiably supported.
- If dynamic switching is supported, expose an explicitly named Adaptive Bitrate / Variable Bitrate mode.
- Allow ABR to operate without an unnecessarily low fixed cap, while supporting an optional user maximum bitrate and preserving per-title/show overrides.
- Keep manual/fixed rendition playback as a distinct path, but require HLS-4 target-device acceptance before relying on the 0.7.13 implementation.
- Clearly distinguish Kodi-native automatic playback, ceiling-limited fixed/initial selection, and true InputStream Adaptive ABR in settings/help text.
- Define fallback behavior when InputStream Adaptive is unavailable or the manifest contains only one rendition.
- Verify startup rendition choice and up/down switching with a controlled multi-variant HLS test or equivalent observable evidence.
- Record whether switching introduces discontinuities, stalls or resolution oscillation on the target device.
- Ensure HLS-1 diagnostics can identify whether a stall occurred during a representation switch when that information is available.

## Authorization
Requested by the user on 2026-09-24 after asking whether current Automatic mode already performs variable bitrate adaptation. The user subsequently reported that the existing maximum-bitrate mode appears to choose the highest rendition below the ceiling rather than dynamically varying bitrate. This triage thread is authorized to record and plan the task; implementation, integration and publication remain separate assignments.

## Evidence
Current Appi source in `resources/lib/app.py` shows `hls_mode == 0` returns without selecting InputStream Adaptive, while the maximum-bitrate path explicitly sets `inputstream.adaptive.stream_selection_type` to `adaptive` and supplies `chooser_bandwidth_max`.

User device observation on 2026-09-24: "Limit maximum bitrate" appears to select the highest stream quality lower than the configured maximum limit and then use that rendition.

0.7.13 introduced a new Appi-owned manual fixed-rate chooser. On 2026-09-26 the user reported that this chooser displays incorrect rendition information and every selection fails playback, requiring rollback to 0.7.12. Although ABR itself still needs separate runtime verification, this is a failed target-device acceptance result for the released HLS-mode work and is tracked in HLS-4.

## Build session — 2026-09-26
- User authorization: all candidates committed to the next release; implementation, integration and publication explicitly authorized.
- Release branch: `release/0.7.13`; base: `8a9b1ad21b3944d8045e1d1abff2a2556c3035cc`.
- Planned paths: plugin.video.appi/resources/lib/hls.py; app.py; settings/tests.
- This worker owns the committed release sequence; review will be recorded as self-review unless independent evidence is added.

## Review evidence — 2026-09-26
- The settings model now separates Native Kodi automatic, Manual fixed quality and Adaptive bitrate (InputStream Adaptive).
- Explicit ABR config sets InputStream Adaptive with stream_selection_type=adaptive; maximum bitrate is optional and 0 means no Appi ceiling. Manual fixed quality no longer delegates its chooser to InputStream Adaptive.
- Unit/smoke coverage verifies master-playlist parsing, manual-mode isolation and the adaptive property/cap path.
- Target-device acceptance failed for the manual fixed-rate path: the user's provider/device shows incorrect rendition metadata and playback failure for every manual selection. ABR representation-switch behavior remains separately unverified.

## Outcome and next action
Do not treat the 0.7.13 HLS-mode implementation as accepted. Repair HLS-4 first using the 0.7.12 working path as reference, then resume ABR verification for this task.

## Publication — 0.7.13
- Published to `main` in merge commit `0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a` on 2026-09-26/27.
- Post-merge release verification: GitHub Actions run 36287058096 passed the automated gate.
- Artifact: `plugin.video.appi-0.7.13.zip`.
- Delivery is released, but target-device verification is failed for the manual playback portion of the HLS-mode work.
