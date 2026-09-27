---
id: LANG-2
role: implementation
status: review
delivery: released
verification: partial
owner: Codex release/0.7.18
base_commit: a0b9eacb23b4816df7ac4c0f60e9c51fb7d1eb79
artifact: plugin.video.appi/plugin.video.appi-0.7.17.zip
---
# LANG-2 — Common-language selection lists for audio and subtitles

## Objective
Replace the free-text preferred audio-language and preferred subtitle-language settings with selectable lists of common languages.

The user should not have to type values such as `eng`, `en` or `English`. Appi should present human-readable language names and store/use stable normalized values that continue to work with the alias-normalization logic introduced by [LANG-1](LANG-1.md).

## Scope
Update both settings:
- Preferred audio language
- Preferred subtitle language

Each setting should use a Kodi list/select control populated with common languages rather than a free-text edit box.

The displayed values should be human-readable language names. The stored/internal values should use a stable canonical code or identifier compatible with the existing normalization/matching layer, while continuing to recognize provider/Kodi aliases such as language names, ISO-639-1 codes and ISO-639-2 codes where applicable.

Include a neutral option such as **None / No preference** so the user can disable automatic language preference without clearing arbitrary text.

The two settings remain independent. This task changes only the settings UX/data-entry method; it must not regress the underlying audio/subtitle matching behavior already delivered in LANG-1.

## Acceptance
- Preferred audio language is presented as a selectable list, not a free-text input.
- Preferred subtitle language is presented as a selectable list, not a free-text input.
- Both lists contain a practical set of common languages with human-readable names.
- Both lists include a **None / No preference** option.
- Selecting a language stores a stable canonical value that the existing language-normalization logic can reliably match against provider/Kodi labels and codes.
- Existing aliases such as English / eng / en continue to match the selected English preference.
- Audio and subtitle preferences remain independently configurable.
- Existing saved settings from older versions are migrated or interpreted safely so an upgrade does not break playback settings.
- Unknown/legacy free-text values fail safely and do not crash settings or playback.
- The change does not affect per-title subtitle mode behavior, saved external subtitle handling, or manual track overrides.
- Settings labels/help text explain that Appi will match common aliases/codes automatically.
- Automated/smoke coverage verifies at least several representative language choices plus None/No preference and legacy-value handling.

## Authorization
Requested by the user on 2026-09-27. The user explicitly requires the audio-language and subtitle-language settings to be selection lists of common languages rather than free-text inputs.

On 2026-09-27 the user explicitly instructed that all currently tracked changes be committed for the next release. LANG-2 is therefore committed release scope.

## Evidence

0.7.18 candidate self-review: both list defaults/options use a non-empty `none` sentinel; normalization maps it to no preference before calling Kodi language APIs. First migration honors legacy language values despite the new default; subsequent runs repair empty/unknown list values without restoring an explicitly cleared legacy preference. All 76 tests passed. The archived 0.7.17 fixture demonstrates the two unsafe null-text options; source and candidate ZIP now contain none. Package settings are byte-identical to source. Playback/service/proxy implementation is unchanged from 0.7.17. Device recovery remains unverified.

2026-09-27 regression report: user says 0.7.17 installs but crashes Kodi almost immediately with no error. Reopened as the sole 0.7.18 blocker under the existing implementation/integration/publication authorization for this release work. Scope is settings/migration safety only; no playback changes. Base `a0b9eacb23b4816df7ac4c0f60e9c51fb7d1eb79`; no overlapping repository changes observed.

Concrete native crash trigger found: both new language controls contain `<option label="32920"></option>`. Kodi 21.3's `CSettingString::Deserialize` calls `optionElement->FirstChild()->Value()` without a null check while parsing options. An empty option has no text child; any initial settings read can reach this native null dereference before Python can display an error. Source: https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/settings/lib/Setting.cpp . The user's exact device stack has not been captured; this is a deterministic source-level crash trigger consistent with the report.

The previous mocks/XML-well-formedness checks missed Kodi's native parser requirement. Add validation of every option text and list default in both source and packaged settings, and legacy/new/explicit-None migration cases.

Published in 0.7.17 through PR #5, merge `18ffae9349b2d225b575cee6a276ea8dcd59143b`. Release/package run 36350783947, post-merge verification 36350856112 and Pages deployment 36350855315 passed. Deployed ZIP hash matched `77dd83244e01bae295d3118073d28b13b2a6d634576cf4ffae84fde14a49b0b1`.

2026-09-27 implementation/self-review (0.7.17 candidate): Both visible controls are curated lists of 29 common languages plus No preference, storing canonical codes independently. Hidden legacy strings migrate once; recognized aliases survive, unknown strings safely become No preference, and later explicit None does not resurrect a legacy preference. Existing subtitle-mode precedence and saved-subtitle smoke tests remain passing.

73 unit/smoke/integration tests passed with Python 3.12, including real FFmpeg MPEG-TS and fMP4 decode at start, forward seek and backward seek; workflow validation and diff whitespace checks passed. `_effective_hls_mode`, `_configure_hls` and `_configure_mp4` are AST-identical to base 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3. Reviewed implementation commit: `842ef37c8deb6ce340946dbbafa29fbd8745ec0c`. This is self-review, not independent review.

The released LANG-1 implementation added normalized preferred-language matching, but the current `plugin.video.appi/resources/settings.xml` still defines both `preferred_audio_language` and `preferred_subtitle_language` as string edit controls with free-text input.

## Outcome and next action
0.7.17 failed startup acceptance. The scoped 0.7.18 native-settings crash correction is implemented and self-reviewed (76 tests pass); package/integrate/publish under existing authorization, then confirm Kodi starts and both language lists work on the target device. Keep review/partial until that confirmation.

## Implementation session — 2026-09-27
User authorized implementation, testing, integration and publication in this session. Base 6d36d9a52733fbe6f3ded3ba5ee335cb779883e3. One worker owns the scoped source/settings/tests and shared release records; no concurrent worker changes observed. Target 0.7.17. Modes 0–2 must remain unchanged.
