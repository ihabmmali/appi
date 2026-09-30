---
id: META-1
role: implementation
status: ready
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# META-1 — Surface media runtime and season episode counts

## Objective
Improve Appi's media information by surfacing runtime/length where the metadata provider exposes it, and by showing the number of locally indexed episodes inside every TV season folder.

## Current behavior
Appi's metadata worker currently requests TMDb Helper/Kodi JSON-RPC properties including title, plot, year, cast, director, artwork, IMDb number/IDs and custom properties, but it does not request or cache a runtime/duration field.

Appi's season folders are currently labelled only as `Season N` in both:
- the normal show season view; and
- the Recently Played show season view.

Appi already has the per-show episode catalogue locally, so season episode counts can be derived without another remote lookup.

## Runtime / media length
Where supported by TMDb Helper/Kodi JSON-RPC:

1. Request the runtime/duration property alongside the existing metadata fields.
2. Normalize it into a clear internal unit, preferably seconds.
3. Cache it with the title's other metadata.
4. Apply it to Kodi's video information tag so skins that display duration/runtime can surface it naturally.
5. Preserve it for movies and episodes when the provider supplies item-specific runtime.
6. Do not invent a runtime when no reliable value is returned.

Compatibility requirements:
- if `runtime` is unsupported by an older JSON-RPC/TMDb Helper path, retry without it just as the current code already falls back when `customproperties` is unsupported;
- a missing runtime must not make an otherwise successful metadata lookup fail;
- clearly distinguish seconds from minutes when normalizing the provider result;
- do not infer duration from HLS bitrate/file size.

If Kodi's standard video info tag supports the runtime field on the active build, use that native field rather than appending duration text to the plot.

## Season episode counts
For every season in a show:

- derive the count from `_load_show_episodes(show_key)`;
- count only episodes whose parsed `season` equals that season number;
- display the count in the season folder label, for example:
  - `Season 1 (8 episodes)`
  - `Season 2 (1 episode)`;
- use the same count in both `show_seasons()` and `show_recent_show()`;
- preserve the actual Kodi `season` metadata value and navigation target;
- do not rely on TMDb season counts when the local Appi catalogue is the source of truth for what is actually available.

If a season has zero locally indexed episodes because of malformed/incomplete catalogue data, do not fabricate a positive count.

## Acceptance
- A movie with runtime metadata shows its length through Kodi's normal video-information field.
- An episode with episode-specific runtime metadata shows its length where the skin supports it.
- Missing runtime leaves the item usable and does not display a false value.
- Metadata lookup remains compatible with the existing fallback path for older Kodi/TMDb Helper JSON-RPC property support.
- Runtime is stored in a single documented unit internally.
- Every season folder shows the number of locally available episodes.
- Singular/plural wording is correct for 1 episode versus multiple episodes.
- Normal TV-show navigation and Recently Played show navigation use the same count logic.
- Season folder counts match the actual number of items opened inside that season.
- No additional network metadata call is required merely to obtain season counts.
- Existing plot, artwork, cast, director and IMDb rating behavior is unchanged.
- Automated tests cover runtime present/missing/unsupported and season counts including singular/plural cases.

## Authorization
Requested by the user on 2026-09-29 as a feature request. META-1 is logged as a ready candidate and is not committed to release scope until explicitly selected under AGENTS.md.

## Evidence
Current `metadata.py` does not request, normalize or cache runtime. Current `_apply_metadata()` does not set a duration field. Current `show_seasons()` and `show_recent_show()` label folders only as `Season N`, while Appi already has the locally indexed episodes needed to calculate an exact available-episode count.

## Outcome and next action
Add runtime as optional metadata and centralize season-count label construction so both season views stay consistent.
