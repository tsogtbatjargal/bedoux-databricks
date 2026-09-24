# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–03 are integrated into `main`, and so are chapter 04's first
four increments; the fifth is an open PR. **249 tests pass on `main`, 273
on `feat/04-recovery-approval`.** Posts for chapters 00–03 are drafted,
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
- **Chapter 04, third increment** (PR #21, merge `8f9d1f5`, tenth CI
  deployment: `Files: 72 uploaded, 0 deleted`, `Resources: 0 created, 0
  changed, 0 deleted, 8 unchanged`). A report needs a non-empty `citations`
  list of paths like `rows[0].stage`, each resolving to non-redacted
  evidence in the payload the provider was sent; otherwise it's `pending`
  (`no_citations`, `unresolved_citation`, `redacted_citation` — also for
  a container whose values are all redacted). `send_payload` itself
  refuses a report echoing the canary or a secret (`report_leak`), using
  sensitive values `prepare_payload` keeps in memory on the
  `CheckedPayload`, so no caller gets an unscreened report. A checked
  report is now stored in the incident log. 28 new tests. Citation checks prove a
  citation *exists* in what was sent, not that it supports the claim.
- **Chapter 04, fourth increment** (PR #22, merge `3fa08a9`, eleventh CI
  deployment: `Files: 74 uploaded, 0 deleted`, `Resources: 0 created, 0
  changed, 0 deleted, 8 unchanged`). `src/bedoux/tools.py`: three read-only
  tools over in-memory synthetic fixtures (`read_gate_status`,
  `read_quarantine_sample`, `read_evidence_log`). A fixed `ALLOWED_TOOLS`
  frozenset decides what runs, and anything else, recovery included, is
  refused (`tool_not_allowed`), never executed, and recorded. Each tool
  result goes back through `prepare_payload` before it's sent, so a
  result carrying the canary or a secret is blocked
  (`tool_result_blocked`). A sample `limit` outside 1–5 is refused
  (`invalid_tool_args`). The loop allows at most 3 tool calls, then
  stops `pending` (`tool_limit_reached`). Each call is a `tool_call` event
  in the incident log, holding only the checked payload. 25 new tests.
  No real model has ever chosen a tool.
- **Chapter 04, fifth increment: open PR from
  `feat/04-recovery-approval`, not merged** (merging deploys).
  - `src/bedoux/recovery.py` defines "the defined approval." There's a
    fixed list of two actions, and executors are injected; only
    recording test fakes exist.
  - A human-side `approve_recovery` names the approver and binds one
    incident, one action, and the SHA-256 of the incident's current
    payload, for a single use. `execute_recovery` refuses anything else
    with a fixed code and zero executor calls. A model's
    `proposed_recovery` never counts as approval.
  - `recovery_started` is fsynced before execution, so a retry runs at
    most once.
  - `src/bedoux/replay.py` merges accepted leads keyed on `lead_id`, so
    replaying a batch twice leaves each lead once. This is offline and
    in memory, not Spark or DLT.
  - 24 new tests, each rule mutation-checked. Chapter 03's
    `gate_evidence_log` retry duplicate is a different gap and still
    open.
- **Chapter 04 acceptance** is mapped per criterion in
  [chapters/04-investigate-recover.md](chapters/04-investigate-recover.md#roadmap-acceptance-mapping).
  If the fifth increment merges, five criteria are met at code level and
  the offline/live separation holds trivially. The business metric is
  deliberately deferred with the live run. None is met live.

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
`series/04-investigate-recover`); and the working branch
`feat/04-recovery-approval` (the open PR). The local
`docs/04-acceptance-mapping`, which had no commits beyond `main` and was
never pushed, was deleted with `git branch -d`. See
[branch-workflow.md](branch-workflow.md).

Local branches: `main`, `series/04-investigate-recover`, and
`feat/04-recovery-approval`.

**One open PR:** chapter 04's fifth increment, from
`feat/04-recovery-approval`. Not merged — merging deploys.

## Exact next useful task

Review the recovery-approval PR and decide whether to merge it (a
deployment). Then the user decides whether chapter 04 closes, using the
acceptance mapping. The remaining items, none authorized:
- Live run: deliberately deferred, since it needs a real provider.
- Before/after business metric: deferred with the live run.
- Real-table reads and a real recovery executor: not built. Both are
  scope, not acceptance criteria.
