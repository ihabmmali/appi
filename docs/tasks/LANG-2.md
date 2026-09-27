---
id: LANG-2
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
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

This task is recorded as actionable work but is not committed release scope unless the user explicitly commits/includes it in the next release under AGENTS.md.

## Evidence
The released LANG-1 implementation added normalized preferred-language matching, but the current `plugin.video.appi/resources/settings.xml` still defines both `preferred_audio_language` and `preferred_subtitle_language` as string edit controls with free-text input.

## Outcome and next action
Replace both free-text controls with curated language-selection lists while preserving LANG-1 normalization and backwards compatibility for existing stored values.
