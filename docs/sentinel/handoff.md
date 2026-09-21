# Session handoff

Updated: 2026-09-21, after chapter 00 was integrated into `main`. Verify the
checkout before working; this page records context, not permission for external
actions.

## Current state

- Chapter 00 is integrated. `main` is at `877e8d3` (merge commit for PR #1),
  fast-forwarded from `4a04e77`.
- Remote branch `series/00-introduction` is retained at `ea72679`
  (`https://github.com/tsogtbatjargal/bedoux-databricks/tree/series/00-introduction`).
  The local branch was deleted after passing every check in
  [branch workflow](branch-workflow.md): clean tree, no other worktree, remote
  tip matched local tip, and the chapter tip is an ancestor of both local and
  `origin/main`.
- Commits merged: `bfd6fdd` (chapter 00 preparation), `b9250aa` (first CI
  separation), `a2231b7` (handoff), `04ded3a` (environment/CI/branch-policy
  cleanup), `0988d88` (cleanup commit SHA recorded), `ea72679` (pinned
  `databricks/setup-cli`, this session).
- Working tree clean, on `main`. Nothing tagged or posted. Repo setting
  `deleteBranchOnMerge` is `false`, confirmed via `gh repo view` before the
  merge.
- No Sentinel runtime exists yet. The launch post remains an unpublished draft.

## Decisions to preserve

Build **Bedoux Sentinel** inside this repo, extending Track 2 with fictional data.
The series is **The Art of Data Defense**: introduction, six working chapters,
and a full demo. Use concrete, natural writing with measured evidence.

The user's latest branch preference supersedes the old local-retention rule:
**keep remote chapter branches and stable post tags; remove merged local chapter
branches once their remote copy and integration are verified.** See
[branch workflow](branch-workflow.md) for exact checks. Chapter 00 followed this
policy: its local branch was removed after verification, its remote branch and
`main` remain.

Codex or Claude Code can implement; a separate session can review. Jev remains
optional and uninstalled. No runtime provider, API budget, AWS budget, or
publication date has been chosen.

## Cleanup completed locally

- Added `pyproject.toml`, `uv.lock`, `.python-version`, and `mise.toml`.
  uv manages the project's ignored `.venv`; Python 3.11 matches the existing
  CI interpreter choice. Removed the superseded `requirements-dev.txt`.
- Installed uv 0.12.17 through the existing mise tool manager and trusted this
  repository's mise config. No global default or shell profile was changed.
  Use `mise exec -- uv ...` if uv is not on PATH. Python and packages were
  installed into managed/project locations, not system Python.
- Local and CI checks now use `uv sync --locked` and
  `uv run --locked python -m pytest -q`.
- Replaced workflow-level path exclusions with a pinned change-detection action.
  Every PR/main push gets local tests. Only `src/**`, `resources/**`, and
  `databricks.yml` changes trigger automatic workspace validation/deployment;
  PRs never deploy. Manual dispatch validates and deploys only if opted in.
- Documentation, tests, tooling, and workflow-only changes do not deploy. The
  full preparation diff has no bundle-path changes, so its merge does not need
  the one-off deployment predicted by the previous handoff.
- Updated the development, agent, branch, and README guidance. Replaced the
  accumulated handoff history with this current summary; history remains in Git.
- Kept both tracks, their contracts, diagrams, and Genie tooling. No unrelated
  application files were identified for deletion.

## Verification and limits

- `mise exec -- uv run --locked python -m pytest -q`: **17 passed**.
- Interpreter: CPython 3.11.16; confirmed `sys.prefix != sys.base_prefix`
  and environment path is this checkout's `.venv`.
- `mise exec -- uv lock --check`: passed. Lock uses the public PyPI registry.
- `mise exec actionlint@1.7.12 -- actionlint .github/workflows/ci.yml`: passed.
  actionlint was installed in mise's managed tools for this check.
- Local CI policy evaluation passed 10 path cases, all four dispatch flag
  combinations, PR deployment exclusion, and the full preparation diff.
  Conditions were read from the YAML and evaluated with Node. This does not
  exercise the remote paths-filter action or GitHub event delivery.
- Confirmed the virtual environment and local credential/preference files are ignored.
- Documentation check: 16 project/doc Markdown files and 29 relative links passed;
  TOML parsed, local/CI uv versions matched, and `git diff --check` was clean.
- No live Databricks validation, deployment, model calls, or GitHub Actions run.

Claude Code's previous fresh session verified its import and both skill adapters.
This Codex session received both skills in its available-skill list and read and
used `sentinel-chapter`. That verifies discovery here, not a fresh standalone
Codex CLI invocation.

### Review session (Claude Code, independent)

Re-ran rather than trusted: `uv sync --locked` + `uv run --locked python -m
pytest -q` → **17 passed**; `uv lock --check` passed; interpreter CPython 3.11.16
with `sys.prefix` in this checkout's `.venv`; `actionlint` clean; 20 Markdown
files / 29 relative links with none broken; all three TOML files parse;
`git diff --check` clean. uv and mise versions match between `mise.toml` and the
workflow pin.

Independently evaluated the job gating from the YAML: nine event cases pass,
including docs PR (tests only), bundle PR (validates, never deploys), docs push
to `main` (no workspace job), bundle push (validate then deploy), and all four
dispatch flag combinations. Also confirmed the pending diff touches no
`src/**`, `resources/**`, or `databricks.yml` path, so integrating chapter 00
deploys nothing. That supersedes the one-off-deployment warning written in the
previous session, which applied to the superseded `paths-ignore` design.

Three concrete fixes applied in the cleanup commit:

- `.gitignore` did not cover mise's machine-local overrides. Added
  `mise.local.toml` and `.mise.local.toml`, matching how `.env` and
  `CLAUDE.local.md` are handled.
- `docs/architecture.drawio` still showed `pytest → validate → deploy` as an
  unconditional chain. Updated the label to the gated flow, matching
  `architecture.md`. The file is diagram source with no committed export, so
  nothing is now out of sync; XML still parses.
- `branch-workflow.md` did not mention that `workflow_dispatch` is not
  restricted to `main` — dispatching from a chapter branch with `deploy` checked
  deploys that branch. Behavior is unchanged from the old workflow and was left
  alone; it is now documented as a decision rather than a surprise.

Previously deliberately not fixed, now resolved in this session (commit
`ea72679`, before the merge): `databricks/setup-cli` is pinned to
`d76f84cea9893ce68311a1f33fb0c95af6c963b7` (tag `v1.17.0`), looked up via the
GitHub API (`gh api repos/databricks/setup-cli/tags`). The `dorny/paths-filter`
(`ceb8a2b...c5cc9d`) and `astral-sh/setup-uv` (`c771a70...ca235ff9`) SHAs,
written offline in the earlier session, were confirmed this session to resolve
exactly to their intended tags `v4` and `v9.0.0` respectively
(`gh api repos/<owner>/<repo>/git/refs/tags/<tag>` matched
`gh api repos/<owner>/<repo>/commits/<sha>`). `actionlint` passed on the
updated workflow.

### Integration session (this session)

- Pushed `series/00-introduction` (`ea72679`) and opened PR #1 into `main`:
  `https://github.com/tsogtbatjargal/bedoux-databricks/pull/1`.
- Confirmed `deleteBranchOnMerge` is `false` on the repo before merging
  (`gh repo view ... --json deleteBranchOnMerge`).
- Observed CI on the PR (run `35647524911`, event `pull_request`): `Detect
  bundle changes` success, `Unit tests` success, `Validate bundle` skipped,
  `Deploy bundle` skipped — matches the predicted no-deploy path since no
  `src/**`, `resources/**`, or `databricks.yml` path changed.
- Merged PR #1 with a merge commit (`gh pr merge 1 --merge`, no branch
  deletion). Merge commit `877e8d3`; `main` fast-forwarded from `4a04e77`.
