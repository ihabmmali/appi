---
id: HLS-3
role: triage
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-3 — Cancel quality selection without starting playback

## Objective
Fix the HLS quality/rendition selection flow so cancelling the resolution/bitrate chooser aborts playback and returns the user to the previous Appi view.

Observed behavior: when "Ask quality before playback" is active, pressing Cancel in the rendition-selection dialog currently allows the media to start playing instead of treating cancel as an abort.

## Scope
Track the cancel/abort semantics of the manual HLS quality chooser. Determine whether the unexpected playback comes from Appi, InputStream Adaptive, Kodi's resolved-item flow, or their interaction.

This task is limited to the manual quality-selection path. It is related to [HLS-2](HLS-2.md), which owns HLS mode semantics and ABR behavior, but HLS-3 remains a distinct regression because cancel must not start playback regardless of future mode naming.

Implementation should preserve the originating Appi directory/search/detail context and avoid creating playback side effects when the user cancels before playback starts.

## Acceptance
- With "Ask quality before playback" enabled, open a multi-variant HLS item and cancel the quality chooser.
- No media playback starts after cancel.
- The user returns to the immediately previous Appi view/context rather than Kodi's add-on browser or an unrelated directory.
- No Recently Played entry, playback-session record, resume state, metadata side effect, or other playback-start side effect is created solely because the chooser was cancelled.
- Repeating the cancel path behaves consistently for movies and TV episodes.
- Selecting a valid rendition still starts playback normally.
- If the cancel event cannot be intercepted directly through InputStream Adaptive, document and implement the safest supported Appi/Kodi flow that produces the required user-visible behavior.
- Add a regression check or reproducible device test covering both cancel and successful selection.

## Authorization
Reported by the user on 2026-09-24 as a bug to fix. This thread is authorized to record and plan the change; implementation, integration and publication remain separate assignments.

## Evidence
User observation: cancelling the resolution/bitrate selection dialog causes the selected media to play instead of returning to the previous view.

No source-level root cause or target-device reproduction has yet been recorded for this task.

## Outcome and next action
Assign a focused implementation/review worker to trace the manual quality-selection cancel path and prevent playback resolution when the chooser is dismissed.
