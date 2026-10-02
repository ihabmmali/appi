---
id: HLS-27
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-27 — Repair video-only pause/resume resynchronization

## Objective
Fix the remaining Appi 0.7.24 Buffered Look Ahead pause/resume defect where the session now survives pause without the old fatal TimeoutError, but video can freeze after resume while audio continues normally.

This is a release-blocking correctness candidate. Do not solve it by increasing buffer size, recovery timeout, localhost socket timeout, or by changing the selected rendition.

## 0.7.24 target-device evidence
The user reports a clear improvement over 0.7.23:
- Buffered Look Ahead playback is generally more stable.
- No silent playback crashes have been observed so far.
- Short and long pauses no longer produce the previous timeout error.

However pause/resume still fails continuity:
- after resuming, video often freezes while audio continues smoothly;
- the video commonly recovers after one or two individual freezes and may visibly catch up;
- playback then often becomes normal again;
- on a smaller number of attempts, the frozen video never recovers even though audio remains active.

This is a different failure mode from the 0.7.23 fatal localhost-consumer timeout.

## Source-level primary hypothesis — resume request misclassified as a true seek
0.7.24 adds request classification in `_Track._classify_request()`.

For a track marked `resume_pending`:
- exactly the expected next segment remains sequential;
- exactly `expected + 1` is accepted as an adjacent resume;
- any request beyond that is classified as `forward-discontinuity` and creates a fresh HLS-12 seek epoch.

Kodi can legitimately resume video on a later HLS/keyframe boundary than audio after a pause without the user having performed a seek.

If video resumes two or more segments beyond Appi's expected index, 0.7.24 can therefore promote a normal pause/resume request into a real seek. `_coordinate_seek()` then:
- increments the shared epoch;
- recenters every required track around the video's target timeline;
- marks the new epoch as preparing;
- invalidates/ignores stale in-flight work.

That can plausibly explain a video freeze/catch-up cycle while audio has already resumed, but this is a hypothesis that must be proven with target-device telemetry before changing the classification policy.

## Secondary hypothesis — video consumer response continuity
HLS-25 correctly makes Kodi-side write timeout/disconnect non-fatal, but a paused video response can still be abandoned while the audio path resumes independently.

Verify whether:
- the first post-pause video request is delayed relative to audio;
- Kodi re-requests the same/recent video segment or jumps to a later video segment;
- Appi serves that requested video segment promptly from cache;
- the video request is classified without a new epoch;
- Kodi nevertheless waits for a later independently decodable video boundary before rendering again.

If Appi delivers the correct video bytes promptly in the same epoch but rendering remains frozen, distinguish a Kodi/decoder keyframe-resynchronization issue from an Appi scheduling/classification issue rather than guessing.

## Required pause/resume model
A pause with no user position change must not be treated as a seek merely because audio and video restart with different segment request patterns.

Implement a target-device-proven resume classification based on actual playback continuity rather than a one-segment index heuristic.

At minimum:
- record player position at pause start and resume;
- distinguish unchanged-position resume from an actual user seek while paused;
- allow normal per-track post-pause request variation without creating a fresh epoch when the playback timeline has not meaningfully moved;
- keep video and required audio in the same authoritative playback epoch;
- do not force audio to recenter merely because video resumes at a later decodable HLS boundary;
- retain true forward/backward seek and cold non-zero resume behavior.

Do **not** simply widen `expected + 1` to an arbitrary fixed number of segments without position/timeline evidence, because that could hide genuine seeks.

## Diagnostics
For every pause/resume cycle, persist enough evidence to reconstruct the first several requests on each required track:

- pause start monotonic time and Kodi playback position;
- resume monotonic time and Kodi playback position;
- pause duration;
- epoch before/after resume;
- per-track first 5-10 post-resume requests:
  - track ID/type;
  - requested index and media sequence;
  - segment timeline start/end;
  - previous last-requested and last-served;
  - request classification;
  - range/re-read status;
  - cached/fetching/absent state;
  - first-byte-served timestamp;
- whether `_coordinate_seek()` was invoked, and which track triggered it;
- exact reason and target timeline if a new epoch was created;
- contiguous video reserve and audio reserve separately;
- total cached bytes;
- player state;
- video/audio request timing skew;
- whether the cycle recovered automatically or remained video-frozen.

Where practical, include Kodi's current playback time during the freeze so a catch-up event can be correlated with segment delivery.

## Preservation constraints
Do not change:
- HLS-13 reservoir startup/high/low/critical policy;
- HLS-22 producer-concurrency defaults merely to address pause;
- HLS-24 exact-segment release behavior;
- HLS-25 non-fatal handling of Kodi-side timeout/disconnect;
- selected quality/rendition;
- HLS modes 0-2.

Do not reintroduce the 0.7.23 fatal TimeoutError behavior.

## Acceptance
Target Fire TV acceptance is mandatory.

- Pause for 5-10 seconds and resume with continuous video and audio.
- Pause for more than 30 seconds and resume with continuous video and audio.
- Pause for several minutes while browsing/selecting subtitles and resume with continuous video and audio.
- Repeat each scenario multiple times; one or two video freezes after resume are not acceptable.
- Video must not remain permanently frozen while audio continues.
- A no-position-change pause/resume must remain in the existing epoch.
- Normal post-pause video requests that move to an appropriate nearby decodable boundary must not be promoted to a seek solely because the index gap is greater than one.
- A real user forward/backward seek, including a seek performed while paused, must still create the appropriate fresh epoch and resume correctly.
- Audio/video remain timeline-coherent after resume.
- No fatal localhost-consumer TimeoutError or silent session teardown.
- Existing healthy sequential playback behavior is unchanged.
- Automated tests cover:
  - video resumes sequentially while audio does likewise;
  - video resumes more than one segment ahead with unchanged player position;
  - audio resumes before video;
  - video response is cancelled during pause then re-requested;
  - true seek while paused;
  - repeated pause/resume cycles.

## Authorization
Created from Appi 0.7.24 Fire TV target-device testing reported by the user on 2026-10-01. HLS-27 is logged as a ready release-blocking candidate and is not committed to release scope until explicitly selected under AGENTS.md.

## Evidence
0.7.24 source marks all tracks `resume_pending=True` when leaving the paused state, but only treats exactly `expected + 1` as a non-seek adjacent resume. A larger forward request becomes a true discontinuity and invokes the shared `_coordinate_seek()` path, which recenters all tracks.

The user's audio-continuous/video-frozen observation makes per-track resume behavior and cross-track epoch coordination the primary evidence target rather than global reservoir capacity.

## Outcome and next action
Instrument the first post-pause audio/video request sequence and actual Kodi playback position, prove whether video is being falsely promoted to a seek or whether correct cached video delivery is failing decoder resynchronization, then repair only the proven boundary.
