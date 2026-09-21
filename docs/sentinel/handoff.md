# Session handoff

Updated: 2026-09-21 (second session). Read this after `AGENTS.md`, then verify
the actual checkout. Current state: `series/00-introduction` at `b9250aa`, two
commits ahead of `main` at `4a04e77`, local only, working tree clean.

## Objective and decisions

Build **Bedoux Sentinel** inside `bedoux-databricks`, extending Track 2. Tell the
story through **The Art of Data Defense**: introduction, six working chapters,
and a final demo. Use synthetic data and natural, evidence-based writing.

The user requested retained chapter branches merged incrementally into `main`,
shared Codex/Claude Code preparation, optional Jev development help, and enough
documentation for a new session to continue. No Sentinel runtime is built yet.

Working defaults, pending any later user correction: retain chapter branches plus
stable post tags; either assistant implements and the other reviews; Jev is
optional. No runtime provider, API budget, AWS budget, or publication date is set.

## This preparation session

- Started from clean `main` at `4a04e77` (added diagram svg file).
- Created local branch `series/00-introduction`.
- Added shared instructions, two reusable skills with Claude adapters, a small
  Codex project config, roadmap, branch guide, writing guide, and introduction draft.
- Replaced legacy agent rules with a pointer to the shared guide and current
  bundle configuration. No pipeline, contract, CI, or workspace resource changed.
- Linked the series from README and ignored local environment/Claude preference files.
- No commits, remote branches, tags, PRs, model API calls, deployments, or posts
  were created by this preparation. These changes were later committed as
  `bfd6fdd` in the session below.

## This review session (Claude Code, fresh)

On `series/00-introduction`, branched from `main` at `4a04e77`. This session
reviewed the preparation, then — on the user's explicit instruction — committed
it and changed CI. Nothing was pushed, merged, deployed, tagged, or deleted; the
branch exists locally only and `main` is untouched.

- Discovery verified in a genuinely fresh session, not asserted. `CLAUDE.md`'s
  `@AGENTS.md` import loaded, and both `sentinel-chapter` and `sentinel-story`
  appeared in the skill list. `/sentinel-chapter` was invoked; its adapter
  resolved and the shared body in `.agents/skills/` was read and followed.
  Codex-side discovery was not exercised in this session.
- Reviewed the tracked diff (`.gitignore`, `README.md`, `docs/ai_rules.md`) and
  all untracked preparation files. The `ai_rules.md` rewrite drops rules that
  `AGENTS.md` now carries (contracts-first, scope, honesty, destructive-action
  authorization); no guardrail was lost, and the stale hardcoded workspace paths
  and personal email are correctly gone. No finding required a correction there.
- Verified `branch-workflow.md`'s CI claim against `.github/workflows/ci.yml`:
  the deploy job had no path filter and its `if` also matched `workflow_dispatch`,
  so a documentation-only merge deployed and a dispatch deployed with `run_job`
  off. The documented coupling was accurate. The user then resolved it; see below.
- One real defect found and fixed: README's "Project layout" block was stale
  after the preparation. It still described `ai_rules.md` as the guardrails and
  omitted `AGENTS.md`, `CLAUDE.md`, `docs/sentinel/`, `.agents/skills/`,
  `.claude/skills/`, and `.codex/config.toml`. All six entries now exist on disk.
## Commits made on this branch

The user authorized committing chapter 00 and separating documentation from
deployment in CI, on `series/00-introduction` only.

- `bfd6fdd` — chapter 00 preparation: `AGENTS.md`, `CLAUDE.md`, both skill
  bodies with their Claude adapters, `.codex/config.toml`, all of
  `docs/sentinel/`, the `docs/ai_rules.md` pointer, and the README additions
  including this session's layout fix. 17 files.
- `b9250aa` — CI change, kept separate: documentation and agent-configuration
  pushes no longer deploy Databricks.

## CI deployment change (`b9250aa`)

`.github/workflows/ci.yml` now separates documentation from deployment:

- `push` to `main` carries `paths-ignore` for `**.md`, `docs/**`, `.agents/**`,
  `.claude/**`, `.codex/**`, `.gitignore`, and `LICENSE`. A push whose every
  changed file matches skips the workflow, so it cannot deploy.
- `pull_request` stays unfiltered, so pipeline changes keep their full test and
  `databricks bundle validate` signal, and documentation PRs still get checked.
- `workflow_dispatch` gained an explicit `deploy` checkbox, default off. The
  deploy job's `if` now requires it. `run_job` sits inside the deploy job, so it
  cannot run a job without a deployment.

The pattern is `**.md`, not `**/*.md`. The latter requires a literal slash and
would not have matched root-level `README.md`, `AGENTS.md`, or `CLAUDE.md` —
which alone would have left the chapter 00 commit deploying. A local simulation
of GitHub's filter semantics caught this before the commit.

