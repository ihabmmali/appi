# Record and session templates

Create only records needed for the work. Task metadata uses a flat YAML-compatible mapping with plain string values; the validator supports this small subset without dependencies.

## Task: docs/tasks/ID.md

```markdown
---
id: EXAMPLE-1
role: implementation
status: proposed
delivery: unreleased
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# EXAMPLE-1 — Short objective

## Objective
Observed versus expected behavior and report reference.

## Scope
Allowed paths, dependencies, exclusions and any budget.

## Acceptance
- Observable success conditions; identify real-device checks.

## Authorization
Source of the request; authority for implementation, integration and publication.

## Evidence
Not yet recorded. Add commands/results, environment, reviewed commit and review type.

## Outcome and next action
Current finding, blocker/previous status where relevant, and next step.
```

Use the statuses defined in [LIFECYCLE.md](../../LIFECYCLE.md). When work becomes active, replace unset with the full base SHA and assign an owner/session. Task ID equals filename. Released work requires an artifact reference; done requires passed verification and evidence.

## Experiment: docs/experiments/ID.md

Task/base commit; question and hypotheses; baseline; success measures and budget; environment and sanitized inputs; commands; per-candidate results including failures; limitations; recommendation; prototype commit and follow-up links.

## ADR: docs/decisions/ID.md

Task/date; status (proposed, accepted, rejected, superseded); context; alternatives; decision and reasoning; acceptance authority/evidence; implementation gap; migration/rollback consequences; supersedes/superseded-by links.

## Session starter

Repository: https://github.com/ihabmmali/appi
Read AGENTS.md and PROJECT_STATE.md. Task: <ID or goal>.
Role: <triage/research/architecture/implementation/review/release>.
Authorized outcome: <record requirements / experiment / implement / integrate / publish>.
Follow the corresponding lifecycle procedure and update canonical records.

A clear natural-language request is sufficient; the worker can infer the role. Mention the repository explicitly in a fresh tool/model.

## Next-release intake example

For Appi, record these candidates for the next release:
- Must have: <change and the result I expect>.
- Nice to have: <change>.
- Bug: <steps, actual behavior, expected behavior, version/skin>.
- Constraint: <what needs to remain compatible>.
Triage and update the trackers; implementation is a separate assignment.

