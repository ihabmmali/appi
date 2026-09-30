---
id: HLS-19
role: implementation
status: review
delivery: released
verification: partial
owner: builder-publisher-0.7.22
base_commit: fd0bd5b08228c34b09de684f7b4b1f865a09e2d2
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.22.zip
---
# HLS-19 — Add resilient in-session recovery for depleted or stalled Buffered Look Ahead playback

## Objective
Make Buffered Look Ahead recover from transient provider stalls even after the playable reservoir drains, instead of converting a temporary delivery delay into a terminal playback timeout.

**Non-regression constraint:** the working 0.7.21 producer/consumer reservoir is the protected baseline. This task adds a recovery layer around it and must not change normal buffering behavior when the provider is healthy.

## Scope
Change only Buffered Look Ahead mode 3. Add bounded Appi-owned recovery, explicit transient/terminal classification, configurable recovery controls, pause-safe session lifetime and recovery telemetry while preserving the healthy 0.7.21 reservoir algorithm and HLS modes 0–2.

## Protected 0.7.21 behavior
With default settings, HLS-19 must preserve:
- startup fill behavior;
- high-water / low-water / critical-water behavior;
- shared video/audio reservoir allocation and track balancing;
- continuous refill scheduling;
- selected rendition/quality behavior;
- progress-aware media transfer behavior;
- fresh-epoch seek/resume ownership;
- cache eviction/admission behavior except where a proven recovery bug requires a narrowly scoped fix.

Recovery logic must remain dormant while the existing reservoir can satisfy playback normally.

## Current 0.7.21 failure boundary
Source inspection shows:
- background prefetch retries failed segments implicitly, currently after a fixed 0.5-second delay;
- when Kodi requests an uncached segment, `_serve_segment()` attempts the target and waits only `RECOVERY_TIMEOUT = 20` seconds for reserve rebuild;
- expiry raises `RecoveryTimeout`;
- the localhost HTTP handler converts that to HTTP 503 (`Buffer refilling; retry request`) and relies on Kodi to retry;
- if Kodi treats the 503 as fatal, playback exits even though Appi's workers may still be capable of recovering;
- other uncaught proxy errors can become fatal session errors / HTTP 502.

This dependency on Kodi's reaction to a transient 503 is too brittle for a feature intended to normalize unstable delivery.

## Required recovery model
Only when the current epoch cannot provide the next required playable media:

1. Enter an explicit recovery state without modifying the normal reservoir policy.
2. Prioritize the exact next required segment(s) for the current video/audio playback point.
3. Retry transient provider failures internally according to configurable recovery controls.
4. Rebuild a minimum playable recovery reserve.
5. Resume the same playback session when the provider recovers within the configured policy.
6. Do not use quality reduction as recovery.
7. Do not reset/rebuild the ordinary reservoir unless required by an already-defined seek/resume epoch transition.
8. Only declare terminal failure after the configured recovery policy is exhausted or a clearly non-retryable error occurs.

Do not use Kodi HTTP 503 retry behavior as the primary recovery mechanism. If the target Kodi HTTP request cannot safely remain open for the entire recovery interval, use a target-device-proven coordination method that preserves the same Appi session.

## Retryable versus terminal conditions
Retry transient conditions such as:
- inactivity/no-progress timeout;
- connection reset / temporary socket failure;
- HTTP 408, 429 and provider 5xx responses;
- temporary incomplete/empty media transfer when retrying the same resource is safe.

Do not blindly retry malformed resource mappings or other deterministic local defects. Authentication/authorization failures must be surfaced deliberately.

## Configurable recovery controls
Consistent with HLS-18 and the project settings rule, expose behavior controls such as:
- overall recovery timeout;
- segment retry delay;
- maximum retry attempts, with an explicit meaning for unlimited-until-overall-timeout if supported;
- retry backoff / maximum retry delay if backoff is used;
- recovery reserve target.

These are recovery-layer controls. They must not implicitly change HLS-13's normal startup/high/low/critical reservoir settings.

## UI and telemetry
During a genuine recovery state, show useful information through the normal buffering UI:
- current playable buffered KB/MB;
- recovery target;
- retry attempt/count where bounded;
- elapsed/remaining recovery window;
- last transient failure category where useful.

HLS-16 may show the same metrics in the optional detailed overlay after its renderer is repaired.

Diagnostics must record recovery entry, retries, successful recovery, exhaustion and final reason without exposing authenticated URLs.

## Acceptance
- Normal playback with a healthy provider behaves the same as 0.7.21.
- Default startup/refill reservoir behavior is unchanged.
- A temporary provider outage long enough to drain the reservoir can recover and continue when delivery resumes within the configured recovery policy.
- Recovery does not require the user to restart playback.
- A transient segment timeout does not immediately poison the session.
- Appi owns retries rather than depending on Kodi retrying a 503.
- Video and required audio recover coherently.
- Selected quality remains unchanged.
- Recovery does not create a new seek epoch unless an actual seek/resume transition occurs.
- Recovery settings are independently configurable.
- Exhausted recovery ends cleanly with a truthful terminal reason.
- Automated tests compare healthy-provider behavior before/after HLS-19 and prove equivalence.
- Fault-injection tests cover temporary no-progress stalls, repeated transient errors, provider recovery, recovery exhaustion and audio/video coherence.
- Target-device acceptance must demonstrate ordinary playback, deliberate/observed recovery, and an extended pause/resume cycle without regression to the working 0.7.21 buffering behavior.

