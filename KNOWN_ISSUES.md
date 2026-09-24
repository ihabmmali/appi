# Known issues and proposed work

Updated: 2026-09-24. Track user reports separately from verified fixes. Move completed entries to [CHANGELOG.md](CHANGELOG.md) and [RELEASE_NOTES.md](RELEASE_NOTES.md) only after implementation and verification.

| ID | Status | Issue / expected result | Verification or next action |
| --- | --- | --- | --- |
| SEARCH-1 | Needs device verification | Earlier 0.7.9–0.7.11 search releases had empty results and back/cancel/favorites navigation failures. 0.7.12 claims to preserve result sessions, but the target device result has not been confirmed here. Search should show cached matches; back and cancel should return to the originating directory; a favorites action should keep results in place. | Exercise movie, TV and mixed search in Kodi, including no match, cancel, enter show/back, favorite/unfavorite and back. Record version, skin, exact navigation sequence and logs if still broken. |
| REFRESH-1 | Planned; absent in 0.7.12 | Full TV refresh downloads numbered pages until an end condition. Add optional configurable leading-window comparison for a prepend-only feed. | Specify overlap algorithm, page boundary behavior, deletion/reordering detection and full-refresh fallback. Verify with page shifts and duplicate items. Avoid claiming a small scan proves the entire remote catalogue unchanged. |
| REFRESH-2 | Planned; absent in 0.7.12 | Optional automatic catalogue refresh, including appropriate failure handling and scheduling. | Define interval, startup behavior, user control and whether the fast/full mode applies; avoid refreshing during playback if it harms responsiveness. |
| LANG-1 | Planned; absent in 0.7.12 | Default audio and subtitle language preferences matching stream labels approximately: `eng`, `en`, `English`, etc. | Define aliases, normalization, preference order, missing/ambiguous labels and what to do when no match exists. Verify HLS and Kodi stream selection on real samples. |
| HLS-1 | Investigation | Some specific ~6 Mbps URLs pause frequently despite generous Kodi buffering, while higher bitrate streams work. | Capture a failing URL's playlist structure, segment delivery timings, Kodi/inputstream logs and behavior after fixed rendition selection before changing playback settings. |
| UI-1 | Investigation | A Kodi skin may hide the playback **Program Settings** control used for HLS resolution selection. | Compare the same stream in Estuary and the target skin; distinguish skin visibility from Appi behavior. |

## Candidate iteration

Choose a small coherent work package and give it a separate chat or issue. A first candidate is SEARCH-1 verification/fix; refresh and language work are independent planned features. Preserve the 0.7.8 package and avoid unrelated HLS playback changes.