Conditions checked by evaluating the patterns and the deploy `if` against real
commits in this repository. All 16 cases passed: `bfd6fdd` and `4a04e77` skip;
`5e2b7e1` (Track 2 pipeline), bundle/`resources` edits, `tests/` edits,
`requirements-dev.txt`, workflow edits, and any docs+pipeline mix still deploy;
dispatch deploys only when opted in; pull requests never deploy.

**This is local evaluation of the conditions, not an observed GitHub Actions
run.** Nothing has exercised the new workflow on GitHub. Two consequences worth
knowing: a documentation-only push to `main` now produces no CI run and reports
no checks, so a required status check on `push` would never be satisfied by such
a merge; and merging a chapter that *does* change pipeline code still deploys, so
that remains a deployment decision needing authorization.

## Verification

Checks re-run this session against the current tree: 19 Markdown files and 23
relative links resolved with zero broken (this count spans all repository
Markdown, a wider scope than the preparation session's 15/19); `git diff --check`
clean; no trailing whitespace or missing final newline in any untracked Markdown
or TOML file; `.codex/config.toml` parsed by `tomllib`; nine branch/tag names
accepted by `git check-ref-format`; `git check-ignore` confirmed `.env` and
`CLAUDE.local.md`; every repository path referenced by the new docs exists.

No Python or bundle file changed this session, so `pytest` and
`databricks bundle validate` were not run. Preparation-session checks follow.

Initial environment inspection: Codex CLI 0.144.1, Claude Code 2.1.263, Python
3.14.7. `python -m pytest --version` reported that pytest is not installed in the
system interpreter. This is an environment observation, not a test failure.
Completed setup checks:

- Skill Creator's `quick_validate.py` passed for both shared skills and both
  Claude adapters (four skill files).
- A local validation pass checked 15 Markdown files, 19 relative links, eight
  unique valid Git branch names, Claude's import/adapters, and TOML syntax.
- `git diff --check` passed; the same validation checked whitespace/newlines in
  new Markdown files, which an ordinary unstaged diff does not include.
- `git check-ignore` confirmed local environment files and Claude preferences
  are ignored. `codex features list` exited successfully without model calls.
- `codex --strict-config features list` was attempted but this client rejects
  that flag for the features subcommand. TOML was parsed independently; this is
  not a claim that a live session loaded the configuration.

No Python behavior changed, so the application test suite was not run or installed.

Live Databricks state, API credentials, and provider access have not been
verified. Do not describe them as tested. Fresh-session discovery is now verified
for Claude Code only; Codex instruction and skill discovery remains unexercised.
The external sources cited in `agent-setup.md` (Codex config/skill docs, Claude
Code docs, TypeSafe/Jev links) were not re-fetched and carry their 2026-09-21 date.

## Next local task

Chapter 00 is complete and committed locally at `b9250aa`, and the CI coupling
that blocked integration is resolved. The branch has never been pushed. The next
step is integration, which needs the user's explicit request:

1. **Push `series/00-introduction` and open a PR into `main`.** Not yet
   authorized; the last instruction was to keep everything local. The PR itself
   runs tests and `databricks bundle validate` and never deploys.

   One thing to decide before merging: **this particular merge will still
   deploy.** `b9250aa` changes `.github/workflows/ci.yml`, which is deliberately
   not in `paths-ignore`, and a push's filter is evaluated over every file the
   push carries. So the merge commit runs the full test → validate → deploy
   chain. That is the last merge with this property — once the new workflow is
   on `main`, later documentation-only chapters skip CI entirely. Either accept
   one deployment of an otherwise unchanged bundle, or land the CI change by
   some route that does not push it to `main` while the old workflow is live.
   Confirm with the user rather than assuming the deployment is acceptable.
2. **Check GitHub's automatic head-branch deletion setting before the first
   merge**, per `branch-workflow.md`; chapter branches are retained.
3. **Tag `post/00-introduction`** only after the demonstrated commit is final and
   the user asks. The introduction draft stays unpublished either way.

Independent of that, a fresh Codex session should confirm its own instruction and
skill discovery, since only Claude Code's has been exercised. Repeat the
link/whitespace/TOML checks only if files change. Incorporate any user correction
to the recorded defaults. Do not re-review the preparation diff; it has been
reviewed once by each of the preparing and reviewing sessions.

After chapter 00 is integrated, start `series/01-know-your-platform` from `main`.
Map the current platform and write synthetic scenario specifications. Track 2's
contract incorrectly mixes append-only/full-recompute and streaming/batch language;
reconcile it with the implementation as part of that chapter. Do not claim the
existing dropped rows are quarantined or that email/phone PII already exists.

Use `roadmap.md` for acceptance criteria. Update this file at the end of each
session with actual checks, remaining work, and branch/commit state. Avoid copying
the full conversation into it.
