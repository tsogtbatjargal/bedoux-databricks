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

## Exact next useful task

**Chapter 04 is the next substantive work and needs explicit authorization
before any of it starts.** Nothing else is outstanding from chapters 00–03.
