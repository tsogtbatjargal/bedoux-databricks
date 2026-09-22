# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

- Chapter 02 is integrated, demonstrated live, and review-closed. Its post
  is drafted, not published. See [evidence](chapter-02-evidence.md) and
  [chapter doc](chapters/02-quality-gate.md).
- Chapter 01's post is now also drafted, not published. See
  [chapter doc](chapters/01-know-your-platform.md)'s "LinkedIn draft"
  section.
- Chapter 03 is integrated (PR #6, merge `569c03d`), **not acceptance-complete**.
  `src/bedoux/evidence.py` implements recursive redaction, sensitive-copy checks,
  and canary checks. No production caller or model transport exists. Tests
  establish fixture behavior, not prevention of a real external call.
  See [acceptance mapping](chapters/03-protect-evidence.md#roadmap-acceptance-mapping).
  Its post is deliberately not drafted — the doc's own "Post draft" section
  says why (not acceptance-complete; the material reads better once a call
  site exists).
- Last recorded workspace verification: fourth CI deployment, normal
  `bedoux_lead_invalid_rate=0.02`, unchanged pipeline IDs, one analytics job,
  Bronze → Silver → gate → Gold, unchanged Gold digests, plus a fresh
  read-only re-observation this session confirming the same (see
  [live-verification.md](live-verification.md), section 3). Prior checks and
  review history are preserved in
  [the archived handoff](handoff-2026-09-22-archive.md).
- Chapters 04–07 remain planned; **chapter 04 was not started this
  session**, per instruction. Jev is optional; no provider/budget has been
  selected for runtime calls. AWS remains deferred.

## This session: three PRs, in order, none merged

1. **PR #7** (`series/00-claude-efficiency` → `main`): commits the
   in-flight workflow-prep work found at session start — this compact
   handoff format, [the implementation brief](claude-implementation.md),
   the Jev/TypeSafe evaluation, `agent-setup.md`'s pointer, and the
   restored architecture SVG. One correction made before committing: the
   brief's chapter-04 invocation was deferred out of "exact next task" per
   the user's decision to defer chapter 04.
2. **PR #8** (`series/03-evidence-leak-fix` → `main`): fixes the leak the
   brief's assessment found — `evaluate_evidence_gate`'s problem strings
   embedded the leaked secret verbatim. Recorded as "Review findings,
   round 3" in [chapters/03-protect-evidence.md](chapters/03-protect-evidence.md) —
   the third time in this chapter that a control checked itself or leaked
   through its own reporting. 125 tests on that branch (121 + 4). **Touches
   `src/bedoux/evidence.py`; merging deploys — the project's fifth
   deployment.**
3. **PR #9** (`series/docs-alignment` → `series/00-claude-efficiency`,
   since PR #7 hadn't merged when this round started — confirmed with the
   user before branching): aligns `live-verification.md` (stale
   "not demonstrated" header and starting-state section corrected, with a
   fresh re-observation), `README.md` (per-chapter build status replacing
   the stale "all planned" framing), `known-gaps.md` (three new chapter 03
   entries), and drafts chapter 01's post. **Docs only, no code, no bundle
   path** — 121 tests unchanged on this branch (round 2's leak fix isn't
   present here; it lives on PR #8's separate branch from `main`).

None of the three are merged. Merge order isn't fixed by dependency except
that PR #9 targets PR #7's branch, so PR #7 should land (or be rebased
around) before PR #9 can merge to `main` cleanly; PR #8 is independent
(based on `main`) and can merge on its own schedule.

## Prior work folded into PR #7 (full detail in Git log, not repeated here)

Workflow-prep round (2026-09-22): the Claude implementation brief, Jev/
TypeSafe evaluation, this compact handoff format, and CLAUDE.md's
compaction guidance. The same inspection that produced the brief is what
found the problem-string leak PR #8 fixes.

Architecture SVG round (2026-09-22): `docs/architecture-context.svg`
restored to the detailed diagram with the TPC-H section removed, per prior
user direction; checked against `resources/bedoux_jobs.yml`/`quality.py`/
`gate_check.py`/the Track 2 contract, rendered and visually inspected. A
refreshed 1800×1600 PNG export exists in the user's external content
folder (not this repo).

## Checks and remaining limits

`uv run --locked python -m pytest -q`: **121 passed** on this branch
(`series/docs-alignment`, based on PR #7's branch — round 2's leak fix
lives on PR #8's separate branch and isn't present here). `git diff
--check` clean; every markdown link added or edited this session resolves
(checked programmatically against actual headings, not by eye).

These tests do not execute Spark or prove IAM, live replay, or provider
behavior. [known-gaps.md](known-gaps.md) is current as of this session:
manual durable incident evidence, client/campaign dedup ties, unexercised
conservation failure paths, CI credential expiry, no caller of
`evaluate_evidence_gate` exists, the sensitive-value check's 8-character/
string-only narrowing (concrete miss: a 7-character password copied
verbatim), and freeform sensitive text being inherently invisible to
`evidence.py`.

## Exact next useful task

Three PRs are open (see above); **none should be merged without the user's
go-ahead**, per this session's constraints. In rough dependency order:

1. Decide PR #7's fate — it's the base PR #9 branches from.
2. Merge PR #8 (leak fix) whenever convenient — independent of the other
   two, deploys on merge (project's fifth).
3. Merge PR #9 (docs alignment) once its base (PR #7) has landed.

After all three: chapter 04 remains the only substantive open door, and it
still needs its own explicit authorization — [the implementation
brief](claude-implementation.md) is a prepared plan, not standing
permission. No API account is needed before that authorization. Publishing
chapters 01 or 02 remains separate and unrequested.
