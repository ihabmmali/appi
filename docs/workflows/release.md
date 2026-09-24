# Release / rollback

Read task/user authority, NEXT_RELEASE, exact source candidate, included task evidence and project publishing commands.

1. Resolve committed-scope blockers or record an authorized exception. Pending device checks remain labeled pending.
2. Prepare manifest/version, CHANGELOG and README release summary. Draft RELEASE_NOTES as a candidate with source identity, changes, checks, limitations and fallback.
3. Run project release tests/build, inspect ZIP layout, hashes and index, preserve the fallback, and record outputs.
4. Publish under existing authorization, rechecking target SHA first. Verify artifact availability/checksums where possible. Partial or unverified publication leaves the release task open.
5. Update RELEASE_NOTES publication evidence → included task delivery/artifact fields → release task evidence/status → issue index and NEXT_RELEASE outcome → PROJECT_STATE current version last.
6. Validate records. Preserve released scope/history in the release record before clearing NEXT_RELEASE for another iteration.

A commit cannot contain its own SHA: refer to an existing tested source commit, and record the later publication commit in a follow-up documentation commit when needed. Do not fabricate hashes.

Rollback uses an authorized target, verifies restored availability and records the incident/follow-up. Required device acceptance, task completion and artifact publication stay separate.

