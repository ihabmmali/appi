---
id: DOWNLOAD-1
role: implementation
status: review
delivery: unreleased
verification: partial
owner: builder-publisher-0.7.22
base_commit: fd0bd5b08228c34b09de684f7b4b1f865a09e2d2
artifact: 971d29d4145411e0c78703326246b770c82d95c3
---
# DOWNLOAD-1 — Use the tested fast FFmpeg remux command for generated download scripts

## Objective
Change Appi's generated FFmpeg download scripts to use the user's tested fast remux command shape instead of the current invocation that is observed to download near playback rate.

Required core command:

```sh
ffmpeg -i 'REPLACE WITH MEDIA URL' -map 0:v:0 -map 0:a:0 -c copy -threads 0 MediaFileName.mp4
```

Appi must substitute the actual authenticated/pre-authorized media URL and its generated media filename safely.

## Scope
Change only generated FFmpeg download-script invocation semantics and its tests. Preserve existing VFS writing, filename sanitization, shell quoting, temporary partial-file output and atomic rename. Do not change playback paths.

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


## 0.7.22 candidate evidence
0.7.22 candidate generates FFmpeg scripts with explicit first-video/first-audio mapping, stream copy and -threads 0 while preserving quoting, partial output and atomic rename. Automated script-generation coverage passed; same-provider real transfer-rate comparison remains a target/environment check.

Final package gate run `36515744781` passed all 100 unit/smoke tests (1 skipped), workflow tracker validation, deterministic rebuild and ZIP/index inspection. Candidate artifact commit: `971d29d4145411e0c78703326246b770c82d95c3`; ZIP SHA-256: `35a50dad9f17f0d0a47c2cea7892d769a1b613ab2743bbbd61a1fc59267ae53f`.
