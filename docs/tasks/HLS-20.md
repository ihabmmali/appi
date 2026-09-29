---
id: HLS-20
role: implementation
status: review
delivery: released
verification: partial
owner: builder-publisher-0.7.22
base_commit: fd0bd5b08228c34b09de684f7b4b1f865a09e2d2
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.22.zip
---
# HLS-20 — Diagnose and reduce post-fill startup handoff delay

## Objective
Remove avoidable delay between Buffered Look Ahead reaching its configured startup reservoir target and actual audio/video playback beginning, without changing the working 0.7.21 reservoir algorithm.

This is an investigation-first implementation task: measure the handoff timeline, identify which stage consumes the delay on the target device, then fix only the responsible Appi-controlled stage(s).

## Scope
Instrument and optimize only the Buffered Look Ahead handoff after the configured startup reservoir is ready. Measure each Appi/Kodi boundary, preload required key/map resources, and remove no delay unless evidence shows it is Appi-owned. Preserve the startup reservoir policy and modes 0–2.

## Current 0.7.21 handoff
Source inspection shows there is no intentional sleep after startup fill completes.

When the reservoir reaches `startup_target_bytes`:
1. `BufferedHlsSession.prepare()` marks the session ready immediately.
2. The plugin-side `request_playback()` polls the service response at roughly 100 ms intervals and returns the localhost HLS URL when `ready` is observed.
3. `play_ref()` assigns that URL to the Kodi `ListItem`.
4. Appi performs remaining local playback-session/subtitle bookkeeping.
5. `xbmcplugin.setResolvedUrl(..., True, list_item)` hands the localhost HLS stream to Kodi.
6. Kodi opens the local master/media playlists and starts demux/decoder/AV playback.

The master and prepared media playlists are normally cached by Appi, but URI dependencies such as `#EXT-X-KEY` encryption keys and `#EXT-X-MAP` initialization resources are registered as proxy resources and may still be fetched on demand when Kodi opens the stream. Those are plausible Appi-side contributors to the handoff gap, but they are not yet proven to be the cause.

Kodi demux/decoder startup may also account for part of the delay. The task must measure rather than assume.

## Required instrumentation
Record monotonic timestamps for at least:
- startup reservoir target reached / session marked ready;
- plugin observes ready response;
- buffered URL returned to `play_ref()`;
- immediately before `setResolvedUrl()`;
- localhost master playlist first request;
- selected media playlist first request;
- first key/map/init resource request where present;
- first media segment request;
- first media bytes served;
- Kodi `onAVStarted` callback.

Derive per-stage elapsed times so target-device diagnostics can say where the post-fill delay occurs.

Instrumentation must not depend on the optional detailed overlay being functional.

## Repair rules
- Preserve HLS-13's working reservoir fill/refill algorithm and defaults.
- Do not reduce startup fill percentage merely to make playback appear faster.
- If key/map/init resources cause the delay, preload the resources required for the first playable window before declaring startup ready.
- If Appi local bookkeeping materially delays `setResolvedUrl()`, move or defer only work proven safe to move.
- If playlist re-open/refresh causes delay, serve the already prepared cached playlist immediately when valid.
- If the dominant remaining delay is inside Kodi after `setResolvedUrl()`, retain the evidence and do not destabilize Appi's reservoir trying to compensate for a Kodi decoder-start cost.
- Keep modes 0-2 unchanged.

## UI
The normal startup UI should distinguish:
- `Filling buffer — ...`
- `Buffer ready — starting Kodi playback...`

If handoff takes more than a brief interval, the second state should remain visible or otherwise be diagnosable rather than appearing as an unexplained blank wait.

HLS-16 may additionally expose handoff timing in its detailed overlay after playback starts, but HLS-20 must remain diagnosable without that overlay.

## Acceptance
- Default 0.7.21 startup reservoir behavior is unchanged.
- The target-device timeline identifies the dominant interval between reservoir-ready and `onAVStarted`.
- No Appi-controlled network dependency required for first frame is unnecessarily deferred until after reservoir-ready.
- Avoidable Appi-side handoff delay is removed or materially reduced.
- Startup never begins with less playable reserve solely to improve perceived latency.
- Encrypted/fMP4 HLS with key/init-map dependencies is covered where available.
- Ordinary TS HLS is covered separately so key/map hypotheses are not generalized incorrectly.
- Automated tests verify ready-to-handoff ordering and any preloaded startup dependencies.
- Target-device verification records reservoir-ready -> `setResolvedUrl` -> first local request -> `onAVStarted` timings before and after the repair.

## Authorization
Created from the user's repeated target-device observation that there is a noticeable delay after initial buffer filling completes and before playback actually starts. On 2026-09-28 the user asked whether the cause had already been identified and whether a fix was being tracked. Source review shows the gap was not yet isolated as a dedicated task. On 2026-09-28 the user explicitly instructed that all current candidates be committed for the next release. HLS-20 is committed next-release scope.

## Evidence
0.7.21 has no deliberate post-fill sleep. `request_playback()` polls readiness every 0.1 seconds, and `prepare()` sets `ready=True` immediately after the startup reservoir is satisfied. The plugin then eventually calls `setResolvedUrl()`. Master/media playlists are cacheable in the local proxy, while key/map resources can remain on-demand. The exact target-device timing boundary is therefore unresolved.

## Outcome and next action
Instrument the entire reservoir-ready-to-AV-start handoff, then repair only the proven Appi-side source of delay while preserving the working 0.7.21 buffering algorithm.


## 0.7.22 candidate evidence
0.7.22 candidate records monotonic handoff stages from reservoir-ready through plugin return/setResolvedUrl, first local playlist/key/map/segment/bytes and AV start, and preloads known key/map dependencies. Automated tests passed; target-device latency evidence remains pending.

Final package gate run `36515744781` passed all 100 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild and ZIP/index inspection. Candidate artifact commit: `971d29d4145411e0c78703326246b770c82d95c3`; ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`.


## 0.7.22 publication
Published in Appi 0.7.22 through PR #11 / merge `92131c95c1d047eb7a683e8e5e2e6abe10e1a518`. Final publication gate run `36626983906` passed 100 tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/index inspection and packaging. GitHub Pages deployment run `36627135052` succeeded. Published ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`. Delivery is released; documented target-device acceptance remains review/partial.
