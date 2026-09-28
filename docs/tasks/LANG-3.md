---
id: LANG-3
role: implementation
status: review
delivery: released
verification: failed
owner: GPT-5.6 Sol release/0.7.19
base_commit: c7a344ae2afa1160adb7daf522092c89b46105bf
artifact: plugin.video.appi/plugin.video.appi-0.7.19.zip
---
# LANG-3 — Preferred language setting is not applied at playback

## Objective
Repair preferred audio/subtitle language behavior after target-device testing of 0.7.18 showed that choosing a default language from the new lists does not appear to affect playback.

## Scope
Trace the complete path from LANG-2's visible list values into LANG-1's runtime audio/subtitle selection.

Investigate:
- canonical value stored by the list control;
- normalization of the new non-empty `none` sentinel and actual language codes;
- whether playback reads the visible setting or stale/legacy hidden values;
- timing of Kodi audio/subtitle stream enumeration;
- actual target-device track labels/codes;
- precedence of per-title subtitle modes and saved external subtitles;
- independent audio versus subtitle behavior;
- behavior across Native Kodi, manual ISA, ABR and Buffered Look Ahead where applicable.

Do not reintroduce free-text settings or unsafe empty list values.

## Acceptance
- Selecting a preferred audio language selects the matching audio track when one exists.
- Selecting a preferred subtitle language selects the matching internal subtitle track when applicable and not superseded by an explicit per-title choice.
- **No preference** leaves Kodi/default behavior unchanged.
- Aliases such as English / eng / en map consistently.
- Runtime reads the current visible list setting rather than stale migration data.
- Audio and subtitle preferences are independently verified.
- No matching track results in graceful fallback, not an unrelated selection.
- Saved external subtitle/manual override precedence remains intact.
- Automated tests cover visible list value -> normalization -> Kodi track selection end to end.
- Target-device verification records selected preference, available track codes/labels and actual chosen track.

## Authorization
Reported by the user on 2026-09-27 while testing 0.7.18. On 2026-09-27 the user explicitly committed this repair for the next release and identified preferred-language selection as the other primary release focus. LANG-3 is committed release scope.

## Evidence

2026-09-27 implementation session: assigned to GPT-5.6 Sol on `release/0.7.19` from base `c7a344ae2afa1160adb7daf522092c89b46105bf`. User authorization covers implementation, integration and publication of the committed next-release scope. Source/test changes are isolated on the release branch; HLS-8 preserves playback modes 0–2.

Automated release/package run 36370407423 passed. New runtime coverage verifies that visible canonical language choices remain pending when Kodi initially exposes no streams, then select the matching audio/subtitle index once streams appear; explicit No preference stays inert, and a restored external subtitle prevents a later internal-subtitle retry from overriding it.
0.7.18 fixes the 0.7.17 native settings-parser crash and Kodi now remains running, but the selected default language appears to have no effect during playback.

## Outcome and next action
Published in 0.7.19, but target-device verification is failed because ISA audio is now broken/absent. AUDIO-1 must first restore reliable audio, then LANG-3 must be re-verified for actual preferred-language selection without muting playback.


## 0.7.19 InputStream audio regression evidence
Target-device testing now shows a more serious problem than the original "preference does not apply" report: InputStream Adaptive playback has broken/absent audio in 0.7.19, both with manual quality selection and other ISA use. Reverting to 0.7.8 restores audio.

This does not prove LANG-3 caused the regression, but 0.7.19's preferred-audio retry/selection logic is absent from 0.7.8 and must be A/B tested before modifying the proven InputStream configuration. [AUDIO-1](AUDIO-1.md) owns the audio-loss regression. LANG-3 target-device verification is failed until audio remains functional while language preference behavior is verified.
