# Session handoff

Updated: 2026-09-21, after the cleanup was reviewed and committed. Verify the
checkout before working; this page records context, not permission for external
actions.

## Current state

- Branch: `series/00-introduction`, based on `main` at `4a04e77`.
- Commits: `bfd6fdd` (chapter 00 preparation), `b9250aa` (first CI separation),
  `a2231b7` (handoff), `04ded3a` (environment/CI/branch-policy cleanup,
  reviewed by a separate Claude Code session).
- Working tree clean. Nothing pushed, merged, deployed, tagged, or posted. No
  branch deleted. `main` untouched at `4a04e77`.
- No Sentinel runtime exists yet. The launch post remains an unpublished draft.
- Chapter 00 is ready for integration when the user requests it.

## Decisions to preserve

Build **Bedoux Sentinel** inside this repo, extending Track 2 with fictional data.
The series is **The Art of Data Defense**: introduction, six working chapters,
and a full demo. Use concrete, natural writing with measured evidence.

The user's latest branch preference supersedes the old local-retention rule:
**keep remote chapter branches and stable post tags; remove merged local chapter
branches once their remote copy and integration are verified.** See
[branch workflow](branch-workflow.md) for exact checks. Neither `main` nor the
current unmerged chapter branch is eligible for deletion now.

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

Not fixed, deliberately: `databricks/setup-cli@main` still tracks a moving
branch while the other third-party actions are SHA-pinned. Pinning it needs a
SHA looked up from the network, and guessing one would risk breaking CI. The
`dorny/paths-filter` and `astral-sh/setup-uv` SHAs were also written offline and
have not been resolved against GitHub; the first real run confirms them or fails
fast. Recorded in `branch-workflow.md`.

## Next task

The cleanup has been reviewed and committed. Chapter 00 is complete locally and
ready for integration; nothing further is pending on this branch. Checks above
already passed — repeat them only for new changes. Use
[Local development](../development.md) to resume.

Integration, when the user requests it:

1. Push `series/00-introduction` and open a PR into `main`. Expect the
   `Unit tests` check to run and the workspace jobs to skip — the branch changes
   no bundle path. Verified locally; not yet observed on GitHub.
2. Before the first merge, confirm GitHub's automatic head-branch deletion is
   off, so the remote chapter branch is retained.
3. After merging, optionally remove the merged *local* branch using the
   preservation and ancestry checks in
   [branch workflow](branch-workflow.md). Never `-D`, never delete the remote.
4. Optionally pin `databricks/setup-cli` to a SHA while network access is
   available, and confirm the two offline-written action pins resolve.

Then start `series/01-know-your-platform` from updated `main`. Map the current
platform, specify synthetic incidents, and reconcile Track 2's contract language
with its batch/full-recompute implementation. Existing invalid rows are dropped,
not quarantined; existing leads have email domains, not email/phone PII.
