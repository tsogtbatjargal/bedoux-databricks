# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–05 are integrated into `main`. **310 tests pass on `main`; 339 on
`series/06-agent-boundaries`.**
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

- **Chapter 06, first step: on `series/06-agent-boundaries`, PR #26 open,
  not merged** (merging deploys: it changes `src/**`).
  - Instructions inside evidence are data, never commands. Tests put the
    instruction in evidence and tool results and show it can't dismiss an
    incident, add a tool, approve or trigger a recovery, or clear a
    failed gate.
  - New `src/bedoux/boundaries.py`: a regex flag, `instruction_in_evidence`,
    made a severe, non-dismissable routing signal. It's easy to evade
    (paraphrase, another language, split fields) and was written after
    seeing `h07` and `t04`; the doc says so.
  - `h07` is no longer dismissed under any route. The classifier route
    still labels it `healthy` but sends it to a person.
  - Chapter 05's held-out set, hash, and numbers are unchanged. Its
    comparison test now passes `instruction_rule=False`, which
    reproduces chapter 05's rules; the chapter 06 result is recorded
    separately.
  - 29 new tests (339 total), each mutation-checked.
  - Criterion map in
    [chapters/06-rules-of-command.md](chapters/06-rules-of-command.md).
    Not built yet, offline: an explicit prohibited-action list (export,
    delete, grant) and an audit record of routing decisions.

[known-gaps.md](known-gaps.md) is current.

## Branches and PRs

Remote branches: `main`, the six retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`,
`series/04-investigate-recover`, `series/05-jev-routing`), and
`series/06-agent-boundaries` (chapter 06, PR open). The merged working
branch `docs/05-close-and-post` was deleted locally and on the server
after confirming it in `git branch -r --merged origin/main`. See
[branch-workflow.md](branch-workflow.md).

Local branches: `main` and `series/06-agent-boundaries`.

**Open PR:** #26, chapter 06's first step, from `series/06-agent-boundaries`.
Not merged. Wait for Unit tests to pass on the PR head before any merge,
docs-only PRs included; PR #25 merged before its checks finished.

## Exact next useful task

Review chapter 06's first-step PR. Merging it deploys and is not
authorized. After it, offline chapter 06 work that could follow, none of
it authorized:
- an explicit prohibited-action list at the executors, with its own
  refusal code;
- writing routing decisions to the incident log as an audit record
  (codes only, no evidence text);
- a failure analysis written from the fakes, labelled that way.

Still deferred and not authorized: the live provider work for chapters
04–06 (a Jev access path, a reasoning model, frozen versions, a spend
cap), publishing any post, and tagging.
