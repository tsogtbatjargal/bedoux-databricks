# Session handoff

Updated: 2026-09-21 (second session). Read this after `AGENTS.md`, then verify
the actual checkout.

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
  were created by this preparation. Changes are currently uncommitted.

## This review session (Claude Code, fresh)

Still on `series/00-introduction` at base `4a04e77`; the preparation work remains
uncommitted. Purpose was the recorded next task: confirm discovery and review the
preparation diff against chapter 00's scope.

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
  the deploy job has no path filter and its `if` also matches `workflow_dispatch`,
  so a documentation-only merge deploys and a dispatch deploys with `run_job` off.
  The documented coupling is accurate and the decision is still open.
- One real defect found and fixed: README's "Project layout" block was stale
  after the preparation. It still described `ai_rules.md` as the guardrails and
  omitted `AGENTS.md`, `CLAUDE.md`, `docs/sentinel/`, `.agents/skills/`,
  `.claude/skills/`, and `.codex/config.toml`. All six entries now exist on disk.
- No commits, pushes, tags, PRs, deployments, model API calls, or posts. The only
  change made this session is the README layout block.

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

Chapter 00's content has been reviewed and its local checks pass. Two things are
now waiting on the user rather than on more local work:

1. **Commit chapter 00.** The preparation plus this session's README fix are
   still uncommitted on `series/00-introduction`. Committing needs the user's
   go-ahead; do not push or open a PR without a separate request.
2. **Decide the CI coupling before integrating.** Verified this session:
   `.github/workflows/ci.yml` deploys the bundle on any push to `main`, including
   a documentation-only merge, and on `workflow_dispatch` even with `run_job`
   off. Either accept that a docs merge deploys, or change CI to gate `deploy`
   (for example a `paths-ignore` on docs, or a manual-only deploy job) first.
   Changing CI is itself a chapter-00-scope decision the user must authorize.

A fresh Codex session should confirm its own instruction and skill discovery,
since only Claude Code's has been exercised. Repeat the link/whitespace/TOML
checks only if files change. Incorporate any user correction to the recorded
defaults. Do not re-review the preparation diff; it has been reviewed once by
each of the preparing and reviewing sessions.

After chapter 00 is integrated, start `series/01-know-your-platform` from `main`.
Map the current platform and write synthetic scenario specifications. Track 2's
contract incorrectly mixes append-only/full-recompute and streaming/batch language;
reconcile it with the implementation as part of that chapter. Do not claim the
existing dropped rows are quarantined or that email/phone PII already exists.

Use `roadmap.md` for acceptance criteria. Update this file at the end of each
session with actual checks, remaining work, and branch/commit state. Avoid copying
the full conversation into it.
