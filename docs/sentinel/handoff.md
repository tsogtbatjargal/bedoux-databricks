# Session handoff

Updated: 2026-09-21, after chapter 01 was integrated into `main`. Verify the
checkout before working; this page records context, not permission for
external actions.

## Current state

- Chapter 01 is integrated via merge commit `442c7a8` (PR #2), which
  fast-forwarded `main` from `66454c2`. Treat `git rev-parse main` as the
  authoritative current tip rather than any SHA recorded in this file — this
  page is a point-in-time record, not a live pointer (chapter 00's history
  below shows why that matters: this file was already wrong twice from
  hardcoded SHAs).
- Remote branch `series/01-know-your-platform` is retained at `4b23521`
  (`https://github.com/tsogtbatjargal/bedoux-databricks/tree/series/01-know-your-platform`).
  The local branch was deleted after passing every check in
  [branch workflow](branch-workflow.md): clean tree, no other worktree, remote
  tip matched local tip, and the chapter tip is an ancestor of both local and
  `origin/main`.
- Working tree clean, on `main`. Nothing tagged or posted. `deleteBranchOnMerge`
  was re-confirmed `false` immediately before this merge.
- No Sentinel runtime exists yet. Chapter 01 was a mapping/documentation
  exercise, not new pipeline behavior — no `src/bedoux` code changed.
- Chapter 01's LinkedIn post remains undrafted (drafting it is a separate task
  for `sentinel-story`, not done this session).

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

## Next task

Chapters 00 and 01 are both integrated into `main`. Start
`series/02-quality-gate` from the current tip of `main` (run `git rev-parse
main` to confirm it) when authorized. Its scope
(`docs/sentinel/roadmap.md`, "02 — Defend before damage spreads") is exactly
what chapter 01's Scenario A/B/C were written to set up: batch identity,
persistent quarantine with reasons, quality metrics, and a publication gate
decision (reject individual records vs. withhold the Gold refresh) for
malformed values, duplicate leads, and missing campaign references.

Before starting: update the roadmap's chapter 01 row from "In progress" to
integrated, and read [branch workflow](branch-workflow.md) — create the new
chapter branch from current `main`, not from a locally cached ref.

Separately, and not blocking chapter 02: chapter 01's LinkedIn post is still
undrafted. Drafting it is a `sentinel-story` task, distinct from pipeline/doc
implementation.
