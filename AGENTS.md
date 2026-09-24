# Appi worker entry point

Read this file before repository work. User authorization and host/tool policies govern what may be done.

1. Read [PROJECT_STATE.md](PROJECT_STATE.md), then the assigned task linked from [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
2. Read [LIFECYCLE.md](LIFECYCLE.md) and only the relevant role below. Consult [ARCHITECTURE.md](ARCHITECTURE.md) and source as needed; read history only when it affects the task.
3. Confirm objective, acceptance criteria, base commit, scope and existing authorization. Infer the role from a clear request. Record existing authorization without asking again.
4. Follow the role's write order, update evidence before summaries, and commit related changes together. Update current state only when its summary changes.

| Intent | Procedure |
| --- | --- |
| Capture/prioritize issues or plan a release | [Triage](docs/workflows/triage.md) |
| Investigate an idea or compare algorithms | [Research](docs/workflows/research.md) |
| Decide long-term architecture | [Architecture](docs/workflows/architecture.md) |
| Implement a feature or fix | [Implementation](docs/workflows/implementation.md) |
| Verify, review or integrate | [Review](docs/workflows/review.md) |
| Package, publish or roll back | [Release](docs/workflows/release.md) |

One worker may perform consecutive roles; changing role does not expand authority. Concurrent work uses task branches/worktrees and a designated integrator. Never overwrite changes from a stale snapshot.

Appi goals and constraints are in ARCHITECTURE. [Templates](docs/workflows/TEMPLATES.md) provide task, experiment, decision and session formats. [NEXT_RELEASE.md](NEXT_RELEASE.md) tracks proposed release scope.

Validate tracker changes with `python3 tools/check_workflow.py`. End with result, checks actually run, commit/publication reference and remaining work. The committed records are the handoff.

