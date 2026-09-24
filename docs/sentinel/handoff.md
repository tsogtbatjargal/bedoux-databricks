# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–06 are integrated into `main`. **362 tests pass on `main`** (372 on
`series/07-full-demo`).
Posts for chapters 00–06 are drafted, none published, no tags.

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

- **Chapter 06 is acceptance-complete at code level, not demonstrated
  live** (the user's decision after PR #27 merged).
  - First step: PR #26 from `series/06-agent-boundaries`, merge
    `db3d0e9`, fourteenth CI deployment. Instructions inside evidence
    can't dismiss an incident, add a tool, approve or trigger a recovery,
    or clear a failed gate. A regex flag, `instruction_in_evidence`,
    makes such text a severe signal; it's easy to evade and says so.
  - Second step: PR #27 from `feat/06-audit-and-prohibited`, merge
    `cb709bb`, fifteenth CI deployment: `Files: 83 uploaded, 0 deleted`,
    `Resources: 0 created, 0 changed, 0 deleted, 8 unchanged`. An audit
    record of routing decisions (written only when the caller passes a
    log; nothing forces one), a prohibited-action rule, and `re.DOTALL`.
  - The rule: writes outside the incident log are prohibited, except
    `replay_batch` and `restore_lead_invalid_rate`, and those only with a
    matching, unused approval (chapter 04).
  - The honest failure analysis is written in the chapter doc, based on
    fakes. The LinkedIn draft is there too, unpublished.
  - Only fakes exist. No real model has seen instruction text, and
    nothing has touched the real tables.

  See [chapters/06-rules-of-command.md](chapters/06-rules-of-command.md#closing-decision)
  and [known-gaps.md](known-gaps.md#chapter-06s-boundaries-are-enforced-by-fakes-names-and-a-local-file).

- **Chapter 07 is in progress on `series/07-full-demo`, not merged**
  (PR #29, open). The user chose option 1: no new live runs.
  - `scripts/full_demo.py` runs chapter 02's fault case (leads at 32.8%)
    through every control, locally, with fakes: gate refuses, rules-only
    routing flags it severe, incident saved before the first model call,
    three read-only tools, a cited report, approvals, an approved restore
    and replay with no duplicates, then h07 and a prohibited export
    refused. Deterministic; prints only counts, codes and hashes.
    `tests/test_full_demo.py` adds 10 tests: **372 pass on the branch**.
  - It lives in `scripts/`, outside the bundle's paths, so merging it
    wouldn't deploy.
  - The chapter doc maps the criteria, records the output, says which
    steps match recorded live evidence (chapter 02 runs `330174171866992`,
    `262274593519322`, `98756061776337`; chapter 03 run
    `180753859499836` and the rejected `UPDATE`/`DELETE`) and which exist
    only with fakes, and holds the video demo script, a draft.
  - Not done: the video recording, the final architecture (the user's
    diagrams), an evaluation result (needs a real provider), redaction in
    the end-to-end path, and the composed finale.

  See [chapters/07-full-demo.md](chapters/07-full-demo.md)
  and [known-gaps.md](known-gaps.md#chapter-07s-end-to-end-run-is-local-its-live-half-is-recorded-not-rerun).

[known-gaps.md](known-gaps.md) is current.

## Branches and PRs

Remote branches: `main`, the seven retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`,
`series/04-investigate-recover`, `series/05-jev-routing`,
`series/06-agent-boundaries`), and the new chapter branch
`series/07-full-demo` (PR #29, open, not merged).
`docs/06-close-and-post` was deleted locally and on the server after it
appeared in `git branch -r --merged origin/main`. See
[branch-workflow.md](branch-workflow.md).

Local branches: `main`, `series/06-agent-boundaries` (merged; kept, no
deletion authorized), and `series/07-full-demo`.

Wait for Unit tests to pass on a PR's head before merging it, docs-only
PRs included.

## Exact next useful task

**Review chapter 07's PR #29; merging it is not authorized.** It changes no
`src/**`, `resources/**` or `databricks.yml`, so merging shouldn't deploy;
confirm on the run. After that, what's left of chapter 07 needs a decision
from the user: recording the video from the draft script, the final
architecture diagrams, and whether any part runs live (a real provider
with frozen versions and a spend cap, real executors, the real tables),
each with its own authorization.

Also not authorized: publishing any post, tagging, and the diagrams.
