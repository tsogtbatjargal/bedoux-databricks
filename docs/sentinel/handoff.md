# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–03 are integrated into `main`, and so are chapter 04's first
two increments. **196 tests pass.** Posts for chapters 00–03 are drafted,
none published, no tags.

- **Chapter 02** is demonstrated live — see
  [chapter-02-evidence.md](chapter-02-evidence.md).
- **Chapter 03 is acceptance-complete at code level, not demonstrated live
  against a model** (the user's decision). Its last criterion, "a failed
  check prevents the external call," is met by chapter 04's model-call
  path: `test_evaluate_evidence_gate_verdict_alone_stops_the_call` forces
  the gate to refuse clean evidence and asserts zero provider calls. Since
  PR #20, `send_payload` also refuses anything but a `CheckedPayload`, so
  the gate can't be skipped by calling it directly. The provider is a test
  fake; no evidence has ever left the process. See
  [chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#roadmap-acceptance-mapping).
- **Chapter 03's append-only evidence log** is deployed and confirmed live
  across four `dev` runs plus a negative `UPDATE`/`DELETE` test. One
  predicted limitation confirmed and not fixed: a task retry writes a
  duplicate row. See [chapter-03-evidence.md](chapter-03-evidence.md) and
  [known-gaps.md](known-gaps.md#durable-incident-evidence-is-manual).
- **Chapter 04, first increment** (PR #18, merge `b347a1c`, eighth CI
  deployment): `src/bedoux/model_call.py`, the guarded model-call path.
- **Chapter 04, second increment** (PR #20, merge `27e20c1`, ninth CI
  deployment: `Files: 72 uploaded, 0 deleted`, `Resources: 0 created, 0
  changed, 0 deleted, 8 unchanged`):
  - `src/bedoux/incidents.py`: a local append-only JSON Lines incident log.
    `investigate()` saves an incident (the checked payload, or no evidence
    if the gate blocked) and fsyncs it before calling the provider, then
    records the outcome. A process that dies mid-call leaves the incident
    pending.
  - `model_call.CheckedPayload`: only `prepare_payload` can create one, and
    `send_payload` raises `TypeError` on anything else before touching the
    provider.
  - Unproven: durability through a machine crash (only process death is
    tested), concurrent writers, retry deduplication, anything live.
  - Only a test fake exists as a provider, and nothing in
    `bedoux_analytics_job` calls either module. See
    [chapters/04-investigate-recover.md](chapters/04-investigate-recover.md).

**Left for the user, deliberately:** the diagrams. `architecture-context.svg`'s
`<desc>` still says "no such call site exists yet in this project" — out of
date since chapter 04's first increment. The user maintains the diagrams by
hand.

[known-gaps.md](known-gaps.md) is current, including the entry recording
that chapter 04's runtime model provider is a deliberate scope decision,
covered in the post/video instead of built.
[claude-implementation.md](claude-implementation.md) is a dated, expiring
brief — delete or archive it when the next chapter-04 increment starts
(see [README.md](README.md)'s "Docs lifecycle").

## Branches and PRs

Remote branches: `main`; the five retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`,
`series/04-investigate-recover`); and `feat/04-incident-log`, a merged
working branch (PR #20) kept because remote deletion wasn't authorized —
deletable once verified merged. See [branch-workflow.md](branch-workflow.md).

Local branches: `main` and `series/04-investigate-recover`. The merged
local working branches were deleted with `git branch -d` after checking
each was an ancestor of both `main` and `origin/main`.

**No open PRs.**

## Exact next useful task

Chapter 04's next steps, each needing its own authorization: validate a
report's evidence citations (and only then store report text), and a
bounded read-only tool set with recovery denied by code. The runtime model
provider stays deliberately unbuilt.
