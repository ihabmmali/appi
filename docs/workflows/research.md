# Research / innovation

Read task, relevant source and architecture/decisions. State the question and initial time/tool/candidate budget.

1. Create `docs/experiments/<ID>.md` from [TEMPLATES.md](TEMPLATES.md): hypotheses, baseline, success measures, sanitized inputs and budget.
2. Use an isolated branch/worktree for prototypes. Retain reproducible code under `experiments/<ID>/` or reference its commit.
3. Record commands, environment, measurements, failed candidates, limitations and recommendation. Stop at sufficient evidence or the agreed budget; explain unresolved uncertainty.
4. Update experiment → task evidence → proposed ADR or follow-up task if needed → index/release scope → state only if changed.
5. Validate records and inspect the scope of the diff.

Completion is an evidence-backed recommendation, including rejection of an approach. A successful prototype is not an accepted architectural decision or a released feature. Promotion requires a recorded decision and implementation scope.

