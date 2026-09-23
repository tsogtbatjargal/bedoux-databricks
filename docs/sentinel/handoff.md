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

**Chapter 03's append-only evidence log is merged, deployed, and partially
demonstrated live** (`src/bedoux/evidence_log.py`, pure, no Spark, plus a
thin writer in `gate_check.py`; PR #11, merge `7856b78`, the sixth CI
deployment). It appends one row to `workspace.bedoux_silver.gate_evidence_log`
every run, pass or fail, before the gate's own raise, so a logging bug can
never withhold a healthy Gold refresh or swallow a real failure. Two `dev`
runs (`649621694823474`, `102698121895581`, default
`bedoux_lead_invalid_rate=0.02`, both passing) confirmed live: a row is
written each run with content matching `gate_status` from the same run,
`SHOW TBLPROPERTIES` shows `delta.appendOnly = true` genuinely set on the
created table, and the second run appended a second row rather than
replacing the first. Raw evidence in
[chapter-03-evidence.md](chapter-03-evidence.md). Docs across the repo
(`architecture.md`, `sentinel/README.md`, `roadmap.md`, `known-gaps.md`,
`live-verification.md`) were swept and corrected to match — none still
say "no call site" or "not deployed."

**Two chapter-03 items remain unobserved live, and both need authorization
beyond a docs session:**
1. A negative test that `delta.appendOnly` actually rejects a mutation —
   an `UPDATE`/`DELETE`/`MERGE` against `gate_evidence_log`, expected to
   fail. This is destructive SQL; running it is the user's decision, not
   a default next step.
2. A `gate_evidence_log` row from a **failing** run — both runs so far
   used the default, passing `bedoux_lead_invalid_rate=0.02`. Observing
   this needs a fault-rate deploy (`bedoux_lead_invalid_rate` above 0.02),
   the same kind of live change chapter 02's fault/restore sequence used.

Exact commands for both are in
[live-verification.md](live-verification.md#6-chapter-03-evidence-log-demonstration-partially-run).

`main` is clean, **149 tests pass**, no bundle-path drift from the sixth CI
deployment. [known-gaps.md](known-gaps.md) is current, including an updated
entry for the evidence log (built and partially run live; the negative
mutation-rejection test is the one part still unobserved) and a new entry
recording that chapter 04's runtime model provider is a deliberate scope
decision, deferred to the post/video, not an oversight.
[The implementation brief](claude-implementation.md) is a prepared plan for
chapter 04, not authorization to start it — and is itself marked as a
dated, expiring artifact (see [README.md](README.md)'s "Docs lifecycle").

Branch cleanup is current: `git branch -r` shows `origin/main` plus the
four retained chapter branches (`series/00-introduction`,
`series/01-know-your-platform`, `series/02-quality-gate`,
`series/03-protect-evidence`) and nothing else — see
[branch-workflow.md](branch-workflow.md) for the archival-vs-working-branch
policy this follows. `chore/docs-currency`, `series/03-evidence-log`, and
`chore/evidence-log-demo` were all working branches, merged and deleted.

**No open PRs.**

## Exact next useful task

Either of the two chapter-03 items above (mutation-rejection test or a
failing-run log row), each needing its own explicit authorization for the
destructive SQL or fault-rate deploy it requires — see "Current state."
After those, chapter 04 is the next substantive work and needs its own
explicit authorization before any of it starts.
