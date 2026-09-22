# Session handoff

This file records current state and the next task, not permission to merge,
deploy, run jobs, change secrets, bind resources, or publish. Inspect Git
before continuing. Detailed session-by-session history lives in Git log and
each chapter's own doc, not here.

## Current state

- **Chapter 02 is fully closed out**: implemented, demonstrated live (fault →
  restore → replay, one uninterrupted `dev` session), review-closed (a real
  campaign-reference gap and terminology fixes, PR #4), and has a
  drafted-not-published post (PR #5, merge commit `1b0694f` — the project's
  third CI deployment, verified directly against the workspace). Full
  history in [chapters/02-quality-gate.md](chapters/02-quality-gate.md);
  durable per-stage evidence in
  [chapter-02-evidence.md](chapter-02-evidence.md); deferred structural gaps
  in [known-gaps.md](known-gaps.md). **Not published**: no
  `post/02-quality-gate` tag, no publication-register row.
- **Chapter 03 ("Protect what matters") is merged and integrated into
  `main`, but not acceptance-complete.** PR #6, merge commit `569c03d` —
  the project's **fourth** CI deployment, verified directly against the
  workspace: `job_id` `133273744478391` present exactly once (no
  duplicate), all three `bedoux_*_pipeline` IDs unchanged, job graph still
  Bronze → Silver → gate → Gold, Bronze's config still
  `bedoux.lead_invalid_rate: 0.02`, all three Gold digests byte-for-byte
  unchanged from the reference values (a deploy runs nothing, so this
  confirms nothing ran). Full design and scope in
  [chapters/03-protect-evidence.md](chapters/03-protect-evidence.md).
  - Built pure Python, no Spark/`dlt`/network (same pattern as
    `quality.py`): `src/bedoux/evidence.py` — `FICTIONAL_SENSITIVE_LEAD`
    (an isolated fixture, not wired into `generator.py` or any real table),
    `CANARY_MARKER` planted in a non-sensitive-looking field (`notes`),
    `redact_evidence_packet` (recursively strips known sensitive field
    names through dicts/lists/tuples), `contains_canary` (recursive scan of
    keys and values), and `evaluate_evidence_gate` (fail-closed: a
    sensitive-value leak check against the original pre-redaction input,
    plus a canary scan of the redacted result).
  - **Three pre-merge review rounds, each reproduced by execution before
    fixing, each pinned by a test that failed first:**
    - **Round 1** (3 confirmed defects): (1) redaction was shallow while
      canary detection was already recursive, so a sensitive field nested
      under the realistic `{"rows": [row, ...]}` packet shape was neither
      redacted nor blocked — the same shape as chapter 02's first review
      finding, a correct control pointed at the wrong input scope; (2) the
      canary scan checked values but not keys; (3) the "sensitive field
      survived redaction" check validated `redact_evidence_packet`'s own
      output against itself and could never fire — the same shape as
      chapter 02's original incident, a check deriving its verdict from the
      same source as the thing it checks.
    - **Round 2** (over-blocking regression from round 1's fix): the
      independent sensitive-value check from finding 3 matched too
      broadly. `{"ssn": None, "stage": None}` blocked because `None ==
      None`; `{"password": "a", "stage": "qualified"}` blocked because `"a"`
      substring-matched ordinary text; `{"api_key": 9001, "lead_id": 9001}`
      blocked because two unrelated fields coincidentally shared a value.
      The `None` case mattered most: evidence packets come from quarantined
      rows, quarantined largely *because* a field is null, so this blocked
      nearly every realistic packet. Fixed: `_collect_sensitive_values`
      skips `None`/`""` (nothing to leak); `_value_leaked` only
      substring-matches strings of at least 8 characters (every fictional
      sensitive format here is 11+; 8 excludes short tokens without
      excluding any real one) and only checks string values at all — a
      non-string sensitive value matching another field by bare equality is
      common coincidence in small fixtures, not evidence of a copy, and
      every `SENSITIVE_FIELDS` value in this project's fixture is
      string-shaped, so this scoping costs nothing real. The genuine leak
      case (`ssn` copied into `notes`) and the canary fixture both still
      block, unchanged.
    - Full writeups with reproduction commands: chapter doc's "Review
      findings, round 1" and "Review findings, round 2" sections. Severity
      stated plainly in both: caught pre-merge, in code nothing calls yet —
      not a live incident like chapter 02's.
  - `tests/test_evidence.py`: **121 tests** (9 first pass, +6 round 1, +5
    round 2). None of the prior tests were weakened at any point; the depth
    and key-scanning fixes from round 1 were untouched by round 2.
  - **A further gap noticed, not fixed**: `evidence.py` can only recognize
    sensitive content under a known field name, carrying the literal
    canary, or copied from a recognized field elsewhere in the same
    packet. Freeform sensitive text with none of those properties is
    invisible to it — inherent to the rule-based approach.
  - **Decision made and recorded**: `evidence.py` stays at
    `src/bedoux/evidence.py`. `quality.py` is also pure Python there and is
    imported by pipeline code; keeping the package together preserves the
    import path, and shipping an unimported module to the workspace on
    deploy costs nothing. Not restructured.
  - **Not acceptance-complete — stated honestly, not marked done.** Of
    `roadmap.md`'s four chapter-03 acceptance criteria: "blocked or
    redacted" and "non-sensitive evidence survives" are met, proven by unit
    tests; "document the inspected boundary" is met. **"A failed check
    prevents the external call" is structurally blocked, not just
    undemonstrated** — no caller of `evaluate_evidence_gate` exists
    anywhere in this project, and building one is chapter 04's job runtime,
    not more chapter-03 pure-Python work. The append-only
    durable-evidence-log mechanism (`known-gaps.md`'s chapter-03
    cross-reference — not actually part of `roadmap.md`'s own acceptance
    criteria for this chapter) is deferred by choice, not blocked; nothing
    prevents building it within chapter 03's scope, it just wasn't this
    session's focus. Full mapping: chapter doc's "Roadmap acceptance
    mapping" section. `roadmap.md`'s chapter 03 row updated to match.
- `dev` is deployed at the normal `bedoux_lead_invalid_rate=0.02`. `main`,
  `series/02-quality-gate`, `series/02-quality-gate-fixes`,
  `series/02-post-draft`, and `series/03-protect-evidence` were all
  merged/cleaned up per `branch-workflow.md` (local branches deleted with
  `git branch -d` only after remote-tip-match/ancestor checks; all remote
  branches retained).
- **An observed anomaly, not a repo defect**: during this session, one push
  to `series/03-protect-evidence` had its CI trigger and PR head-SHA sync
  delayed by several minutes (no check-runs existed for the commit for a
  while, then resolved on its own). The next push synced and triggered CI
  within seconds, as normal. Before merging PR #6, `gh pr view 6 --json
  headRefOid,mergeStateStatus` was checked against `git ls-remote` and
  confirmed matching, with CI green on that exact SHA, before merging —
  worth repeating that check rather than assuming sync is instant.

## Checks and results

- `uv run --locked python -m pytest -q`: **121 passed** (101 before chapter
  03; +9, +6, +5 across the three build/review rounds). `uv lock --check`
  and `git diff --check` clean throughout.
- PR #5's CI and resulting `main` deploy (project's third): all green,
  verified against the workspace.
- PR #6's CI (three pushes, one per round) and resulting `main` deploy
  (project's **fourth**): all green; deploy verified directly against the
  workspace (see above) — no drift, no duplicates, all three Gold digests
  unchanged.
- The post-merge `roadmap.md`/chapter-doc status-honesty commit (`66315a1`,
  direct to `main`, docs-only) correctly triggered `Unit tests` only —
  `Validate`/`Deploy bundle` both skipped, as expected for a non-bundle-path
  change.

## Limitations

Structural/deferred gaps (whole-Gold not per-table withholding, freshness
not immutable batch identity, the `clients_clean`/`campaigns_clean`
dedup-tie bug, `expect_or_fail`/`conserved=false` never observed live, local
tests not executing Spark, manual incident-evidence capture — still open,
see chapter 03's "Roadmap acceptance mapping" for why — and CI's PAT
expiring 2026-12-20) are consolidated in [known-gaps.md](known-gaps.md).
Chapter 03 adds one more, specific to `evidence.py`: it can only recognize
sensitive content under a known field name, the canary, or a copy of a
recognized field's value — freeform sensitive text with none of those
properties is invisible to it.

## Exact next task

Three independent paths, not mutually exclusive; **do not start chapter 04
without explicit authorization**, even though it's the dependency the
"external call" criterion above is blocked on:

- **Publish the chapter 02 post**, when requested: tag
  `post/02-quality-gate`, add the publication-register row in
  `branch-workflow.md`, post the draft, record the public URL.
- **Close chapter 03's remaining acceptance criterion**, when authorized:
  requires chapter 04's job runtime to exist first (a call site to wire
  `evaluate_evidence_gate` into) — this is a dependency, not something
  chapter 03 can finish alone.
- **Build the append-only durable-evidence-log mechanism**, when
  authorized and scoped: still open, deferred by choice; worth deciding
  first whether it belongs in chapter 03 or as its own future chapter,
  per the chapter doc's "Roadmap acceptance mapping."

Use `sentinel-story` only when asked to draft/revise posts;
`sentinel-chapter` for chapter implementation/review. Jev remains optional;
AWS is deferred with no budget or deployment authorization.
