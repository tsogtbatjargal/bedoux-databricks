# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–05 are integrated into `main`. **310 tests pass on `main`.**
Posts for chapters 00–05 are drafted, none published, no tags.

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

- **Chapter 05 is acceptance-complete at code level, not demonstrated
  live** (the user's decision after PR #24 merged; merge `9274317`,
  thirteenth CI deployment: `Files: 80 uploaded, 1 deleted`, `Resources:
  0 created, 0 changed, 0 deleted, 8 unchanged`).
  - `src/bedoux/routing.py` has three strategies: rules only, rules plus
    reasoning, and rules plus a cheap classifier with selective
    escalation. Every model call goes through `prepare_payload` and
    `send_payload`.
  - Severe deterministic signals can't be dismissed, in both the flat
    and the `gate_evidence_log` shape. A model can't dismiss evidence
    the rules don't recognise.
  - A frozen, synthetic held-out set (hash pinned) and a scoring harness.
  - The chapter's central result is a measurement, so closing it at code
    level means the harness exists but the result doesn't. The live
    three-way comparison is deliberately deferred with the other
    provider work (Jev access, a reasoning model, frozen versions, a
    spend cap); the user will cover it in the post or video.
  - Fake models only. Scores describe scripted fakes; costs are relative
    *estimate* units; latency isn't measured.
  - The LinkedIn draft is in the chapter doc, unpublished. It leaves out
    the fake scores and estimate units.

  See [chapters/05-spend-intelligence.md](chapters/05-spend-intelligence.md#closing-decision)
  and [known-gaps.md](known-gaps.md#chapter-05s-comparison-is-a-harness-without-a-result).

[known-gaps.md](known-gaps.md) is current.

## Branches and PRs

Remote branches: `main` and the six retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`,
`series/04-investigate-recover`, `series/05-jev-routing`). The chapter
05 branch was kept after PR #24 merged, like the others; GitHub's
delete-head-branch-on-merge setting is off. See
[branch-workflow.md](branch-workflow.md).

Local branches: `main`, `series/04-investigate-recover`, and
`series/05-jev-routing`. The last two are merged and could be removed
locally under branch-workflow.md's checks, but no branch deletion was
authorized this session.

**No open PRs.**

## Exact next useful task

Chapter 05 continues. None of the following is authorized:
- The live comparison needs real providers: a Jev access path and a
  reasoning model, with frozen versions and a spend cap.
- Offline follow-ups that could come first:
  - wire the reasoning model's chapter 04 report into routing;
  - add runbooks behind the labels;
  - grow the held-out set, which only matters once real models exist.
