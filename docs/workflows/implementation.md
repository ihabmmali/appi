# Implementation

Read task criteria, project constraints and relevant source/tests at the current base.

1. Record owner/session, base SHA, paths, dependencies and authority; check overlaps and set active.
2. Reproduce the defect or establish the feature baseline. Resolve significant uncertainty through research/architecture as needed.
3. Make the scoped change and meaningful regression checks. Inspect behavior, data preservation and unintended changes.
4. Update source/tests → task evidence and review status → affected ARCHITECTURE → CHANGELOG under Unreleased → index/release plan → state if changed.
5. Apply the [review procedure](review.md) before authorized integration. Record self-review honestly.

Version bumps, package changes and publication belong to the [release procedure](release.md) when authorized. Completion requires the task's criteria and evidence; pending required device checks keep it open. Separate integration, delivery and verification in the record.

