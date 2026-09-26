---
id: SUB-1
role: review
status: ready
delivery: released
verification: failed
owner: unassigned
base_commit: unset
artifact: https://github.com/ihabmmali/appi/blob/main/plugin.video.appi-0.7.12.zip
---
# SUB-1 — Restore downloaded subtitle persistence across playback sessions

## Objective
Investigate and fix a regression where an externally downloaded subtitle that was selected during playback is not remembered and automatically restored when the same movie or episode is stopped and later resumed or restarted.

Appi already contains a persistence design: subtitle files detected in Kodi temporary storage are copied into Appi profile storage and indexed by media identity, then the last saved subtitle is reapplied on a later playback session when subtitle persistence/auto-restore is enabled. The reported behavior indicates that this intended flow is not working reliably in the latest releases.

## Scope
Review the complete saved-subtitle lifecycle for movies and TV episodes:
- creation of the subtitle playback session before media starts;
- detection/capture of subtitle files downloaded by Kodi subtitle add-ons;
- stable mapping of saved files to the same Appi media item;
- session finalization when playback is stopped, ended or errors;
- lookup and reattachment of the previously saved subtitle when the same item is resumed or restarted.

Determine whether failure is in capture, indexing, media-key stability, session cleanup/timing, file existence/path handling, or reattachment through Kodi player/list-item APIs.

Preserve existing user controls such as subtitle persistence, automatic saved-subtitle loading, explicit per-title subtitle modes, and Clear Saved Subtitles. Do not silently change unrelated subtitle-search/provider behavior.

## Acceptance
- On the current baseline, reproduce the reported sequence: play a movie, download/select an external subtitle, exit playback, then resume the same movie.
- Repeat with "Play from beginning"/restart of the same movie where available.
- Repeat the equivalent flow for a TV episode.
- Confirm the downloaded subtitle is actually copied/indexed into Appi-owned persistent storage before or at playback termination.
- On the next playback of the same media identity, automatically restore and enable the last saved subtitle when persistence/auto-load settings permit it.
- Confirm resume versus restart does not change the media key used for subtitle lookup.
- Confirm stopping playback shortly after downloading a subtitle does not lose the subtitle because the polling/copy step has not yet run.
- Confirm a newly downloaded replacement subtitle becomes the new last-saved choice for that media item.
- Confirm subtitles saved for one movie/episode are never attached to a different item.
- Confirm disabling automatic saved-subtitle loading prevents automatic reattachment without deleting the persisted subtitle.
- Confirm Clear Saved Subtitles removes the stored files/index and subsequent playback does not restore them.
- Record Kodi version, platform, subtitle add-on/provider used for reproduction, Appi version, and whether the failure was capture-side or restore-side.
- Add regression coverage for the identified failure path where practical, plus a target-device check.

## Authorization
Reported by the user on 2026-09-26 as a regression in recent Appi releases: after downloading a subtitle, exiting a movie and then resuming or restarting it appears to forget the downloaded subtitle. This triage thread is authorized to record and plan the repair; implementation, integration and publication remain separate assignments.

## Evidence
Current source contains the intended persistence path:
- `subtitle_store.prepare_session()` snapshots Kodi temp subtitle files and returns saved subtitles for the media key.
- `capture_temp_changes()` copies newly downloaded subtitle files into Appi profile storage and updates an index/last-saved pointer.
- `subtitle_service.AppiPlayer` polls for downloaded subtitle changes during playback and attempts to reapply `last_saved_subtitle()` on `onAVStarted`.
- `play_ref()` prepares the subtitle session and can attach previously saved subtitles before playback.

User device observation on 2026-09-26 indicates this end-to-end behavior is currently failing across stop/resume or restart. No root cause has yet been established.

## Outcome and next action
Treat SUB-1 as a current-baseline regression. A review worker should reproduce the exact stop/resume/restart flows first, identify whether persistence fails during capture or restoration, then move the same task into implementation for the scoped repair.
