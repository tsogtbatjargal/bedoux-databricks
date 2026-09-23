# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–03 are integrated into `main`, and so is chapter 04's first
increment. **171 tests pass.** Posts for chapters 00–03 are drafted, none
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

Retained chapter branches: `series/00-introduction`,
`series/01-know-your-platform`, `series/02-quality-gate`,
`series/03-protect-evidence`, `series/04-investigate-recover`.
Merged working branches kept after their PRs, deletable once verified
merged: `chore/evidence-docstring-fix` (PR #14),
`docs/evidence-log-diagrams` (PR #15), `docs/chapter-03-live-close-out`
(PR #16), `docs/grain-alignment` (PR #17), and
`docs/chapter-03-criterion-closed` (the docs PR recording the chapter 03
decision). See [branch-workflow.md](branch-workflow.md).

**No open PRs.**

## Exact next useful task

Chapter 04's next increment, which needs its own authorization: persist
an incident before the model call so a `pending` outcome survives a
restart, validate a report's evidence citations, and add a bounded
read-only tool set with recovery denied by code. The runtime model
provider stays deliberately unbuilt.
