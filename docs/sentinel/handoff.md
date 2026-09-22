# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–03 are integrated into `main` (merge commits `442c7a8`, `f8ae89d`/
`b62bffa`/`1b0694f`, `569c03d`, `0f96632`/`a4db223`/`b7e35cf`). Chapter 02 is
demonstrated live and its post is drafted, not published — see
[chapter-02-evidence.md](chapter-02-evidence.md) and
[chapters/02-quality-gate.md](chapters/02-quality-gate.md). Chapter 01's post
is also drafted, not published — see
[chapters/01-know-your-platform.md](chapters/01-know-your-platform.md).
Chapter 03 is integrated but **not acceptance-complete**: `evaluate_evidence_gate`
has no caller anywhere in this project, so "a failed check prevents the
external call" is structurally blocked — see
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#roadmap-acceptance-mapping).
Its post is deliberately not drafted, for the same reason.

`main` is clean, 125 tests pass, no bundle-path drift from the fifth CI
deployment (verified against the workspace — see
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md)'s "Review
findings, round 3"). [known-gaps.md](known-gaps.md) is current, including
chapter 03's three entries. [The implementation brief](claude-implementation.md)
is a prepared plan for chapter 04, not authorization to start it — and is
itself marked as a dated, expiring artifact (see [README.md](README.md)'s
"Docs lifecycle").

Pre-chapter-04 cleanup is done (PR #10, merge `cb10d0d`, docs only, no
deploy): the two architecture diagrams' independent-maintenance split is
documented in README.md; [branch-workflow.md](branch-workflow.md) now
distinguishes archival chapter branches from ordinary working branches; the
five approved working branches (`series/00-claude-efficiency`,
`series/02-post-draft`, `series/02-quality-gate-fixes`,
`series/03-evidence-leak-fix`, `series/docs-alignment`) are deleted from the
remote, each verified as an ancestor of `origin/main` first. `git branch -r`
now shows exactly `origin/main` plus the four retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`).

A docs-currency pass is on `chore/docs-currency` (PR #12, open, not merged,
docs only — no bundle path touched, CI skips Validate/Deploy): records the
Track 1 keep decision (README.md, `contracts.md#track-1-stays` — kept for
its Auto CDC comparison point, flagged as an extraction candidate later,
with the `databricks.yml`-includes-`resources/*.yml` constraint that makes
removing its resource files a workspace-destroying operation, not a code
move); brings `architecture.md` current (adds `bedoux_gate_task` to the
diagram, states `evidence.py`'s missing call site is a deliberate omission
from it); rewrites README's Sentinel section to present tense; fixes
`roadmap.md`'s stale "121 tests" and missing PR #8 reference, and a
mislabeled test count in `chapters/03-protect-evidence.md` (24 tests in
`test_evidence.py`, not 125 — that was the repo-wide total); and re-checks
`ai_rules.md` (current, unchanged) and `genie.md` (flagged the CLI version
its subcommands were last verified against is behind `mise.toml`'s current
pin, not re-verified since).

**Separately, chapter 03's append-only evidence log is on
`series/03-evidence-log` (PR #11, open, not merged, touches `src/**` — merging
deploys).** See that PR/branch for details; not repeated here.

## Exact next useful task

**Merge PR #12 (docs, no deploy) and PR #11 (deploys) when authorized, run
PR #11's live demonstration per `live-verification.md` section 6, then
chapter 04 is the next substantive work and needs its own explicit
authorization before any of it starts.**