- Observed CI on the resulting push to `main` (run `35647610948`, event
  `push`): `Unit tests` success, `Validate bundle` skipped, `Deploy bundle`
  skipped. No workspace deployment occurred.
- Ran the local-branch-cleanup checks from
  [branch workflow](branch-workflow.md) and all passed: clean tree, single
  worktree, `git fetch origin` then `git ls-remote --exit-code --heads origin
  refs/heads/series/00-introduction` found the branch, local tip
  `ea72679` equaled the fetched remote tip, and
  `git merge-base --is-ancestor series/00-introduction main`/`origin/main`
  both succeeded after fast-forwarding local `main`. Deleted the local branch
  with `git branch -d series/00-introduction` (not `-D`). The remote branch
  is confirmed present at the same tip.
- Did not tag, did not publish the LinkedIn draft, made no paid model calls.

## Next task

Chapter 00 is integrated. Start `series/01-know-your-platform` from updated
`main` (already at `877e8d3` locally). Map the current platform, specify
synthetic incidents, and reconcile Track 2's contract language with its
batch/full-recompute implementation. Existing invalid rows are dropped, not
quarantined; existing leads have email domains, not email/phone PII.

Read [branch workflow](branch-workflow.md) before starting: create the new
chapter branch from `main` at `877e8d3`, not from the deleted local
`series/00-introduction` ref.
