# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

Chapters 00–03 are integrated into `main`. **Chapter 04 has started** on
`series/04-investigate-recover`: its first increment is implemented and
unit-tested, with an open PR, not merged and not deployed (see "Chapter 04,"
below). Chapter 02 is demonstrated live
and its post is drafted, not published — see
[chapter-02-evidence.md](chapter-02-evidence.md) and
[chapters/02-quality-gate.md](chapters/02-quality-gate.md). Chapter 01's post
is also drafted, not published — see
[chapters/01-know-your-platform.md](chapters/01-know-your-platform.md).
Chapter 03 is integrated but **not acceptance-complete**:
`evaluate_evidence_gate` has a real caller (`evidence_log.gate_and_redact`,
guarding the append-only evidence log below), but that's a durable Delta
write, not the network egress the roadmap criterion means — "a failed check
prevents the external call" gets its control flow from chapter 04's
`model_call.call_model`, tested against a fake provider only. See
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#roadmap-acceptance-mapping).

**Chapter 03's append-only evidence log is merged, deployed, and now fully
confirmed live**, including the negative mutation test
(`src/bedoux/evidence_log.py`, pure, no Spark, plus a thin writer in
`gate_check.py`; PR #11, merge `7856b78`, sixth CI deployment; PR #14,
merge `028b27e`, seventh, a docstring-only fix). It appends at least one
row to `workspace.bedoux_silver.gate_evidence_log` every run, pass or
fail, before the gate's own raise (a retry appends more than one — see
below). Four `dev` runs confirmed it live:
`649621694823474` and `102698121895581` (passing, default
`bedoux_lead_invalid_rate=0.02`), `180753859499836` (failing, under a
separately authorized fault deploy at `0.30` — leads breached at 32.8%
quarantine, gate correctly withheld Gold, and the row's `problems` held
its first-ever non-empty value), and `793561848702599` (restore run,
confirmed `0.02` actually redeployed before running, not assumed). A
follow-on negative test then targeted two real, existing rows with an
`UPDATE` and a `DELETE`: both failed with
`[DELTA_CANNOT_MODIFY_APPEND_ONLY]`, and a full re-`SELECT` confirmed
every row unchanged. Raw evidence in
[chapter-03-evidence.md](chapter-03-evidence.md).

**One confirmed limitation, predicted at design time, not fixed:** a
job-level task retry re-runs `gate_check.py` with the same `run_start_ms`,
so a retried failing run appends two evidence rows for one run, not one.
Append-only guards mutation, not duplication. See
[known-gaps.md](known-gaps.md#durable-incident-evidence-is-manual).

Both diagrams (`architecture.drawio`, `architecture-context.svg`) now show
the evidence-log sub-step inside `bedoux_gate_task`, matching
`architecture.md` and `sentinel/README.md`'s text — no diagram/doc
disagreement remains (PR #15, merge `663e280`).

Docs across the repo (`architecture.md`, `sentinel/README.md`,
`roadmap.md`, `known-gaps.md`, `live-verification.md`,
`contracts-bedoux.md`, `chapters/03-protect-evidence.md`) were swept and
corrected to match the live results — none still say "not yet confirmed,"
"still unobserved," or claim `gate_evidence_log`'s grain is exactly one
row per job run (`contracts-bedoux.md` said so; PR #16 corrected it to
"at least one," matching the confirmed retry-duplicate behavior). Chapter
03's LinkedIn post is now drafted (not published) in
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#linkedin-draft).

## Chapter 04

First increment on `series/04-investigate-recover`: the guarded model-call
path, `src/bedoux/model_call.py`. `call_model` runs `evaluate_evidence_gate`
and returns `blocked` before touching the provider if it fails, re-checks
the exact serialized payload, calls an injected provider once, and maps
timeouts, provider errors, and malformed responses to `pending` with fixed
reason codes. The only provider is a test fake; nothing in the job calls
this module; no evidence has left the process. 22 new tests
(`tests/test_model_call.py`), **171 total**. Full design and what the tests
do and don't prove: [chapters/04-investigate-recover.md](chapters/04-investigate-recover.md).

The same branch fixes `src/bedoux/gate_check.py`'s stale "Writes one row
every run" comment and `evaluate_evidence_gate`'s docstring, so **merging it
is a `src/**` change and deploys** (both edits are comments/docstrings; the
new module isn't referenced by any job). Merging is a separate decision.

Not updated on purpose: the diagrams (the user updates them by hand), and
chapter 03's unpublished LinkedIn draft, which still says "no model-call
site exists yet" — true from chapter 03's point of view, and worth revising
before that post is ever published.

`main` is clean at `0952961`, **149 tests pass** there. [known-gaps.md](known-gaps.md) is
current, including the confirmed evidence-log entry, the retry-duplicate
limitation above, and an entry recording that chapter 04's runtime model
provider is a deliberate scope decision — deferred to the post/video,
not an oversight, because a live provider would incur real API spend for
no additional demonstrated capability beyond what a fake provider already
proves; the plan is to show the boundary holding under a fake provider's
timeouts and malformed responses, not to prove a real vendor's API works.
[The implementation brief](claude-implementation.md) is a prepared plan
for chapter 04, not authorization to start it — and is itself marked as a
dated, expiring artifact (see [README.md](README.md)'s "Docs lifecycle").

Branches besides `origin/main`: the four retained chapter branches
(`series/00-introduction`, `series/01-know-your-platform`,
`series/02-quality-gate`, `series/03-protect-evidence`); the new chapter
branch `series/04-investigate-recover` (retained permanently, like the
others); and merged working branches kept after their PRs, deletable once
verified merged — `chore/evidence-docstring-fix` (PR #14),
`docs/evidence-log-diagrams` (PR #15), `docs/chapter-03-live-close-out`
(PR #16), `docs/grain-alignment` (PR #17). See
[branch-workflow.md](branch-workflow.md).

**One open PR:** chapter 04's first increment, from
`series/04-investigate-recover`. Not merged — merging deploys.

## Exact next useful task

Review chapter 04's open PR, then decide whether to merge it (a
deployment). After that, the next increment — each needs its own
authorization: persist an incident before the model call so `pending`
survives a restart, validate a report's evidence citations, and add a
bounded read-only tool set with recovery denied by code. The runtime model
provider stays deliberately unbuilt (see `known-gaps.md`), covered in the
post/video instead.
