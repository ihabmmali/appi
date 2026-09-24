---
id: FRAMEWORK-1
role: implementation
status: done
delivery: not-applicable
verification: passed
owner: lifecycle-setup-session
base_commit: eb2dc14be8361b82398ca86b8b4cac078e81caf9
artifact: none
---
# FRAMEWORK-1 — Establish portable development lifecycle pilot

## Objective
Expand Appi instructions and tracking for triage, research, architecture, implementation, review and release; provide next-release intake guidance.

## Scope
Repository instructions, workflow documents, task records, draft release scope and a standard-library validator/tests. Product runtime and package publishing are outside this task. Cross-model trials are follow-up evaluation, not claimed here.

## Acceptance
- Each role defines reads, outputs, write order and completion.
- Existing six product IDs and open issues are preserved in canonical records.
- Model-independent session/task formats and concurrent-work rules are documented.
- Draft release scope distinguishes candidates from committed work.
- Validator accepts the records and catches representative malformed records/links.
- Current product version and release archives are unchanged.

## Authorization
User explicitly requested expansion of Appi tracking/instructions as a framework proof of concept, followed by guidance for tracking next-release changes. GitHub documentation updates were authorized in this thread.

## Evidence
Self-review of all new procedures and migrated records against the prior trackers at the base above. Local document/record validator passed. Eight checker tests passed, covering valid records, missing/invalid metadata, index drift, unsupported completion/release claims and broken links. Runtime tests were not run because product source/packages are unchanged. Integration is the Git commit containing this record; no independent review is claimed.

## Outcome and next action
Initial structure and structural checks complete. See [PILOT.md](../workflows/PILOT.md) for unevaluated fresh-thread/multiple-model/concurrency trials. Select next-release scope through triage before starting product implementation.

