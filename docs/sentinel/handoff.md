# Session handoff

Updated: 2026-09-21. Chapter 01 is integrated into `main`; chapter 02 is
implemented locally on `series/02-quality-gate`, not yet pushed. Verify the
checkout before working; this page records context, not permission for
external actions.

## Current state

- Chapter 01 is integrated via merge commit `442c7a8` (PR #2), which
  fast-forwarded `main` from `66454c2`. `main` has since taken three more
  docs-only commits (handoff/roadmap updates). Treat `git rev-parse main` as
  the authoritative current tip rather than any SHA recorded in this file —
  this page is a point-in-time record, not a live pointer (chapter 00's
  history below shows why that matters: this file was already wrong twice
  from hardcoded SHAs).
- Remote branch `series/01-know-your-platform` is retained at `4b23521`
  (`https://github.com/tsogtbatjargal/bedoux-databricks/tree/series/01-know-your-platform`).
  The local branch was deleted after passing every check in
  [branch workflow](branch-workflow.md): clean tree, no other worktree, remote
  tip matched local tip, and the chapter tip is an ancestor of both local and
  `origin/main`.
- The checkout is currently on `series/02-quality-gate` (branched from `main`
  at `3bdee7e`), one commit ahead (`89c334c`), working tree clean, **not
  pushed**. This is the first chapter that changes `src/bedoux/*.py` — see
  "Chapter 02" below.
- Nothing tagged or posted. `deleteBranchOnMerge` was `false` as of chapter
  01's merge.
- Chapter 00/01's LinkedIn posts remain undrafted (drafting them is a
  separate `sentinel-story` task).

## Chapter 01 — what shipped

See [`chapters/01-know-your-platform.md`](chapters/01-know-your-platform.md)
for the full content. Summary:

- A platform map (source data, trust boundaries, dataset dependencies, owners,
  business impact) distinguishing what Track 2 already implements from what
  later Sentinel chapters will add. Every claim cites the source file it was
  verified against (`src/bedoux/*.py`, `resources/bedoux_*.yml`,
  `databricks.yml`).
- Three synthetic incident scenarios (malformed lead batch, duplicate leads,
  missing campaign reference) plus a normal control, each with explicit
  inputs and expected behavior, chosen to match chapter 02's stated scope so
  chapter 02 can build directly against them.
- A capability-check table: local unit tests and code-read claims are
  **verified**; anything needing a live workspace (`bundle validate`, a live
  pipeline run, Genie queries) is **unavailable** in this environment (no
  `DATABRICKS_HOST`/`DATABRICKS_TOKEN`, no `~/.databrickscfg`, no `databricks`
  CLI installed) — an environment limit, not a choice.
