# Working on Appi

These instructions apply to work in this repository. Keep this file short and stable; put changing facts in the trackers linked below.

## Start a task

1. Read [PROJECT_STATE.md](PROJECT_STATE.md) for the current baseline and priorities, then the relevant entry in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
2. Check `plugin.video.appi/addon.xml` and the current source before assuming a version or behavior. Use [ARCHITECTURE.md](ARCHITECTURE.md) for the module map. The repository source wins if documentation differs.
3. Define the observed behavior, expected behavior and scope of this task. Reproduce a bug when possible; distinguish a user report, a code-level finding, an automated test and a Kodi device result.

## Design boundaries

- Preserve Kodi's native watched and resume state as the authority. Appi's recent history is for identity and order.
- Keep movie and TV provider order where browsing or refresh depends on it. TV catalogues are numbered pages; do not assume a partial scan proves an entire feed unchanged. Handle overlap, page shifts and full-refresh fallback explicitly if implementing fast refresh.
- Treat search navigation as a Kodi directory behavior: test category/query entry, results, show/back, cancellation and favorites refresh together.
- Protect the user-configured catalogue URLs and profile data. A failed or cancelled refresh should not discard a valid cache.
- Avoid changing HLS/playback behavior as a side effect of unrelated tasks. Keep the published, user-confirmed fallback package available; find its current version in PROJECT_STATE.md.
- Keep background metadata and external FFmpeg script generation distinct from catalogue refresh and playback. Inspect current code before changing these flows.

## Finish a task

- Make a focused change with meaningful regression coverage for affected behavior. Run the relevant tests; for a release, run `python3 -m unittest discover -s tests` and `python3 tools/build_repository.py`, inspect ZIP structure, hashes and index, and record any Kodi device testing separately.
- If publishing a package, update `plugin.video.appi/addon.xml`, release summaries in `README.md` and `CHANGELOG.md`, and the package/verification record in `RELEASE_NOTES.md`. Update `PROJECT_STATE.md` and `KNOWN_ISSUES.md` when status changes. Preserve the previous fallback.
- If work is incomplete, record the concrete remaining issue and evidence in `KNOWN_ISSUES.md`; do not claim the behavior was fixed merely because tests passed.
- End with a short report: changed behavior, checks actually run, release or commit reference if applicable, and remaining risks. No separate conversational handoff document is needed.
