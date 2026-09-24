# Review / verification / integration

Read exact candidate/base commits, task criteria, authorization and diff.

1. Inspect the change and relevant tests; execute checks that resolve concrete risks. Device evidence names Kodi version, skin, platform, scenario and result.
2. Record findings against the reviewed commit and whether review was independent or self-review.
3. Return failures to active. Keep missing required evidence in review/blocked with a concrete next action.
4. Before authorized integration, reread target SHA, reconcile conflicts and rerun checks affected by integration. Preserve concurrent work; do not force-push.
5. Update task evidence/status → affected documentation → index/release plan → state. Validate the tracker.

Review authority alone does not authorize product expansion or publication. Completion means criteria and integration status are documented. Product release remains a separate delivery event.

