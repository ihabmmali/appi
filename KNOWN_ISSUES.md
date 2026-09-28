# Appi task index

Updated: 2026-09-27. Each linked task is the canonical requirements/status/evidence record. This index covers bugs, features and investigations. Preserve IDs and completed records; archive through Git/history instead of erasing evidence.

| ID | Status | Role | Task |
| --- | --- | --- | --- |
| SEARCH-1 | review | review | [Search navigation regression investigation](docs/tasks/SEARCH-1.md) |
| SEARCH-2 | review | review | [User-manageable search history](docs/tasks/SEARCH-2.md) |
| REFRESH-1 | review | review | [Fast leading-window catalogue refresh](docs/tasks/REFRESH-1.md) |
| REFRESH-2 | review | review | [Optional automatic catalogue refresh](docs/tasks/REFRESH-2.md) |
| LANG-1 | review | review | [Default audio and subtitle languages](docs/tasks/LANG-1.md) |
| LANG-2 | review | implementation | [Common-language selection lists for audio and subtitles](docs/tasks/LANG-2.md) |
| LANG-3 | review | implementation | [Preferred language setting is not applied at playback](docs/tasks/LANG-3.md) |
| AUDIO-1 | review | implementation | [Restore audio for InputStream Adaptive playback](docs/tasks/AUDIO-1.md) |
| DIAG-1 | review | review | [Export bounded playback diagnostics](docs/tasks/DIAG-1.md) |
| DIAG-2 | review | review | [Causal HLS playback telemetry](docs/tasks/DIAG-2.md) |
| HLS-1 | proposed | research | [Investigate repeated HLS stalls](docs/tasks/HLS-1.md) |
| HLS-2 | review | review | [Explicit adaptive bitrate HLS mode](docs/tasks/HLS-2.md) |
| HLS-3 | review | review | [Cancel quality selection without starting playback](docs/tasks/HLS-3.md) |
| HLS-4 | review | review | [Repair 0.7.13/0.7.14 manual HLS playback regression](docs/tasks/HLS-4.md) |
| HLS-5 | review | implementation | [Buffered Look Ahead Playback](docs/tasks/HLS-5.md) |
| HLS-6 | review | implementation | [Configurable Buffered Look Ahead buffer, quality choice and debug overlay](docs/tasks/HLS-6.md) |
| HLS-7 | review | implementation | [Stabilize Buffered Look Ahead startup, seeking and failure handling](docs/tasks/HLS-7.md) |
| HLS-8 | review | implementation | [Repair 0.7.18 Buffered Look Ahead preparation and runtime failure](docs/tasks/HLS-8.md) |
| HLS-9 | review | implementation | [Make InputStream Adaptive a prerequisite dependency](docs/tasks/HLS-9.md) |
| HLS-10 | review | research | [Verify/repair Buffered Look Ahead detailed debug overlay](docs/tasks/HLS-10.md) |
| HLS-11 | review | implementation | [Repair multi-variant HLS seek, resume-point and recovery timeout](docs/tasks/HLS-11.md) |
| HLS-12 | ready | implementation | [Replace Buffered Look Ahead seek/resume with fresh buffer epochs](docs/tasks/HLS-12.md) |
| SUB-1 | review | review | [Restore downloaded subtitle persistence across playback sessions](docs/tasks/SUB-1.md) |
| PLAY-1 | proposed | research | [Investigate playback-start Trakt API error](docs/tasks/PLAY-1.md) |
| UI-1 | proposed | research | [Playback Program Settings visibility](docs/tasks/UI-1.md) |
| UI-2 | review | implementation | [About / installed Appi version](docs/tasks/UI-2.md) |
| UI-3 | review | implementation | [Appi add-on artwork / icon](docs/tasks/UI-3.md) |
| UI-4 | review | implementation | [Integrate revised Appi artwork](docs/tasks/UI-4.md) |
| FRAMEWORK-1 | done | implementation | [Lifecycle pilot setup](docs/tasks/FRAMEWORK-1.md) |

Use [NEXT_RELEASE.md](NEXT_RELEASE.md) to select release scope. A candidate is not an implementation commitment. Follow [triage](docs/workflows/triage.md) to add/change a task.