## Authorization
Requested by the user on 2026-09-28 after observing that a sufficiently delayed stream / emptied reservoir can still end in timeout and buffering failure. The user explicitly required that the new resilience **must not impact the currently working 0.7.21 algorithm**. On 2026-09-28 the user explicitly instructed that all current candidates be committed for the next release. HLS-19 is committed next-release scope.

## Evidence
0.7.21 currently has a hard-coded 20-second recovery wait for an uncached playback request and converts recovery expiry into HTTP 503 for Kodi to retry. Background prefetch itself keeps retrying failed media, but Appi does not yet own a robust end-to-end playback recovery window when Kodi reaches an empty reservoir.

## Outcome and next action
Add an isolated recovery controller around the proven 0.7.21 reservoir. Prove non-regression first, then prove that transient depletion can recover within configurable limits.


## Pause/resume lifecycle evidence
Target-device observation on 0.7.21: pausing playback for an extended period can cause the video to exit silently. Starting/resuming the item again works normally.

Source review exposes a plausible lifecycle failure boundary:
- the service passes `player.isPlayingVideo()` into `BufferedHlsManager.poll(player_active=...)`;
- after playback has started, the manager stops the active buffered session when `player_active` is false and no local HLS request has refreshed `last_access` for more than 10 seconds;
- paused playback naturally stops consuming local HLS segments, so `last_access` can stop advancing;
- if the target Kodi/Fire TV build reports a paused player as not actively playing for this check, the manager can tear down the session while the user is merely paused.

This must be verified on-device/logged rather than assumed, but HLS-19 must not allow pause to be mistaken for playback termination.

### Additional HLS-19 requirements
- Explicitly distinguish **playing**, **paused**, **stopped/ended**, **error**, and **buffering/caching** states when deciding whether to retire a session.
- A paused session must remain valid indefinitely subject only to an explicit, user-configurable pause-retention policy; the default must not silently terminate normal long pauses.
- Do not use absence of segment requests by itself as proof playback ended.
- On resume from pause, keep the same session/epoch when playback position has not changed.
- If the provider-side media URLs expire during a very long pause, recover through the normal HLS-19 retry/reload path rather than silently exiting.
- Log the reason for any session retirement so a silent user-visible exit can be traced.
- Add target-device acceptance for a pause substantially longer than 10 seconds followed by successful resume without restarting the item.


## Runtime failure evidence and HLS-21 dependency
The user reports a repeatable 0.7.21 failure sequence: A/V freezes while subtitles keep advancing, playback may briefly resume/catch up, Appi reports a Buffered Look Ahead timeout, then playback stops a few seconds later.

Do not assume this proves the configured buffer is too small. [HLS-21](HLS-21.md) must distinguish true contiguous-reserve exhaustion from a missing next segment, sustained provider deficit, required-track starvation, or recovery timeout while progress is still occurring.

HLS-19 should consume that evidence but remains constrained to add recovery around the working reservoir rather than redesigning normal fill/refill behavior.


## HLS-16 observability dependency
HLS-16 is a practical diagnostic dependency for target-device validation of this recovery work. A working overlay should expose reserve, track starvation, throughput and recovery state while HLS-19 is exercised so recovery failures do not require another blind reproduction cycle.


## 0.7.22 candidate evidence
0.7.22 candidate performs transient depletion retry inside Appi, rebuilds a configurable recovery reserve, returns terminal failure only after policy exhaustion, and removes the old ten-second player-idle retirement path. Automated transient-retry and lifecycle coverage passed; provider-specific stall and long-pause device acceptance remain pending.

Final package gate run `36515744781` passed all 100 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild and ZIP/index inspection. Candidate artifact commit: `971d29d4145411e0c78703326246b770c82d95c3`; ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`.


## 0.7.22 publication
Published in Appi 0.7.22 through PR #11 / merge `92131c95c1d047eb7a683e8e5e2e6abe10e1a518`. Final publication gate run `36626983906` passed 100 tests (1 skipped), workflow tracker validation, deterministic rebuild, ZIP/index inspection and packaging. GitHub Pages deployment run `36627135052` succeeded. Published ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`. Delivery is released; documented target-device acceptance remains review/partial.


## 0.7.22 initial target-device observation
The user reports that buffering **appears better** in 0.7.22, but explicitly notes that more testing is required. Treat this as preliminary positive evidence only, not full target-device acceptance.

Overlay behavior is separately defective and tracked by HLS-23; do not infer buffering/recovery failure from the overlay regression.


## 0.7.22 failed same-stream A/B acceptance
Target-device testing on 2026-09-29 shows the same provider stream that freezes/catches up/stops in Buffered Look Ahead plays perfectly in Manual fixed-quality/InputStream Adaptive mode with no stutter.

This fails HLS-19's intended resilience outcome. Source review identifies a successor correctness defect: 0.7.22 can fetch the exact missing segment successfully but still withhold it from Kodi until the larger recovery reserve is rebuilt. HLS-24 owns that repair.

Do not treat 0.7.22's preliminary "buffering appears better" observation as acceptance; same-stream A/B evidence shows Buffered mode is currently degrading a stream that does not require such intervention.
