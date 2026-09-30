---
id: HLS-23
role: implementation
status: review
delivery: unreleased
verification: partial
owner: builder-publisher-2026-09-29
base_commit: ff256d99b7097dcea3787c3a86582bec29354972
artifact: none
---
# HLS-23 — Fix Buffered Look Ahead overlay gating and screen-safe layout

## Objective
Make the Buffered Look Ahead on-screen status/debug renderer obey its setting reliably and render all enabled telemetry within the visible screen area on the target Fire TV/Kodi environment.

This is a successor to HLS-16 target-device verification of published 0.7.22. Do not alter the Buffered Look Ahead reservoir or recovery algorithm while fixing the renderer.

## 0.7.22 target-device observations
The user reports:
- `Appi buffering` appears during playback even when the Buffered Look Ahead detailed debug overlay setting is disabled;
- on some occasions the full detailed debug display also appears while the setting is disabled;
- when the full debug display is visible, its single-line text exceeds the screen width rather than wrapping or using multiple lines;
- buffering itself appears improved in 0.7.22, but additional playback testing is still required.

## Confirmed source behavior
The current `buffered_ui.status_text()` intentionally returns a simple `Appi buffering — ...` string when `recovering` is true even if `debug=False`.

The English setting help also states: `The simple buffering indicator is always enabled.`

The 0.7.22 automated test `test_overlay_is_purely_presentational_and_disabled_is_silent` explicitly asserts this simple-message behavior after setting `recovering=True`. That test name is therefore inconsistent with what it actually verifies.

The detailed text path builds one long pipe-separated string. The bundled `AppiBufferOverlay.xml` renders it through one label control approximately 1840 pixels wide with no multiline/wrapping layout.

The user's observation that the **full** detailed text sometimes appears while the setting is disabled is not explained by the intended simple-message path and requires separate reproduction/instrumentation.

## Required visibility contract
The existing `buffered_debug_overlay` setting becomes the authoritative master gate for this renderer:

- when disabled, **no BufferOverlay text may be shown**, including the simple `Appi buffering` message;
- disabling the setting while an overlay is already visible must close it promptly and clear stale text/state;
- when enabled, the renderer may show concise recovery status and the full detailed metrics as appropriate;
- no cached setting value, stale dialog state, fallback renderer, or prior debug text may cause the overlay to reappear while disabled.

If a future design wants a permanently enabled buffering indicator, it must be a separately named/settings-backed user option rather than bypassing the debug-overlay setting.

Update the setting help text so it matches the actual behavior.

## Layout requirements
Do not render the detailed telemetry as an unbounded single-line string.

Use a screen-safe layout such as:
- multiple bounded label rows; or
- a multiline/textbox control proven to wrap correctly on the supported Kodi/Fire TV target.

At minimum group information logically across lines, for example:
1. playable reserve / target / total cache;
2. seconds ahead / state / epoch;
3. selected bitrate / provider throughput;
4. recovery attempt / missing-track information when applicable.

Requirements:
- stay inside the 1920x1080 safe region with reasonable left/right margins;
- no horizontal clipping or off-screen overflow;
- avoid covering an excessive portion of the video;
- preserve readability at the target device's actual UI scale;
- optional fields may be omitted or abbreviated rather than forcing overflow;
- fallback renderer must obey the same width/gating contract.

## Instrumentation for the disabled-state leak
Log enough state on overlay create/update/close to determine why full debug text can appear while disabled, including:
- current effective setting value;
- requested render mode (disabled/simple/detailed);
- renderer type;
- whether a window already existed;
- close reason;
- text-mode transition, without logging URLs or sensitive stream data.

Do not spam normal logs; log state transitions and anomalous disabled-state render attempts.

## Acceptance
- On the target Fire TV, setting OFF produces no `Appi buffering` overlay and no detailed debug overlay during normal playback, refill, recovery, seek or pause/resume.
- Turning the setting OFF while the overlay is visible removes it promptly and it does not reappear until re-enabled.
- Setting ON shows the intended live telemetry.
- No stale full-debug text appears after transition from enabled to disabled.
- Detailed telemetry remains fully within screen bounds.
- Long values and optional metrics do not force horizontal overflow.
- WindowXMLDialog and compatibility fallback paths both obey the same gating semantics.
- Automated tests assert OFF is completely silent even when `recovering=True`.
- Automated tests cover enable -> visible -> disable -> closed transitions and prevent stale-text reappearance.
- Automated layout checks verify multiline/bounded controls rather than one unrestricted label.
- Target-device acceptance is mandatory; mocked renderer success alone is insufficient.
- HLS-13/HLS-19 buffering and recovery behavior is unchanged.

## Authorization
Created from target-device observations on published Appi 0.7.22 reported by the user on 2026-09-29. On 2026-09-29 the user explicitly instructed that everything tracked so far be committed, specifically including the debug-message display bug. HLS-23 is committed next-release scope.

## Outcome and next action
Correct the overlay visibility contract and layout, instrument the unexplained full-debug disabled-state leak, and verify the renderer on the Fire TV without touching the buffering algorithm.


## 0.7.23 implementation evidence
Implementation session `builder-publisher-2026-09-29` uses base `ff256d99b7097dcea3787c3a86582bec29354972`.

The candidate makes `buffered_debug_overlay` the master gate: when false, `status_text()` returns no text even during recovery/caching and `BufferOverlay.update()` closes any existing renderer. Enabled detail is four bounded lines rather than one pipe-delimited line. The bundled renderer changes to a 1180×180 textbox; the compatibility path uses a textbox when available and otherwise four bounded label rows. State-transition logging records effective enabled state, requested mode, renderer, pre-existing window and close reason without stream URLs.

Automated coverage is added for OFF during recovery, enabled→visible→disabled closure, stale-text non-reappearance, and bounded multiline XML layout. Target Fire TV visibility/scale verification remains required.


## Scope
For 0.7.23, change only the Buffered Look Ahead on-screen renderer and its instrumentation: make the existing debug-overlay setting authoritative, close stale renderer state when disabled, use a bounded multiline layout when enabled, and keep GUI failures non-fatal. Do not alter reservoir/recovery behavior or HLS modes 0–2.


## Evidence
Published 0.7.22 target-device evidence shows buffering/debug text while the setting is disabled and single-line detail overflowing the screen. Source inspection confirmed the simple recovery string deliberately bypassed the debug flag. Candidate implementation commit `65868eabc584c2d60bffca8804060b84683e32a1` makes OFF silent, closes existing windows, uses four bounded rows, and adds transition logs. Automated unit/smoke tests passed in run `36661239740`; tracker validation, packaging, and target-device acceptance are still pending at this checkpoint.


## 0.7.23 self-review
Self-review completed by the builder/publisher thread against the exact release candidate. This is a self-review, not an independent review.

Automated release run `36661752457` passed 103 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/hash/index inspection and packaging. Deterministic candidate artifact commit: `640b06e9ee2a464ad1c8e6af4b18b528b5fd5d1e`. Candidate ZIP SHA-256: `029e2a33b52f235746ce79f8e6140f569addefb549fcebf757c786a5171ca6ff`.

Review confirms the setting is now an authoritative master gate: disabled returns no Appi buffering/debug text and closes an existing renderer. Enabled telemetry is four bounded lines in the bundled 1180×180 textbox, with a bounded compatibility fallback. Transition logging contains renderer/mode state but no stream URLs.

Verification remains **partial** because the task explicitly requires target Fire TV acceptance for OFF during refill/recovery/seek/pause-resume, enabled visibility, real UI scale and screen bounds. Mocked/unit renderer checks cannot satisfy that device requirement.
