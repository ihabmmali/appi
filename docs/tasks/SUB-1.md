---
id: SUB-1
role: implementation
status: review
delivery: released
verification: partial
owner: builder-publisher-2026-10-10
base_commit: 8a9b1ad21b3944d8045e1d1abff2a2556c3035cc
artifact: https://ihabmmali.github.io/appi/plugin.video.appi-0.7.25.zip
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

## Build session — 2026-09-26
- User authorization: all candidates committed to the next release; implementation, integration and publication explicitly authorized.
- Release branch: `release/0.7.13`; base: `8a9b1ad21b3944d8045e1d1abff2a2556c3035cc`.
- Planned paths: plugin.video.appi/resources/lib/subtitle_store.py; subtitle service/tests.
- This worker owns the committed release sequence; review will be recorded as self-review unless independent evidence is added.

## Review evidence — 2026-09-26
- Root cause repaired: the ordinary poller still waits for a stable subtitle-file fingerprint, while playback stop now performs a final capture pass before clearing the subtitle session.
- Regression coverage includes the immediate-stop case where a subtitle has only been observed once before stop, plus restore/language interaction in the service smoke test.
- Automated suite passed in Actions run 36277010649. Verification remains partial pending movie and episode stop/resume/restart checks on the target device.

## Outcome and next action
Treat SUB-1 as a current-baseline regression. A review worker should reproduce the exact stop/resume/restart flows first, identify whether persistence fails during capture or restoration, then move the same task into implementation for the scoped repair.

## Publication — 0.7.13
- Published to `main` in merge commit `0d708565e4bccb0abe03c7a0ae004ccb3dc0a72a` on 2026-09-26/27.
- Post-merge release verification: GitHub Actions run 36287058096 passed the full automated gate.
- Artifact: `plugin.video.appi-0.7.13.zip`; 0.7.8 remains the known-good fallback.
- Delivery is released; verification remains partial until the task's documented target-device checks are completed.


## 0.7.24 intermittent movie recurrence
On 2026-10-04 the user reports that externally downloaded subtitles for movie media still occasionally disappear/not restore. There is no reliable reproduction pattern yet; it occurs intermittently.

This confirms SUB-1 remains an active current-baseline defect despite the earlier immediate-stop fix. The canonical task is reopened for implementation rather than creating a duplicate subtitle-persistence task.

### Current evidence boundary
The current persistence path only detects files visible through `_snapshot_temp()`, which:
- scans Kodi's translated temp directory;
- recognizes a fixed set of subtitle extensions;
- intentionally stops recursion below roughly two directory levels.

A provider/add-on that writes outside that scanned area, uses a deeper temporary path, replaces a file in a way not observed by the poller, or removes/moves the file before the final capture can therefore evade persistence. These are hypotheses only.

### Additional diagnostics required
For every downloaded/selected external subtitle during an Appi movie session, record:
- media key/canonical movie ref;
- current selected subtitle path if Kodi exposes it;
- temp paths/fingerprints observed by the poller;
- whether the file was first observed, stabilized, copied, indexed and restored;
- copy/index failure reason;
- final-capture invocation and result;
- whether the source file disappeared before capture;
- saved destination and whether it still exists at next playback;
- restore attempt path and Kodi `setSubtitles()` result.

Do not log subtitle contents.

### Additional acceptance
- Repeat movie download -> select -> stop/resume cycles enough times to cover the intermittent case, including different subtitle providers where available.
- A subtitle that Kodi has successfully selected must not be lost merely because its provider uses a different temporary-directory layout or cleanup timing.
- If Kodi exposes the selected subtitle path directly, prefer using that authoritative path or a similarly reliable player API over relying solely on shallow temp-directory discovery.
- Preserve TV-episode persistence and Clear Saved Subtitles behavior.


## 2026-10-10 release-scope recommit
The user explicitly instructed that all current candidates be committed for the next release. The reopened current-baseline subtitle persistence regression is therefore committed next-release scope under SUB-1.

This recommit authorizes release scope selection only. Implementation, integration, build and publication remain separate lifecycle actions under AGENTS.md.

## 0.7.25 recurrence repair — implementation and self-review (device checks pending)

Owner: builder-publisher-2026-10-10. Base: `a6f22d924cd490c387ec6a3a201eab9cb349e52a`; branch: `release/0.7.25`.

Capture scans a bounded deeper Kodi temp hierarchy plus a configured local custom subtitle-storage folder using the documented `subtitles.storagemode` and `subtitles.custompath` settings. Capture on `onAVChange` uses a final-pass copy before a provider can remove a transient source; ordinary polls retain the stable-fingerprint gate. Saved file copies now use an atomic temporary path and index recording. File-name-free media-key/capture/restore diagnostics distinguish detection, copy, index and restore boundaries; final capture exceptions are no longer silently swallowed. Regression coverage tests nested temp/custom folders, final capture, separate movie identities and clearing. Existing episode and provider behavior should be retested on target Fire TV, especially any provider storing files outside discoverable local folders. Kodi `Player.getSubtitles()` does not expose a selected filesystem path; do not claim support for arbitrary external locations. Self-review only; verification is partial pending device tests.


## 0.7.25 publication and pending verification

Published in PR #16 merge `9de26765b4af163974162ebb76f43e14a1001a5c` on 2026-10-10. Exact candidate gate [38063374015](https://github.com/ihabmmali/appi/actions/runs/38063374015) passed 112 automated tests (1 skipped), workflow checker, deterministic build and ZIP/hash/index inspection; package checksum `a46637a96b15ae01e75df3a59b0558d993f54c2f4c43506406a91036ba77d1c0`. GitHub Pages build/deploy [38063465450](https://github.com/ihabmmali/appi/actions/runs/38063465450) completed successfully. Delivery: **released**. Verification: **partial**; documented Kodi Fire TV target-device acceptance remains outstanding and is not inferred from CI.
