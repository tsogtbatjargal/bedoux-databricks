# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–03 are integrated into `main`. Chapter 02 is demonstrated live
and its post is drafted, not published — see
[chapter-02-evidence.md](chapter-02-evidence.md) and
[chapters/02-quality-gate.md](chapters/02-quality-gate.md). Chapter 01's post
is also drafted, not published — see
[chapters/01-know-your-platform.md](chapters/01-know-your-platform.md).
Chapter 03 is integrated but **not acceptance-complete**:
`evaluate_evidence_gate` now has a real caller (`evidence_log.gate_and_redact`,
guarding the append-only evidence log below), but that's a durable Delta
write, not the network egress the roadmap criterion means — "a failed check
prevents the external call" is still structurally blocked until chapter 04
builds an actual model-call site. See
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#roadmap-acceptance-mapping).
Its post is deliberately not drafted, for the same reason.

**Chapter 03's append-only evidence log is merged** (PR #11, merge commit
`7856b78`, the project's sixth CI deployment): `src/bedoux/evidence_log.py`
(pure, no Spark) plus a thin writer in `gate_check.py` append one row to
`workspace.bedoux_silver.gate_evidence_log` every run, pass or fail, before
the gate's own raise, so a logging bug can never withhold a healthy Gold
refresh or swallow a real failure. Table created with
`delta.appendOnly = true` — a real Delta property, implemented but **not yet
verified live**: the deploy plan showed `0 created, 0 changed, 0 deleted, 8
unchanged` (no Track 1 or Track 2 resource drift), because this change is
job/notebook code, not a `resources/` definition — the table itself gets
created the first time `bedoux_gate_task` actually runs, which hasn't
happened yet. Design, schema, and exact live-demonstration commands are in
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#append-only-evidence-log-design-this-session)
and [live-verification.md](live-verification.md#6-chapter-03-evidence-log-demonstration-not-yet-run).

**Docs-currency pass merged** (PR #12, merge commit `e5545ce`, docs only, no
deploy): records the Track 1 keep decision (README.md,
[contracts.md#track-1-stays](../contracts.md#track-1-stays) — kept for its
Auto CDC comparison point, flagged as an extraction candidate later, with
the `databricks.yml`-includes-`resources/*.yml` constraint that makes
removing its resource files a workspace-destroying operation, not a code
move); brings `architecture.md` current; rewrites README's Sentinel section
to present tense; fixed `roadmap.md`'s stale test count and PR references.
Merging PR #11 afterward reopened some of those same numbers (see below).

`main` is clean, **149 tests pass**, no bundle-path drift from the sixth CI
deployment. [known-gaps.md](known-gaps.md) is current, including an updated
entry for the evidence log (built, not yet verified live) and a new entry
recording that chapter 04's runtime model provider is a deliberate scope
decision, deferred to the post/video, not an oversight.
[The implementation brief](claude-implementation.md) is a prepared plan for
chapter 04, not authorization to start it — and is itself marked as a
dated, expiring artifact (see [README.md](README.md)'s "Docs lifecycle").

Pre-chapter-04 branch cleanup (PR #10) is done: `git branch -r` shows
`origin/main` plus the four retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`) — see
[branch-workflow.md](branch-workflow.md) for the archival-vs-working-branch
policy this now follows.

**No open PRs.**

## Exact next useful task

**Run the chapter 03 evidence log's live demonstration** per
`live-verification.md` section 6 (deploy is already done; this is the
job-run and query steps that prove `delta.appendOnly` actually rejects a
mutation and that a row is written on both a passing and a failing run).
After that, chapter 04 is the next substantive work and needs its own
explicit authorization before any of it starts.
