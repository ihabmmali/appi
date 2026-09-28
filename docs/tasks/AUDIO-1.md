---
id: AUDIO-1
role: implementation
status: review
delivery: released
verification: partial
owner: builder-publisher-2026-09-27
base_commit: 24ac0358640864a0129d97b638ca37c616f6612b
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.20.zip
---
# AUDIO-1 — Restore audio for InputStream Adaptive playback

## Objective
Restore working audio whenever Appi uses InputStream Adaptive.

On published Appi 0.7.19, the user reports that audio is broken for InputStream Adaptive playback in both manual quality selection and other ISA-based playback modes. Reverting to Appi 0.7.8 restores audio on the same target device/media.

This is a release-blocking playback regression candidate.

## Observed target-device behavior
- Appi 0.7.19: video can play through InputStream Adaptive but playback is completely silent.
- Kodi's playback UI still exposes the audio-stream details/tracks during the silent playback, so audio-track discovery is occurring at least at the UI level.
- The problem occurs with manual InputStream quality selection and with other InputStream Adaptive playback use.
- Reverting to Appi 0.7.8 restores audible playback on the same target device/media.
- The user has reverted to 0.7.8 as the practical fallback until the next release.
- The report is distinct from Buffered Look Ahead seek/recovery failures.

## Regression boundary
Source comparison shows that Appi 0.7.8 and 0.7.19 use the same basic InputStream Adaptive handoff architecture for the established ISA modes:
- original HLS URL remains the ListItem path;
- `inputstream=inputstream.adaptive`;
- manual mode uses `stream_selection_type=ask-quality`;
- adaptive mode uses `stream_selection_type=adaptive`.

A major behavioral difference is that 0.7.19's persistent player service now implements preferred-audio selection after AV start by calling Kodi's `getAvailableAudioStreams()` and `setAudioStream()`. That logic did not exist in 0.7.8.

This makes the preferred-language/player-service path a primary A/B regression boundary to test, but it is not yet proven to be the cause. The fact that Kodi still lists audio streams while playback is silent further suggests the failure may occur after discovery, during selection/indexing/timing or decoder/ISA handoff.

## Scope
Diagnose and repair audio loss in InputStream Adaptive playback without changing working Native Kodi playback or hiding the problem by switching engines.

At minimum:
- reproduce with manual ISA and adaptive ISA modes;
- reproduce with preferred audio language set to **No preference** and to an explicit language;
- A/B test the current post-AV preferred-audio selection logic enabled versus bypassed;
- capture `getAvailableAudioStreams()` output, current selected audio index where Kodi exposes it, and the index passed to `setAudioStream()`;
- capture the audio stream details Kodi displays during the silent state;
- determine whether ISA audio tracks are separate renditions/groups and whether Kodi's stream indices are stable when Appi applies the preference;
- verify whether `onAVStarted` / `onAVChange` timing causes Appi to switch audio before ISA has finalized its stream list or decoder;
- compare the actual 0.7.19 ListItem/InputStream properties against known-working 0.7.8 before changing those properties;
- verify that making InputStream Adaptive a required dependency in HLS-9 is not conflated with runtime audio-track behavior;
- capture Kodi/InputStream Adaptive logs around stream enumeration, audio selection and decoder initialization.

Do not remove the preferred-language feature as a permanent workaround unless evidence establishes that Kodi/ISA cannot safely support it. If the language feature is causal, repair its timing/indexing/guard logic so ISA audio remains functional.

## Acceptance
- The same media that has audio in Appi 0.7.8 also has audio in the repaired current build.
- Manual InputStream Adaptive quality selection plays video **and audible audio**.
- Automatic/adaptive InputStream Adaptive playback plays video **and audible audio**.
- Kodi's displayed audio stream list corresponds to a actually audible selected stream rather than a silent/stale selection.
- **No preference** performs no Appi audio-track switch and leaves Kodi/ISA's default audio intact.
- An explicit preferred language switches only after a valid matching audio stream is available and never results in silent playback.
- If no matching language exists, Appi leaves the current working audio stream untouched.
- Appi never calls `setAudioStream()` with an invalid/stale index.
- Delayed ISA stream enumeration is handled without muting or losing audio.
- Native Kodi playback remains unchanged.
- Buffered Look Ahead is regression-tested separately; AUDIO-1 must not use buffered behavior as proof that ISA is repaired.
- Automated tests cover No preference, matching preference, no match, delayed stream enumeration, changing stream lists, manual ISA and adaptive ISA.
- Target-device verification repeats the same item on 0.7.8 and the repaired build and records available audio streams, displayed stream details, selected index, playback mode and audible result.

## Authorization
Reported by the user on 2026-09-27 while testing published Appi 0.7.19. The user confirmed the same media regains audio after reverting to Appi 0.7.8. On 2026-09-27 the user explicitly instructed that all current candidates be committed. AUDIO-1 is therefore committed release scope and a release blocker.

## Evidence
Implementation/research session opened on branch `release/0.7.20` from base `24ac0358640864a0129d97b638ca37c616f6612b`; user authorization includes implementation, integration and publication of the committed next-release scope.

Known-working Appi 0.7.8 source commit: `d66db9724417bd44d6ece91ea01a903ced29b9d8`.

In 0.7.8, `_configure_hls()` already used InputStream Adaptive for manual/adaptive modes, but the service did not contain `getAvailableAudioStreams()`, `setAudioStream()`, or preferred-audio retry logic.

In 0.7.19, `subtitle_service.AppiPlayer` starts preferred-language handling on `onAVStarted()`, polls pending language selection, and may call `setAudioStream(index)` once streams appear.

The unchanged core ISA handoff plus the newly introduced service-side audio selection makes that feature boundary especially important to test first. Kodi's ability to display audio stream details while output remains silent is additional evidence that discovery alone is not the missing step.

Candidate implementation `4c5363e3220dc16507b308e6ccfa8bbec4eb6d40` leaves the established native/manual/adaptive HLS ListItem configuration unchanged and changes only post-AV preferred-audio behavior. No preference is inert. Explicit selection waits for an unchanged non-empty stream list across a service poll boundary, re-enumerates immediately before using an index, leaves a stable no-match untouched, and queries Kodi's current audio stream through JSON-RPC when available so an already-selected preferred stream receives no redundant `setAudioStream()` call. Release/package run `36375784976` passed the full 87-test suite (1 intentional skip), tracker validation, deterministic rebuild and package inspection. Target-device audible-output acceptance remains pending.

Published through PR #8 / merge `6e6db9bec185ec6b5eea664d27cb7b94f4efa2ef`. Post-merge verification run `36376270017` passed and Pages deployment run `36376269821` completed successfully. Delivery is `https://ihabmmali.github.io/appi/plugin.video.appi-0.7.20.zip`; the verified generated ZIP SHA-256 is `41e1bdec7229d1a0a3d8787427ac9c434fb773e302c7d8f5bae428de0de7755f`. Publication does not establish target-device acceptance.

## Outcome and next action
0.7.20 is published. Keep this task in review/partial verification until the documented target-device checks are completed; do not treat publication as acceptance.
