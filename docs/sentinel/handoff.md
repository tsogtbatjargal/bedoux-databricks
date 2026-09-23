# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–03 are integrated into `main`, and so is chapter 04's first
increment. **171 tests pass on `main`; 190 on `feat/04-incident-log`.** Posts for chapters 00–03 are drafted, none
published, no tags.

- **Chapter 02** is demonstrated live — see
  [chapter-02-evidence.md](chapter-02-evidence.md).
- **Chapter 03 is acceptance-complete at code level, not demonstrated live
  against a model** (the user's decision). Its last criterion, "a failed
  check prevents the external call," is met by chapter 04's
  `model_call.call_model`: `test_evaluate_evidence_gate_verdict_alone_stops_the_call`
  forces the gate to refuse clean evidence and asserts zero provider calls,
  and removing the gate line from `call_model` makes exactly that test
  fail. The provider is a test fake, so no evidence has ever left the
  process; a live proof needs a real provider, deliberately deferred. See
  [chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#roadmap-acceptance-mapping).
- **Chapter 03's append-only evidence log** is deployed and confirmed live
  across four `dev` runs (`649621694823474`, `102698121895581` passing;
  `180753859499836` failing under an authorized `0.30` fault; `793561848702599`
  restore), plus a negative test: `UPDATE` and `DELETE` both rejected with
  `[DELTA_CANNOT_MODIFY_APPEND_ONLY]`. One predicted limitation confirmed live
  and not fixed: a task retry writes a duplicate row sharing `run_start_ms`.
  See [chapter-03-evidence.md](chapter-03-evidence.md) and
  [known-gaps.md](known-gaps.md#durable-incident-evidence-is-manual).
- **Chapter 04, first increment integrated** (PR #18, merge `b347a1c`, the
  eighth CI deployment: `Files: 70 uploaded, 0 deleted`, `Resources: 0
  created, 0 changed, 0 deleted, 8 unchanged`). `src/bedoux/model_call.py`
  gates evidence, re-checks the exact serialized payload, calls an injected
  provider once, and maps timeouts, provider errors, and malformed
  responses to `pending` with fixed reason codes. The only provider is a
  test fake, and nothing in `bedoux_analytics_job` calls this module. See
  [chapters/04-investigate-recover.md](chapters/04-investigate-recover.md).
- **Chapter 04, second increment: open PR from `feat/04-incident-log`, not
  merged** (merging deploys). `src/bedoux/incidents.py` adds a local
  append-only JSON Lines incident log: `investigate()` saves an incident
  (the checked payload, or no evidence if blocked) and fsyncs it *before*
  calling the provider, then records the outcome (status + reason codes;
  report text isn't stored). 19 tests, including a real subprocess dying
  mid-call and a check that the file never holds raw secrets or the
  canary. Unproven: durability through a machine crash, concurrent
  writers, retry deduplication, anything live.

**Left for the user, deliberately:** the diagrams. `architecture-context.svg`'s
`<desc>` still says "no such call site exists yet in this project" — out of
date now that `model_call.py` is a call site (with a fake provider). The
user maintains the diagrams by hand.

[known-gaps.md](known-gaps.md) is current, including the entry recording
that chapter 04's runtime model provider is a deliberate scope decision,
covered in the post/video instead of built.
[claude-implementation.md](claude-implementation.md) is a dated, expiring
brief whose first increment is now done — delete or archive it when the
next chapter-04 increment starts (see [README.md](README.md)'s "Docs
lifecycle").

## Branches and PRs

Remote branches: `main`, the five retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`,
`series/04-investigate-recover`), and the working branch
`feat/04-incident-log` (the open PR). The five merged working branches
from PRs #14–#17 and #19 were deleted after confirming each was merged
into `origin/main`. See [branch-workflow.md](branch-workflow.md).

Stale **local** copies of four deleted branches remain in the original
checkout (`docs/chapter-03-criterion-closed`,
`docs/chapter-03-live-close-out`, `docs/evidence-log-diagrams`,
`docs/grain-alignment`), plus a local `series/04-investigate-recover`.
Their deletion wasn't in scope; they're safe to remove with `git branch
-d` (all merged).

**One open PR:** chapter 04's second increment, from
`feat/04-incident-log`. Not merged — merging deploys.

## Exact next useful task

Review the open incident-log PR, then decide whether to merge it (a
deployment). After that, chapter 04's next steps, each needing its own
authorization: validate a report's evidence citations (and only then
store report text), and a bounded read-only tool set with recovery denied
by code. The runtime model provider stays deliberately unbuilt.
