# Working in bedoux-databricks

This is a portfolio lakehouse with two existing tracks. Bedoux Sentinel extends
Track 2 through a series called **The Art of Data Defense**. Its data is fictional.

## Start a session

1. Read `docs/sentinel/handoff.md` for the current state and next task.
2. Check `git status --short --branch`. Preserve existing work. The checkout is
   evidence; a branch name recorded in a document may be stale.
3. Read the relevant chapter in `docs/sentinel/roadmap.md`. Before pipeline work,
   read `docs/contracts.md` for Track 1 or `docs/contracts-bedoux.md` for Track 2,
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
  `main`, merges back when ready, and retains its branch. Never automatically
  delete chapter branches, force-push them, or move a published post tag.
- Current CI deploys the bundle on a push to `main`. Treat merging/pushing there
  as a deployment decision. Do not infer permission from a documentation task.
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

Use `sentinel-chapter` for chapter implementation/review/handoff and
`sentinel-story` for posts and demo scripts. Claude adapters load the same skill
bodies as Codex. Read only the references needed for the current task.

## Checks and context

- Search with `rg` first; read targeted ranges of large files (over 350 lines).
  Keep logs and diffs bounded. Do not print secrets or dump whole transcripts.
- For Python behavior changes, run `python -m pytest tests/ -q` in an environment
  with `requirements-dev.txt` installed. These tests do not exercise live Spark.
- For bundle changes, validate when workspace credentials are available; report
  missing access honestly. Deploying, binding, running jobs, and destructive SQL
  require authorization covering the actual workspace action.
- For documentation/configuration work, check links, syntax, skills, and diff
  whitespace. Do not add tests that merely restate prose.
- Write plainly. Prefer a concrete problem, decision, result, and limitation to
  slogans. Follow `docs/sentinel/writing.md` for public-facing material.
