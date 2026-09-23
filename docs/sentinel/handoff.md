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
`evaluate_evidence_gate` has a real caller (`evidence_log.gate_and_redact`,
guarding the append-only evidence log below), but that's a durable Delta
write, not the network egress the roadmap criterion means — "a failed check
prevents the external call" is still structurally blocked until chapter 04
builds an actual model-call site. See
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

`main` is clean, **149 tests pass**. [known-gaps.md](known-gaps.md) is
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
`series/02-quality-gate`, `series/03-protect-evidence`), plus
`docs/chapter-03-live-close-out` — this session's PR branch (PR #16,
merge `92e6d15`), kept per policy after merging, deletable once verified
merged — see [branch-workflow.md](branch-workflow.md).

**No open PRs.**

**One stale source comment, deliberately not fixed yet:**
`src/bedoux/gate_check.py:86` says the evidence-log block "Writes one row
every run" — Run 3 disproved that (a task retry writes a second row with
the same `run_start_ms`). It's a comment only, but it's a `src/**` change,
so fixing it triggers a CI deployment and needs its own authorization. The
correct wording is in `contracts-bedoux.md`'s `gate_evidence_log` entry.

## Exact next useful task

Chapter 04 ("Investigate and recover") is the next substantive chapter
and needs its own explicit authorization before any of it starts —
including the scope decision, already recorded in `known-gaps.md`, to
keep its runtime model provider out of live implementation and cover it
in the post/video instead.
