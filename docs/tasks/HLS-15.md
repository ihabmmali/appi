---
id: HLS-15
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# HLS-15 — Show actual buffered KB/MB in the normal preparation/recovery UI

## Objective
Make the normal Buffered Look Ahead status useful without enabling the detailed debug overlay.

During initial preparation and ordinary buffering/recovery, Appi must show the user how much playable media is actually buffered in human-readable storage units such as KB or MB. A percentage/progress bar alone is not sufficient.

## Scope
Update the simple, always-available Buffered Look Ahead preparation/recovery UI.

At minimum:
- show actual contiguous playable cached-ahead bytes using KB or MB;
- where a startup/high-water target exists, also show the target amount, for example **Buffered 42.6 MB / 96 MB**;
- continue updating the value while the reservoir fills;
- use the same truthful metric during seek/resume epoch preparation and recovery where applicable;
- keep the existing progress bar if useful, but never make it the only indication of fill state;
- do not require Detailed buffer debug overlay to be enabled.

The displayed amount must describe media that is actually usable as contiguous playback reserve for the active epoch. Do not count stale files, unrelated tracks, abandoned epochs, or arbitrary total disk usage as "buffered".

HLS-13 owns the deep-reservoir algorithm and defines the actual startup/high-water target. HLS-12 owns fresh seek/resume epochs. HLS-14 owns the optional detailed in-playback overlay.

## Display behavior
Examples are illustrative rather than exact formatting requirements:
- `Filling buffer — 18.4 MB / 96 MB`
- `Filling buffer — 742 KB / 32 MB`
- `Appi buffering — 7.2 MB buffered`

If the exact target is temporarily unknown, show the actual buffered amount alone rather than hiding the metric or fabricating a percentage.

A secondary playable-seconds value may also be shown, but KB/MB is mandatory because the user specifically wants to see the actual stored reserve.

## Acceptance
- Initial Buffered Look Ahead preparation visibly shows actual buffered storage in KB or MB.
- The value increases as contiguous playable media is fetched.
- When a startup/high-water target is known, both current and target storage are shown.
- The text corresponds to actual playable reserve for the active epoch, not total cache directory size.
- The numeric text continues to update even if the progress bar is present.
- Seek/resume preparation created by HLS-12 shows the new epoch's buffered amount rather than stale pre-seek data.
- Recovery/buffering UI shows the current reserve in KB/MB where the simple status window is visible.
- The display never reports 100% or a target amount reached unless HLS-13's readiness criteria are actually satisfied.
- It works with the detailed overlay disabled.
- UI updates remain lightweight enough not to reduce fetch throughput materially.
- Automated tests verify byte-to-KB/MB formatting, monotonic fill for a fixed epoch, epoch reset, stale-cache exclusion and target display.
- Target-device acceptance observes the numeric KB/MB amount changing during preparation of a known multi-variant HLS stream.

## Authorization
Requested explicitly by the user on 2026-09-28: the initial buffering information is too weak and must show how much is actually buffered in KB or MB, not just a progress bar. The user instructed that these changes be committed for the next release. HLS-15 is therefore committed release scope.

## Evidence
Published 0.7.20 shows a simple preparation window/progress bar but does not give the user a useful numeric view of the actual buffered reserve. This makes it difficult to distinguish real reservoir growth from a stalled or misleading percentage.

## Outcome and next action
Committed for the next release. Wire the simple preparation/recovery UI directly to HLS-13/HLS-12's active-epoch playable-reserve byte metrics and display those bytes as KB/MB throughout filling and recovery.
