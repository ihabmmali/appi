---
id: DOWNLOAD-1
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# DOWNLOAD-1 — Use the tested fast FFmpeg remux command for generated download scripts

## Objective
Change Appi's generated FFmpeg download scripts to use the user's tested fast remux command shape instead of the current invocation that is observed to download near playback rate.

Required core command:

```sh
ffmpeg -i 'REPLACE WITH MEDIA URL' -map 0:v:0 -map 0:a:0 -c copy -threads 0 MediaFileName.mp4
```

Appi must substitute the actual authenticated/pre-authorized media URL and its generated media filename safely.

## Current behavior
`resources/lib/downloads.py` currently generates an invocation equivalent to:

```sh
ffmpeg -hide_banner -nostdin -y \
  -i 'MEDIA URL' \
  -sn -dn -c copy -f mp4 'MediaFileName.part.mp4'
```

and then atomically renames the completed `.part.mp4` file to the final `.mp4` filename.

The current automated test explicitly asserts that no `-map` option is present.

The user reports the current generated command appears to download at approximately playback rate, while the explicit-map command above has been tested on the same use case and downloads dramatically faster.

## Required change
Generate the FFmpeg media operation using the tested semantics:

- `-i <media URL>`
- `-map 0:v:0`
- `-map 0:a:0`
- `-c copy`
- `-threads 0`
- output as MP4 using Appi's generated media filename.

The generated script must select the first video stream and first audio stream explicitly.

Preserve the existing safety/portability behavior unless testing proves it conflicts with the fast path:
- POSIX-safe quoting of the URL and filename;
- execution relative to the script's own folder;
- temporary `.part.mp4` output plus atomic rename on success;
- overwrite/noninteractive behavior needed for unattended execution;
- no subtitle/data-stream download unless separately requested in a future feature.

Do not add `-re`, input-rate throttling, artificial sleeps, or any option that intentionally paces input at playback speed.

If an existing wrapper flag such as `-hide_banner`, `-nostdin`, `-y`, or explicit `-f mp4` is retained, verify that the resulting FFmpeg operation remains functionally equivalent to the user's tested command and does not materially reduce transfer rate.

## Acceptance
- Generated scripts contain `-map 0:v:0 -map 0:a:0 -c copy -threads 0` in the FFmpeg invocation.
- The URL remains shell-quoted safely, including URLs containing apostrophes/query parameters.
- The final generated filename remains Appi's sanitized movie/episode filename.
- Existing atomic partial-file behavior is preserved unless there is measured evidence that it causes the slowdown.
- Existing scripts remain syntactically valid under `sh -n`.
- Automated tests are updated so they require the explicit video/audio mapping instead of asserting that `-map` is absent.
- Movie and TV download-script generation are both covered.
- A same-media/same-URL timing comparison is performed between the old generated command and the new command on an environment where the provider permits faster-than-real-time transfer.
- The new command is not intentionally playback-rate limited and should reproduce the user's observed faster-than-real-time behavior where upstream throughput permits.
- No media transcoding is introduced; `-c copy` remains mandatory.

## Authorization
Requested and explicitly committed by the user on 2026-09-28. The user supplied the tested command shape and reported that it downloads dramatically faster than Appi's current generated FFmpeg script. DOWNLOAD-1 is committed next-release scope.

## Evidence
Current `plugin.video.appi/resources/lib/downloads.py` emits `-sn -dn -c copy -f mp4` with no explicit `-map` or `-threads 0`. Current `tests/test_downloads.py` explicitly asserts `'-map ' not in script`, confirming the generated command does not currently follow the requested form.

## Outcome and next action
Update only the generated FFmpeg command and its tests, then verify both command structure and real transfer behavior. Do not change unrelated download naming, VFS script generation, or playback/buffering code.
