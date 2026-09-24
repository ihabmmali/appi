# Portable AI development lifecycle — pilot 0.1

Adopted for the Appi proof of concept on 2026-09-24. This is a working repository convention; cross-model effectiveness remains to be measured.

## Existing foundations

Related approaches reviewed on 2026-09-24:
- [AGENTS.md](https://agents.md/): an open repository instruction format.
- [GitHub Spec Kit](https://github.github.com/spec-kit/): specification, planning and implementation workflows across coding-agent integrations.
- [BMad Method](https://github.com/bmad-code-org/BMAD-METHOD): broader AI development workflows covering product, architecture, development and testing.
- [OpenSpec](https://github.com/Fission-AI/OpenSpec): change proposals/specifications, implementation and archiving into the current specification.
- [Architecture Decision Records](https://adr.github.io/): architectural decisions with alternatives, reasoning and consequences.

These are substantial precedents. This pilot adapts common practices into a small Git-based contract; it makes no claim to invent the category or constitute a universally adopted standard. Compare reuse of these frameworks before extending custom tooling. No third-party framework has been installed.

## Portable structure

The common contract is this file, role procedures and record templates. Project bindings are the goals, paths, commands and constraints in [ARCHITECTURE.md](ARCHITECTURE.md). Another repository can substitute those bindings and its task records.

Markdown and Git carry the process; Python's standard library supports the optional validator. Agents without automatic AGENTS.md discovery must be explicitly told to read it. Shared chat memory, vendor-specific commands and simultaneous agents are not required.

## Authority and truth

| Source | Establishes |
| --- | --- |
| User request and task Authorization | Permitted work, integration and publication |
| Accepted requirements / decisions | Intended behavior |
| Source at an identified commit | Implemented behavior |
| Tests and device observations | Verified behavior within a stated environment |
| Artifact retrieval / checksums / publication record | Delivered behavior |
| PROJECT_STATE | Short current summary and navigation |

Code can contain a bug; it does not override requirements. Resolve discrepancies instead of silently redefining intent. Roles are procedures, not permission grants.

## Record ownership

- `docs/tasks/<ID>.md`: canonical requirements, status, scope, authorization and evidence for one task.
- KNOWN_ISSUES: concise index of task IDs, statuses, roles and links.
- NEXT_RELEASE: proposed/committed/deferred scope for the next release; links tasks and does not duplicate their requirements.
- PROJECT_STATE: short current baseline and immediate priorities.
- ARCHITECTURE: current structure and clearly distinguished accepted constraints.
- `docs/decisions/<ID>.md`: proposed/accepted/rejected/superseded decisions, created when needed.
- `docs/experiments/<ID>.md`: reproducible hypotheses and results, created when needed.
- CHANGELOG: implemented changes, including Unreleased.
- RELEASE_NOTES: package-specific features, limitations and verification/publication evidence.

Preserve completed task records and stable IDs. Git provides detailed edit history. If GitHub Issues are adopted, explicitly choose a canonical status store and link it; do not maintain two competing copies.

## Work state

| Transition | Required evidence |
| --- | --- |
| proposed → ready | Actionable scope, acceptance criteria and authority identified |
| ready → active | Owner/session, actual base commit, paths and overlap check recorded |
| active → review | Outputs, checks and limitations recorded |
| review → done | Criteria passed and review recorded, including integration status |
| review → active | Findings require revision |
| Any nonterminal → blocked | Concrete blocker, previous status and next action |
| blocked → ready/active/review | Blocker resolved with reason recorded |
| Any nonterminal → cancelled | Decision source and rationale |
| done/cancelled → ready | Explicit reopening and new evidence/scope |

One worker may self-review low-impact work; label it self-review. Do not call it independent review. Research can be done when its evidence supports rejecting an idea. Triage can finish its intake work while leaving a product task proposed.

Track separate dimensions:
- Delivery: `not-applicable` for planning/docs tasks, `unreleased` for pending product work, `released` when linked to a published artifact.
- Verification: `pending`, `partial`, `passed`, `failed`, relative to that task's acceptance criteria.
- Done requires passed acceptance and evidence. Required device checks pending means review/blocked even if a patch has shipped.

## Read/write order

Read entry point → state → task → common contract and selected role → relevant source/evidence. Do not load all roles/tasks/history.

Produce primary outputs and evidence → canonical task → affected architecture/changelog/release documents → index and release scope → state last if changed. Each role specifies the conditional steps. This is a dependency order: publish coherent commits, not inconsistent intermediate snapshots.

Small edits need a compact task record, not a compulsory experiment or architecture decision. Complex changes receive the extra evidence they need.

## Collaboration and recovery

Use isolated task branches/worktrees for product changes, experiments and concurrent workers. Single-worker authorized documentation maintenance may use one coherent default-branch commit.

Record base SHA and paths. The integrator serializes claims and shared index/state updates. An owner field is not a lock. Resolve overlapping edits, review the combined diff and rerun affected checks before advancing the target branch without force. If target moved, reconcile from the latest version.

A resumed worker reads the record and actual diff, preserves completed work and continues the next unfinished step. Preserve existing user changes. Record unknown authorization; do permitted independent work until an essential decision is available.

## Validation and evaluation

`python3 tools/check_workflow.py` checks task structure, enums, index consistency, evidence-field requirements and local Markdown file links. It does not prove evidence is true, enforce permissions, lock workers, verify historical transitions or run product tests. CI and branch protection are separate controls and are not claimed to be configured.

Record pilot observations in [PILOT.md](docs/workflows/PILOT.md): fresh-thread continuation, another model/tool, conflicting edits, repeated clarification, documents loaded, elapsed time where available and regressions. The presence of files alone does not demonstrate efficiency.

