# Session handoff

This file records current state and the next task, not permission to merge,
deploy, run jobs, change secrets, bind resources, or publish. Inspect Git
before continuing. Detailed session-by-session history lives in Git log and
each chapter's own doc, not here.

## Current state

- **Chapter 02 is fully closed out**: implemented, demonstrated live (fault →
  restore → replay, one uninterrupted `dev` session), review-closed (a real
  campaign-reference gap and terminology fixes, PR #4), and now has a
  drafted-not-published post (PR #5, merge commit `1b0694f` — the project's
  **third** CI deployment, verified directly against the workspace: same
  `job_id` `133273744478391` and all three `bedoux_*_pipeline` IDs, unchanged
  job graph Bronze → Silver → gate → Gold, Bronze's config still
  `bedoux.lead_invalid_rate: 0.02`, all three Gold digests byte-for-byte
  unchanged from the reference values in `chapter-02-evidence.md`). Full
  history, incident writeup, and the "LinkedIn draft"/"Before posting"
  sections are in
  [chapters/02-quality-gate.md](chapters/02-quality-gate.md); durable
  per-stage evidence in [chapter-02-evidence.md](chapter-02-evidence.md);
  deferred structural gaps in [known-gaps.md](known-gaps.md) (including the
  CI PAT's 2026-12-20 expiry and its misleading auth-failure symptom, and the
  `clients_clean`/`campaigns_clean` dedup-tie finding). **Not published**: no
  `post/02-quality-gate` tag, no publication-register row — both need
  separate authorization from drafting.
- `dev` is deployed at the normal `bedoux_lead_invalid_rate=0.02`. `main`,
  `series/02-quality-gate`, `series/02-quality-gate-fixes`, and
  `series/02-post-draft` were all merged/cleaned up per
  `branch-workflow.md` (local branches deleted with `git branch -d` only
  after remote-tip-match/ancestor checks; all remote branches retained).
- **Chapter 03 ("Protect what matters") is scoped and its redaction/canary
  half is implemented and tested, not merged.** Branch
  `series/03-protect-evidence`, PR #6 open (from integrated `main`). Design
  and scope in [chapters/03-protect-evidence.md](chapters/03-protect-evidence.md).
  Built across two rounds this session, pure Python, no Spark/`dlt`/network
  (same pattern as `quality.py`):
  - `src/bedoux/evidence.py`: `FICTIONAL_SENSITIVE_LEAD` (an isolated
    fixture, not wired into `generator.py` or any real table), a
    `CANARY_MARKER` planted in a non-sensitive-looking field (`notes`),
    `redact_evidence_packet` (recursively strips known sensitive field
    names through dicts/lists/tuples), `contains_canary` (recursive scan of
    both keys and values), and `evaluate_evidence_gate` (fail-closed: two
    independent checks — a sensitive-value leak check against the original
    pre-redaction input, and a canary scan of the redacted result).
  - **A pre-merge review round found and fixed three confirmed defects**
    (each reproduced by execution first, each pinned by a test that failed
    before the fix): (1) redaction was shallow while canary detection was
    already recursive, so a sensitive field nested under the realistic
    `{"rows": [row, ...]}` packet shape was neither redacted nor blocked —
    **the same shape as chapter 02's first review finding, a correct
    control pointed at the wrong input scope**; (2) the canary scan checked
    values but not keys; (3) the "sensitive field survived redaction" check
    validated `redact_evidence_packet`'s own output against itself and
    could never fire — **the same shape as chapter 02's original incident,
    a check deriving its verdict from the same source as the thing it
    checks**. Full writeup with reproduction commands in the chapter doc's
    "Review findings, round 1" section. Explicitly lower severity than
    chapter 02's: caught pre-merge in code nothing calls yet, not a live
    incident.
  - `tests/test_evidence.py`: 15 tests total (9 from the first round, 6
    pinning the three defects above), including the positive case that
    non-sensitive evidence still survives redaction at nesting depth.
  - **A further gap noticed, not fixed**: `evidence.py` can only recognize
    sensitive content under a known field name, carrying the literal
    canary, or copied from a recognized field elsewhere in the same
    packet. Freeform sensitive text with none of those properties is
    invisible to it — inherent to the rule-based approach, not part of
    this round's fix.
  - **Deliberately not built this session**: no wiring into
    `bedoux_analytics_job`, no `resources/`/`databricks.yml` changes, no
    outbound model call anywhere in the project, and — separately —
    **no append-only durable-evidence-log mechanism**. `known-gaps.md`'s
    "Durable incident evidence is manual" entry names chapter 03 as that
    gap's owner; this session closes only the redaction/canary half, not
    that gap. See the chapter doc's "Does this close the durable-evidence
    gap from chapter 02?" section.
  - **One decision flagged for the user, not acted on**: `evidence.py`
    sits under `src/**`, so CI's bundle filter matches it and merging PR #6
    will deploy — shipping a module nothing imports to the workspace.
    Harmless, but noted in the PR: is that intended, or should non-pipeline
    pure-Python modules live outside the bundle's `src/**` path? Not
    restructured.
  - `roadmap.md`'s chapter 03 build-status column reflects this split
    (scoped + redaction spec implemented, durable-log half not started);
    publication column untouched ("Not drafted" — accurate, nothing drafted).

## Checks and results

- `uv run --locked python -m pytest -q`: **116 passed** (101 before this
  session; +9 for `evidence.py`'s first round; +6 pinning the three
  confirmed defects). `uv lock --check` and `git diff --check` clean
  throughout.
- PR #5's CI (two runs, one per push) and the resulting `main` deploy: `Unit
  tests`/`Validate bundle`/`Deploy bundle` all green; deploy verified
  directly against the workspace (see above) — no drift, no duplicates.
- Chapter 03 work this session: unit tests only, run locally, both rounds.
  No `bundle validate`, no deploy, no job run — none were needed or
  authorized, since nothing in `resources/`/`databricks.yml`/`src/bedoux/*`
  that the job actually imports changed.

## Limitations

Structural/deferred gaps (whole-Gold not per-table withholding, freshness
not immutable batch identity, the `clients_clean`/`campaigns_clean`
dedup-tie bug, `expect_or_fail`/`conserved=false` never observed live, local
tests not executing Spark, manual incident-evidence capture — now explicitly
still open despite chapter 03's first session, see above — and CI's PAT
expiring 2026-12-20) are consolidated in [known-gaps.md](known-gaps.md).

## Exact next task

Two independent paths, not mutually exclusive:

- **Publish the chapter 02 post**, when requested: tag
  `post/02-quality-gate` at the demonstrated commit, add the
  publication-register row in `branch-workflow.md`, post the draft, record
  the public URL.
- **Continue chapter 03**: either build the append-only durable-evidence-log
  mechanism (the still-open half of the chapter's own scope, per
  `known-gaps.md`), or wire `evidence.py`'s gate into an actual call site —
  both need their own authorization and design discussion before code, per
  this chapter's own "deliberately left unbuilt" list. `series/03-protect-
  evidence` is pushed with PR #6 open, CI green (not merged); review or
  extend on that branch rather than starting a new one for continuation
  work. Before merging, resolve the flagged decision about `evidence.py`'s
  location under `src/**` (see above) — it doesn't block the merge, but it
  should be a deliberate choice, not an accident of where the file landed.

Use `sentinel-story` only when asked to draft/revise posts;
`sentinel-chapter` for chapter implementation/review. Jev remains optional;
AWS is deferred with no budget or deployment authorization.
