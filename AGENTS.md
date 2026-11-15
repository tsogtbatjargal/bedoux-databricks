# Working in bedoux-databricks

This is a portfolio lakehouse with four tracks: TPC-H medallion (1), Bedoux
analytics (2), regulated gaming & retail (3) and the Agentic Data Platform (4,
also deployed to Azure Databricks). Bedoux Sentinel extends Track 2 through a
series called **The Art of Data Defense**. All data is fictional.

## Start a session

1. Read `docs/sentinel/handoff.md` for the current state and next task.
2. Check `git status --short --branch`. Preserve existing work. The checkout is
   evidence; a branch name recorded in a document may be stale.
3. Read the relevant chapter in `docs/sentinel/roadmap.md`. Before pipeline work,
   read `docs/contracts.md` for Track 1, `docs/contracts-bedoux.md` for Track 2,
   `docs/contracts-aglc.md` for Track 3 or `docs/contracts-adp.md` for Track 4,
   plus the affected resource YAML. Flag contract/code disagreements explicitly.
4. Continue the task the user authorized. An approved plan does not need repeated
   approval for ordinary local edits and checks. A handoff records context, not
   new authorization to deploy, publish, or change live data.

## Scope and evidence

- Keep Track 1 stable unless the task specifically includes it.
- Use synthetic fixtures. Never copy employer/client data, credentials, private
  logs, or unredacted sensitive data into commits, posts, or model requests.
- Distinguish planned, implemented, and demonstrated behavior. A local fixture
  test does not prove a Databricks integration or an IAM boundary works.
- Record measured results with their command, inputs, and environment. Label
  estimates. Do not invent costs, row counts, incidents, quotes, or personal stories.
- A rules-based control enforces permissions and publication decisions. Model
  output is evidence to evaluate, not authority to widen permissions.

## Branches and delivery

- Follow `docs/sentinel/branch-workflow.md`. Each chapter starts from integrated
  `main` and keeps its remote branch after merging. The user permits removing a
  merged local chapter branch after verifying its remote copy and integration.
  Never delete remote chapter branches, force-push them, or move published tags.
- Current CI deploys Free Edition `dev` on pushes to `main` that change
  `src/`, `resources/` or `databricks.yml`. Treat merging those changes as a
  deployment decision. Docs and local-tooling changes alone run tests only.
- Azure (Track 4) deploys only through the manual `deploy-azure.yml` workflow
  (GitHub OIDC, target `azure_ci`) or a local CLI deploy; never automatically.
- Standing authority from the owner: agents may commit, push branches, open PRs,
  run read-only cloud checks, and merge docs/images-only PRs after `Unit tests`
  passes. Ask first for other merges, deploys, job runs, grants, model
  deployments, deletes/destroys and paid model calls (with a spend cap).
- Do not publish LinkedIn posts, send messages, install global tools, or spend on
  model calls merely because a chapter describes those activities.
- Before ending implementation work, update `docs/sentinel/handoff.md` with what
  changed, checks and results, remaining work, and the exact next useful task.

## Agent workflow

Either Codex or Claude Code can implement. The other can review the same diff in
a separate session. One writer per checkout; use separate worktrees if the user
requests simultaneous implementations. Reviewers report findings before editing.
Jev is optional advisory classification; its absence must not block local work.
See `docs/sentinel/agent-setup.md` for invocation and review prompts.

Use `sentinel-chapter` for Sentinel chapter work and `adp-platform` for Track 4
(code, Azure, evaluation, evidence, diagrams). Codex reads them from
`.agents/skills/`; Claude Code's adapters in `.claude/skills/` load the same bodies. Keep editorial work
in the separate `bedoux-sentinel-content` workspace, which owns `sentinel-story`.
See `docs/sentinel/repository-scope.md`; do not add posts or narration here.

## Checks and context

- Search with `rg` first; read targeted ranges of large files (over 350 lines).
  Keep logs and diffs bounded. Do not print secrets or dump whole transcripts.
- Use `uv sync --locked` and `uv run --locked python -m pytest -q` for local
  Python checks. Dependencies belong in `pyproject.toml` and `uv.lock`; use the
  project `.venv`, not system pip. These tests do not exercise live Spark.
- For bundle changes, validate when workspace credentials are available; report
  missing access honestly. Always pass `--target` (the default is Free Edition).
  Azure CLI isn't installed: use `uvx -q --python 3.13 --from azure-cli az`. Deploying, binding, running jobs, and destructive SQL
  require authorization covering the actual workspace action.
- For documentation/configuration work, check links, syntax, skills, and diff
  whitespace. Do not add tests that merely restate prose.
- Write technical docs plainly: problem, decision, evidence and limitation.
- Commit shared technical agent instructions and skills. Keep personal model
  preferences, credentials and machine-local settings ignored.
