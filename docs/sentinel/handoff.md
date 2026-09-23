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

**Chapter 03's append-only evidence log is merged and partially
demonstrated live** (PR #11, merge commit `7856b78`, the project's sixth
CI deployment): `src/bedoux/evidence_log.py` (pure, no Spark) plus a thin
writer in `gate_check.py` append one row to
`workspace.bedoux_silver.gate_evidence_log` every run, pass or fail, before
the gate's own raise, so a logging bug can never withhold a healthy Gold
refresh or swallow a real failure. A later session ran
`bedoux_analytics_job` twice (default `bedoux_lead_invalid_rate=0.02`, both
passing) and confirmed live: a row is written each run with content
matching `gate_status` from the same run, `SHOW TBLPROPERTIES` shows
`delta.appendOnly = true` genuinely set on the created table (not just
requested in the creation code), and the second run appended a second row
rather than replacing the first — see
[chapter-03-evidence.md](chapter-03-evidence.md) for the raw run IDs,
timestamps, and row content. **Still not observed live:** the property
actually rejecting a mutation (`UPDATE`/`DELETE`/`MERGE` — a negative test
needing destructive SQL, not run), and a `gate_evidence_log` row from a
failing run (would need a fault-rate deploy, not run). Design, schema, and
exact commands are in
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#append-only-evidence-log-design-this-session)
and [live-verification.md](live-verification.md#6-chapter-03-evidence-log-demonstration-partially-run).

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
entry for the evidence log (built and run live; the negative
mutation-rejection test is the one part still unobserved) and a new entry
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

One open PR: `chore/evidence-log-demo` (docs only — two residual stale-doc
lines fixed, plus this session's live-demonstration evidence and doc
updates).

## Exact next useful task

Two pieces of chapter 03's live demonstration remain, both requiring
explicit authorization beyond what this session had: a negative test that
`delta.appendOnly` actually rejects a mutation (destructive SQL against
`gate_evidence_log`), and a `gate_evidence_log` row from a failing run
(needs a fault-rate deploy, `bedoux_lead_invalid_rate` above 0.02).
`live-verification.md` section 6 has the exact commands for both. After
that, chapter 04 is the next substantive work and needs its own explicit
authorization before any of it starts.
