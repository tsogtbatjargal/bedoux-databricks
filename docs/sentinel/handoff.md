# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–04 are integrated into `main`. **273 tests pass on `main`.**
Posts for chapters 00–04 are drafted, none published, no tags.

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
- **Chapter 04 is acceptance-complete at code level, not demonstrated
  live** (the user's decision after PR #23 merged).
  - Five increments are integrated: the guarded model-call path (PR
    #18), the local incident log and `CheckedPayload` (PR #20), report
    citations (PR #21), read-only tools (PR #22), and recovery approval
    with duplicate-free replay (PR #23, merge `c9b9815`).
  - PR #23 was the twelfth CI deployment: `Files: 77 uploaded, 0
    deleted`, `Resources: 0 created, 0 changed, 0 deleted, 8 unchanged`.
  - Five criteria are met at code level, and the offline/live
    separation holds trivially.
  - The before/after business metric and the live run are deliberately
    deferred together. Both need a real provider, which the user will
    cover in the post or video instead of building.
  - No real model has been called, only test-fake executors exist, and
    no tool has read a real table.
  - The LinkedIn draft is in the chapter doc, unpublished.

  See [chapters/04-investigate-recover.md](chapters/04-investigate-recover.md#roadmap-acceptance-mapping)
  and [known-gaps.md](known-gaps.md#chapter-04s-runtime-model-provider-is-deliberately-not-built).

**Left for the user, deliberately:** the diagrams. `architecture-context.svg`'s
`<desc>` still says "no such call site exists yet in this project" — out of
date since chapter 04's first increment. The user maintains the diagrams by
hand.

**Known stale text, left alone this session:**
- `src/bedoux/evidence.py`'s module docstring still says "no outbound
  model call exists anywhere in this project yet." Fixing it touches
  `src/**` and so deploys; that's a separate decision.
- [claude-implementation.md](claude-implementation.md) is a dated,
  expiring brief. Its own instruction was to delete or archive it once
  chapter 04 started, and that hasn't been done (see
  [README.md](README.md)'s "Docs lifecycle").

[known-gaps.md](known-gaps.md) is current.

## Branches and PRs

Remote branches: `main` and the five retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`,
`series/04-investigate-recover`). `feat/04-recovery-approval` was deleted
locally and remotely after confirming it was merged into `origin/main`.
See [branch-workflow.md](branch-workflow.md).

Local branches: `main` and `series/04-investigate-recover`.

**No open PRs.**

## Exact next useful task

Chapter 05, "Spend intelligence carefully," is not authorized. It would
start from integrated `main` on `series/05-jev-routing`: optional Jev
classification/routing, compared against rules only and rules plus the
reasoning model on a held-out incident set. Its acceptance asks for
measured misses, routing quality, latency, and cost, so a live comparison
would need a real provider. Without Jev access, only adapter and fixture
work is possible (see [roadmap.md](roadmap.md)).
