---
id: META-1
role: implementation
status: review
delivery: unreleased
verification: partial
owner: builder-publisher-2026-09-30
base_commit: e359459e1e3734e1c60608632b2213fe33bc92e7
artifact: none
---
# META-1 — Surface media runtime and season episode counts

## Objective
Improve Appi's media information by surfacing runtime/length where the metadata provider exposes it, and by showing the number of locally indexed episodes inside every TV season folder.

## Scope
Add optional runtime normalization/application to the existing metadata path and derive season counts solely from the locally indexed per-show episodes. Preserve existing metadata fields, browsing targets and network behavior outside the optional runtime request.

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
Requested by the user on 2026-09-29 as a feature request. On 2026-09-30 the user explicitly instructed that all current candidates be committed for the next release. META-1 is committed next-release scope.

## Evidence
Current `metadata.py` does not request, normalize or cache runtime. Current `_apply_metadata()` does not set a duration field. Current `show_seasons()` and `show_recent_show()` label folders only as `Season N`, while Appi already has the locally indexed episodes needed to calculate an exact available-episode count.

## Outcome and next action
Add runtime as optional metadata and centralize season-count label construction so both season views stay consistent.

## 0.7.24 implementation evidence
Source implementation: `4cfd2939567113d34e73ecb97d3c5fed9d7089bd`. Automated coverage: `94c62ee25271b13a13b78038f344bcf51e8d0ffc`.

Metadata lookup requests optional `runtime`, normalizes supported numeric runtime/duration to seconds, retries compatible JSON-RPC property combinations after Invalid params, caches `runtime_seconds` and applies it through Kodi's native duration tag. Season labels use locally derived counts with correct singular/plural wording.

Release gate run `36763219643` passed all 108 unit/smoke tests (1 skipped). Packaging was blocked only by task-record Scope validation; target-device presentation remains pending.

## 0.7.24 self-review
Self-review completed against artifact commit `dec2cb5f491aba7568e2f6d7ba28be91ba247369`. Release run `36763427233` passed 108 unit/smoke tests (1 skipped), tracker validation and deterministic package inspection. Tests cover runtime present, absent and unsupported plus local season-count singular/plural behavior.

Review confirms runtime is stored in seconds, missing/unsupported runtime is non-fatal, episode runtime stays episode-specific and season counts are derived without a new network call. Verification remains partial pending target-device presentation acceptance.
