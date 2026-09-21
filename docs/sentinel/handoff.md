# Session handoff

Updated: 2026-09-21. Chapter 01 is integrated into `main`; chapter 02 is on
`series/02-quality-gate`, pushed, with [PR #3](https://github.com/tsogtbatjargal/bedoux-databricks/pull/3)
open and **not merged** — its `Validate bundle` check is failing for a
missing-CI-credentials reason, not a code defect (see "PR #3 opened" below).
Verify the checkout before working; this page records context, not
permission for external actions.

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
- `series/02-quality-gate` (branched from `main` at `3bdee7e`) is pushed and
  open as PR #3 at head `29adace`, three commits ahead of `main`. **Not
  merged** — `Validate bundle` fails in CI for a missing-credentials reason;
  see "PR #3 opened" below. This is the first chapter that changes
  `src/bedoux/*.py`.
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

## Chapter 02 — gate redesigned after a second review

PR #3 stays open. The first gate implementation put the decision inside Gold's
DLT dataset functions; a second review found four defects with one root cause,
and the gate was redesigned as an orchestration step.

**The four defects, all in the old `gold.py`:**

1. `.count()` ran inside a dataset definition — a driver-side action Databricks
   warns against in declarative dataset functions.
2. `_publish_or_withhold` read the Gold table it was defining.
3. A failing gate on a first-ever run published the fresh, rejected data,
   because there was no previous version to fall back to.
4. Fail-open evidence handling: a source with no `gate_status` row passed, and
   a null `gate_passed` passed too (`~NULL` is `NULL`, so the filter dropped it).

**The replacement.** `bedoux_gate_task`, a notebook task running
`src/bedoux/gate_check.py`, sits between `bedoux_silver_task` and
`bedoux_gold_task`. It collects `gate_status`, calls the new pure
`quality.evaluate_gate`, and raises on failure — so the Gold task never starts.
`gold.py` now has no gate logic and each table just returns its result.
Because it is ordinary job code rather than a dataset definition, the
imperative check is legal there.

Each defect closes structurally, not by patching: there is no `.count()` in a
dataset function because there is no gate code in `gold.py`; nothing reads a
Gold table, because withholding means not running the task; a first-run failure
creates no Gold table at all; and `evaluate_gate` is fail-closed — missing,
duplicated, null, or stale evidence all withhold.

**Run binding.** `gate_status` now carries `_computed_ts`, and the task receives
`{{job.start_time.iso_datetime}}`. Evidence computed before this run started is
rejected, so a leftover row cannot authorize publishing a different batch.

**Tradeoff, deliberate:** Gold is one pipeline, so one task, so the gate is now
whole-Gold rather than per-table. A `leads` failure also withholds
`gold_ogi_ops_health`, which does not depend on `leads`. Keeping per-table
precision would mean either gate logic back inside dataset functions (the
unsupported thing this removed) or splitting Gold into several pipelines
(discouraged by Free Edition's one-active-pipeline-per-type limit, and a bigger
change than this chapter warrants). Withholding too much is the safer error for
a publication gate. Contract updated accordingly.

**Known gap:** running `bedoux_gold_pipeline` directly bypasses the gate. It is
an orchestration control, not an invariant inside Gold. Belongs with chapter
06's permission work.

### Checks — all policy-level, none runtime

- `uv run --locked python -m pytest -q`: **53 passed** (was 33; 20 new in
  `tests/test_gate_policy.py`).
- New tests cover normal input, a failing gate, missing source rows, duplicate
  rows, null `gate_passed`, stale and null `_computed_ts`, first-run failure,
  non-mutation, and repeat evaluation.
- `resources/bedoux_jobs.yml` parsed and asserted: `bedoux_gold_task` depends
  on `bedoux_gate_task`, not on `bedoux_silver_task`.
- `gate_check.py` parses as valid Python and carries the
  `# Databricks notebook source` header.

**These are policy tests. They prove what the gate decides given rows. They do
not prove that Spark produces those rows, that the job graph stops Gold, that a
withheld table keeps its data, or that a `notebook_task` with `base_parameters`
runs on Free Edition serverless. Chapter 02 is implemented, not demonstrated.**

## PR #3 opened, CI observed — a real environment finding

Pushed `series/02-quality-gate` (user confirmed) and opened
[PR #3](https://github.com/tsogtbatjargal/bedoux-databricks/pull/3) into
`main` at head `29adace`. This is the first chapter branch to change
`src/bedoux/*.py`, so unlike chapters 00/01, `paths-filter` matched and
`Validate bundle` actually ran on the PR (not just `Unit tests`).

Observed CI run [`35653758420`](https://github.com/tsogtbatjargal/bedoux-databricks/actions/runs/35653758420)
(event `pull_request`, head `29adace`):

- **`Detect bundle changes`: success.**
- **`Unit tests`: success** (33 passed, same as local).
- **`Validate bundle`: failure.** `databricks bundle validate --target dev`
  exited 1 with `Error: failed during request visitor: default auth: cannot
  configure default credentials...`. The job's own log shows
  `DATABRICKS_HOST:` and `DATABRICKS_TOKEN:` both **empty** in the step's
  env. Confirmed the root cause directly: `gh secret list` on this repo
  returns **zero configured secrets** — `DATABRICKS_HOST`/`DATABRICKS_TOKEN`
  were never set up as GitHub Actions secrets on this repository at all, not
  a permissions or expiry problem. This is the same "no live Databricks
  access" limitation every chapter so far has recorded locally
  (`which databricks`, no `~/.databrickscfg`) — it turns out to also be true
  in CI, not just this local dev environment. **Not a code defect and not
  worked around**; reporting it honestly per instruction.
- **`Deploy bundle`: skipped** — correctly: PRs never deploy regardless of
  `Validate bundle`'s outcome, and it would have been blocked by the failed
  dependency anyway.
- `gh pr view 3`: `mergeable: MERGEABLE`, `mergeStateStatus: UNSTABLE` (the
  failing `Validate bundle` check).

**Not merged.** Merging this branch would deploy the bundle to the `dev`
target on the resulting `main` push — but `Validate bundle` has never
succeeded, and would fail on `main` too for the same credential reason.
Stopped here per instruction to report the PR's `Validate bundle` result
before any merge decision.

## Next task

This session's task is done pending the user's decision. Whoever picks this
up next needs the user to decide one of:

- Configure `DATABRICKS_HOST`/`DATABRICKS_TOKEN` as GitHub Actions secrets
  (a real workspace-credential decision, not something to do
  unprompted) and re-run `Validate bundle` on PR #3 before considering merge.
- Explicitly accept merging without a passing `Validate bundle` (would still
  fail identically on the `main` push and block `Deploy bundle` there too —
  not a merge that would actually deploy anything, just a merge of code that
  has never been validated against a live workspace).
- Leave PR #3 open, unmerged, until workspace access exists.

Whichever the user chooses, do not add or change repository secrets, and do
not merge on your own initiative — both are explicitly the user's decision
to make. `series/02-quality-gate` is retained (pushed, not deleted); nothing
in `docs/sentinel/branch-workflow.md`'s local-cleanup checklist applies yet
since nothing has merged.

Separately, and not blocking chapter 02 or 03: chapters 00 and 01's LinkedIn
posts are still undrafted. Drafting them is a `sentinel-story` task, distinct
from pipeline/doc implementation.

AWS extension-chapter context is unchanged and recorded above under
"Decisions to preserve".