- Two real discrepancies found and fixed in `docs/contracts-bedoux.md`:
  Bronze's opening line called itself "append-only" while its own rules three
  lines down said "full recompute... not append-only"; Silver called
  `leads`/`web_events`/`ops_events` "streaming tables" though `silver.py`
  implements them as batch-reading `@dlt.table`s (inherited verbatim from
  Track 1's contract, where Bronze genuinely is append-only). No pipeline code
  changed — only the contract text. A follow-up commit tightened both fixed
  sections to state current behavior plainly rather than narrate their own
  revision history (the correction itself lives in git history and in the
  chapter doc, not in the contract's prose).
- Roadmap build-status column updated: chapter 00 "Integrated into main",
  chapter 01 now integrated too — update its row before starting chapter 02.

## Integration session (this session)

- Pushed `series/01-know-your-platform` (user confirmed) and opened PR #2:
  `https://github.com/tsogtbatjargal/bedoux-databricks/pull/2`.
- Confirmed `deleteBranchOnMerge` was `false` before merging.
- Observed CI on the PR twice (once per push — the second push added a
  handoff-only commit): both runs were `Unit tests` success, `Detect bundle
  changes` success, `Validate bundle` skipped, `Deploy bundle` skipped. PR was
  `CLEAN`/`MERGEABLE`.
- Merged PR #2 with a merge commit (`gh pr merge 2 --merge`, no branch-deletion
  option passed). Merge commit `442c7a8`; `main` fast-forwarded from `66454c2`.
- Observed CI on the resulting push to `main` (run `35651242985`, event
  `push`): **`Unit tests` success, `Detect bundle changes` success, `Validate
  bundle` skipped, `Deploy bundle` skipped.** Matched the predicted no-deploy
  pattern; reported here as observed, not assumed.
- Ran the local-branch-cleanup checks from
  [branch workflow](branch-workflow.md) and all passed: clean tree, single
  worktree, `git fetch origin` then `git ls-remote --exit-code --heads origin
  refs/heads/series/01-know-your-platform` found the branch, local tip
  `4b23521` equaled the fetched remote tip, and
  `git merge-base --is-ancestor series/01-know-your-platform main`/`origin/main`
  both succeeded after fast-forwarding local `main`. Deleted the local branch
  with `git branch -d series/01-know-your-platform` (not `-D`). The remote
  branch is confirmed present at the same tip.
- Did not tag, did not draft or publish the LinkedIn post, made no paid model
  calls, did not start chapter 02.
- Pushed the local-only handoff commit `b15ba0f` directly to `main` (docs-only,
  no bundle path changed). Observed CI run `35651900611` on that push:
  **`Unit tests` success, `Detect bundle changes` success, `Validate bundle`
  skipped, `Deploy bundle` skipped** — matched the predicted no-deploy pattern.

## Decisions to preserve

Build **Bedoux Sentinel** inside this repo, extending Track 2 with fictional data.
The series is **The Art of Data Defense**: introduction, six working chapters,
and a full demo. Use concrete, natural writing with measured evidence.

**Keep remote chapter branches and stable post tags; remove merged local
chapter branches once their remote copy and integration are verified.** See
[branch workflow](branch-workflow.md) for exact checks. Chapters 00 and 01 both
followed this policy: local branches removed after verification, remote
branches and `main` remain.

Codex or Claude Code can implement; a separate session can review. Jev remains
optional and uninstalled. No runtime provider, API budget, AWS budget, or
publication date has been chosen.

### AWS extension chapter — context for later, not now

The user pointed at a separate private repo,
`/var/home/tsogtb/src/github.com/bedoux-tech/bedoux-commerce-cloud`, as a
source of reusable Terraform for the AWS extension chapter described in the
roadmap's "Shared scenario and deferred work" section:
`infra/terraform/modules/{s3-images,github-actions-oidc,iam-workload,
iam-cluster}`. That repo has **no CloudTrail module** — object-event logging
for the decoy-bucket scenario is new work, not reuse. Adapt patterns only;
copy no credentials or real data from that repo. AWS remains fully deferred:
no spend authorized, no Terraform written yet, this is a pointer for whichever
session eventually scopes that chapter.

## Chapter 00 — integration history (compressed)

Full session-by-session detail lived here before and is still in Git history
(`git log -- docs/sentinel/handoff.md`) if needed.

- Prepared on `series/00-introduction` across commits `bfd6fdd`, `b9250aa`,
  `a2231b7`, `04ded3a`, `0988d88`, `ea72679` (the last pinned
  `databricks/setup-cli` to a commit SHA and confirmed the `dorny/paths-filter`
  and `astral-sh/setup-uv` pins resolve to their intended tags via the GitHub
  API).
- Pushed, opened PR #1, confirmed `deleteBranchOnMerge` was already `false`,
  observed CI on the PR (`Unit tests` success, workspace jobs skipped — no
  bundle path changed), merged with a merge commit (`877e8d3`, no branch
  deletion), observed CI on the resulting `main` push (same no-deploy
  pattern), then ran every check in
  [branch workflow](branch-workflow.md)'s local-cleanup section before
  deleting the local branch. The remote branch (`series/00-introduction`) is
  retained at `ea72679`.
- Two further docs-only commits landed directly on `main` after the merge
  (`6be715b`, `66454c2`), each confirmed to run tests and skip workspace jobs.
  This is why "current state" sections in this file defer to
  `git rev-parse main` instead of hardcoding a SHA.

## Verification and limits (chapter 00 preparation)

- `mise exec -- uv run --locked python -m pytest -q`: 17 passed, confirmed
  independently by two separate sessions (interpreter CPython 3.11.16,
  `.venv` in this checkout both times).
- `uv lock --check`, `actionlint .github/workflows/ci.yml`, and a documentation
  check (Markdown files + relative links, TOML parse, `git diff --check`) all
  passed, also confirmed independently by two sessions.
- Local CI policy evaluation (path-filter conditions, dispatch flag
  combinations, deployment gating) was evaluated from the YAML and with Node
  before any real GitHub Actions run existed; the chapter 00 and chapter 01
  integration sessions both confirmed the actual runs matched every local
  prediction.
- No live Databricks validation, deployment, model calls, or Genie query has
  ever been run against this project. That remains true through chapter 01.

## Chapter 02 — implemented, not yet pushed

`series/02-quality-gate` (branched from `main` at `3bdee7e`, commit `89c334c`)
implements the roadmap's "02 — Defend before damage spreads" scope in full —
see [`chapters/02-quality-gate.md`](chapters/02-quality-gate.md) for the
complete design, scenario mapping, and verification table. Summary:

- **Batch identity**: Bronze stamps `leads_raw`/`web_events_raw`/
  `ops_events_raw` with `_row_id` (deterministic Python-list order) because
  `_ingest_ts` ties across every row of one table computation and can't order
  duplicates.
- **Persistent quarantine with reasons**: each fact table's Silver stage now
  produces `<source>_clean` and `<source>_quarantine` from a shared
  `_flagged` view — rejected rows carry reason codes and a
  `_quarantined_ts`; nothing is dropped silently anymore.
- **Quality metrics + publication gate**: `quality_metrics`/`gate_status`
  turn quarantine rates into a per-source `gate_passed`. `gold.py` withholds
  a table's refresh (keeps previously published content) when a source it
  depends on exceeds a 10% quarantine rate (5x the generator's ~2% baseline)
  — reject individual records by default, withhold only past that threshold.
  Documented as **not** whole-platform transactional publication.
- Covers chapter 01's Scenario A (malformed batch), B (duplicate leads), C
  (missing campaign reference), the normal control, and an explicit replay/
  idempotence test — all as pure-function unit tests in
  `tests/test_quality.py` (`quality.py` is the tested spec; `silver.py`/
  `gold.py` reimplement it as native Spark expressions, same pattern as
  `transforms.py`/`gold.py`).
- `uv sync --locked` + `uv run --locked python -m pytest -q`: **33 passed**
  (17 pre-chapter-02 + 16 in `test_quality.py`), this session.
- `docs/contracts-bedoux.md` updated to document the new Silver quarantine/
  metrics/gate tables and Gold's gate, so contract and code stay in sync.
- A related-but-unfixed finding recorded in the chapter doc: `clients_clean`/
  `campaigns_clean`'s dedup window still orders on the tied `_ingest_ts`
  (same class of bug `_row_id` fixes elsewhere) — left flagged, not fixed,
  since it wasn't in this chapter's named scope and neither table has test
  coverage to catch a regression.
- **Not verified**: the publication gate's self-referencing read
  (`spark.read.table` of a Gold table's own current state) and everything
  else requiring a live pipeline run — no `DATABRICKS_HOST`/`DATABRICKS_TOKEN`,
  no `~/.databrickscfg`, no `databricks` CLI in this environment. Same
  limitation chapter 01 recorded.
- **This chapter touches `src/` and `resources`-adjacent pipeline code for
  the first time in the series.** Per `AGENTS.md`, merging it to `main` will
  trigger `Validate bundle`/`Deploy bundle` on push (paths-filter matches
  `src/**`) — integrating it is a real deployment decision, not a docs-only
  push. Not pushed, no PR opened, nothing merged or deployed this session,
  per explicit instruction.
- Roadmap's chapter 02 row updated to "Implemented (local, unpushed)".

### Review fixes (before push)

A review of the first implementation found one correctness bug and three
spec divergences, all fixed on this branch before any push — see
[`chapters/02-quality-gate.md`](chapters/02-quality-gate.md)'s "Review fixes"
section for full detail. Summary:

1. **Gate double-counting (real bug):** `gate_status` summed
   `quality_metrics`' *exploded* per-reason counts, so a row with two reasons
   (e.g. a duplicate that's also missing `campaign_id`) inflated both the
   numerator and denominator of the quarantine rate — the reviewer's worked
   example (100 leads, 10 duplicate+null rows) computed `18.2%` instead of
   the true `10%`, which would have wrongly withheld a Gold refresh that
   should have published. Fixed by adding `_row_counts` (one row in, one row
   counted, sourced directly from the `_flagged` views) as `gate_status`'s
   basis instead; `quality_metrics`' exploded breakdown is unchanged and
   still useful, just no longer wired into the gate. Regression-tested:
   `test_gate_rate_counts_rows_not_reasons_for_multi_reason_batch`.
2. **Duplicate reason codes**: `quality.reconcile` previously gave duplicates
   only `duplicate_<key>`, discarding classification reasons; `silver.py`
   evaluates both independently and can emit both at once. Resolved in favor
   of `silver.py`'s richer union-of-reasons behavior (the double-counting bug
   above only exists because a row can carry two reasons, so collapsing to
   one would hide the bug's premise) — `quality.reconcile` rewritten to
   classify and dedup in one pass; `dedup_by_key` kept as a standalone,
   no-longer-internally-used utility.
3. **`web_events` null duration silently accepted**: `< 0` is `NULL` (not
   `True`) for a `NULL` duration. Fixed to `.isNull() | (... < 0)`, matching
   the `ops_events` pattern that already had this right.
4. **`leads` null stage silently accepted — a regression** from the
   pre-chapter-02 `expect_or_drop`, which did drop it: `~col(...).isin(...)`
   is `NULL` for a `NULL` stage. Fixed with an explicit `isNull()` check.

**Closed testing gap**: the original suite only exercised `quality.py`, so a
`quality.py`/`silver.py` divergence passed green. Reason-code string
literals in `silver.py` are now extracted into named `REASON_*` constants
(with a comment block mapping each to its `quality.py` counterpart), and
`test_silver_reason_constants_match_quality_spec` greps `silver.py`'s source
text (no Spark/`dlt` import needed) to check those constants against
`quality.py`'s reason vocabulary. This narrows but doesn't close the gap —
the Spark join/window/control-flow *logic* itself still has no automated
cross-check, same as `gold.py` vs. `transforms.py` always has had.

**Still not verified** (unchanged by the fixes): `_publish_or_withhold`
reads a Gold table's own current state while that table is being defined —
a self-referencing read pattern no local test can validate against real
DLT. No workspace credentials are available in this environment.

## Next task

When authorized: push `series/02-quality-gate`, open a PR into `main`, and
expect **both** `Unit tests` and `Validate bundle` to run this time (paths-filter
will match `src/bedoux/*.py`) — `Deploy bundle` only runs on a bundle-path push
to `main` itself, not on the PR. Flag the merge/deploy decision explicitly
before acting on it; do not merge on your own initiative. After merge, observe
the actual `main`-push CI run (expect `Deploy bundle` to actually run this
time — report what happens, not what's predicted) and follow
[branch workflow](branch-workflow.md)'s cleanup checklist before removing the
local branch.

Separately, and not blocking chapter 02 or 03: chapters 00 and 01's LinkedIn
posts are still undrafted. Drafting them is a `sentinel-story` task, distinct
from pipeline/doc implementation.

AWS extension-chapter context is unchanged and recorded above under
"Decisions to preserve".
