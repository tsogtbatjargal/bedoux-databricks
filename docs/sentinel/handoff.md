# Session handoff

Updated: 2026-09-21. Chapter 02 is implemented locally, **not demonstrated**.
Local Databricks CLI access is now set up and read-only-verified against the
live workspace (see below); no deploy or job run has occurred.
This file records context, not permission to push, merge, deploy, run jobs,
change secrets, bind resources, or publish. Inspect Git before continuing.

## Current checkpoint

- Branch: `series/02-quality-gate`, **pushed and in sync with origin**.
  PR #3 is open, unmerged, `MERGEABLE`, and now **green**.
- Local HEAD: `b8d630f`, matching PR #3's head. The five chapter-02 commits
  are `8e4cf6a` gate redesign, `46e8d1f` live-verification runbook,
  `01e7972` run-boundary hardening + fault-injection knob, `6ec7b37`
  Databricks CLI pin, `b8d630f` credential determination.
- Working tree clean. No merge, deploy, or job run has occurred.
- Track 1 source/resources and CI policy are unchanged.
- No credential value was read, printed, or configured. Read-only workspace
  API calls were made (see "Credential capability" below). No deployment, job
  run, merge, tag, push, paid model call, or publication occurred.
- Chapters 00/01 are integrated into main; remote chapter branches retained.
  Their local branches were previously removed after preservation/ancestry
  checks. Detailed history remains in Git and chapter documents.

## Implementation now in the checkout

- Bronze/Silver generate fictional data, quarantine rejected facts with reasons,
  and count rows without double-counting multi-reason records.
- The ordinary `bedoux_gate_task` notebook runs after Silver and before Gold.
  Gold has no imperative gate or self-referencing fallback. Failed gate means
  the whole Gold pipeline should not run, including a first-ever run.
- `quality.evaluate_gate` rejects absent/duplicate sources, false/null pass
  values, stale/null/invalid timestamps, empty required-source configuration,
  and missing or timezone-naive run boundaries.
- The task now requires `{{job.start_time.timestamp_ms}}`. It converts Spark
  timestamps with `unix_millis` before Python collection and uses explicit
  UTC datetimes. Missing/unresolved widgets cannot disable freshness.
- Bundle variable `bedoux_lead_invalid_rate` feeds pipeline configuration
  `bedoux.lead_invalid_rate`; default 0.02, demo fault 0.30, valid range 0..1.
  Malformed/nonfinite values fail. Explicit lead schema handles the all-null
  campaign column at rate 1. Other source rates/seeds remain unchanged.
- This is a deploy-time override, not a job-run parameter. Restoration requires
  redeploying 0.02. No live rate setting was changed in this session.

## Important limits

- Timestamp freshness is **not exact run/batch binding**. The supported demo
  assumes one full serialized job and no other writers, direct pipeline runs,
  repair-only runs, or deployments mid-run. Exact batch/version binding is
  not implemented. Direct Gold execution bypasses the gate.
- Gold withholding is whole-pipeline, not per-table. Successful gate approval
  does not make subsequent multi-table Gold publication atomic.
- Synthetic business rows are reproducible; audit timestamps are not.
  Quarantine tables are recomputed, not an append-only incident archive.
  Capture failed-stage evidence before restoring the normal fixture.
- CI credentials are configured and **proven working**: the user set
  `DATABRICKS_HOST` and `DATABRICKS_TOKEN` as repository secrets from a
  90-day PAT created 2026-09-21 (comment `github-actions-ci`), and run
  `35667369376` on `b8d630f` validated the bundle in CI. The original
  `Validate bundle` failure was missing credentials, not a bundle defect.
  **Consequence:** merging PR #3 to `main` would now deploy, because the
  bundle-path condition and credentials are both satisfied. Treat merging as
  a deployment decision.
- Full `bundle deploy` includes both tracks. Do not confuse unchanged Track 1
  source with a Track-2-only deployment.
- Databricks CLI is now installed locally and OAuth-authenticated (see
  "Databricks CLI access" below); `bundle validate` has succeeded once
  against `dev`. Notebook runtime, scheduler withholding, and retained Gold
  content still require live verification via an actual job run, which has
  not happened. Serverless notebook configuration is documented; there is no
  evidence yet requiring a different task type.

## Databricks CLI access

- Installed the official Databricks CLI `v1.17.0` (matched GitHub's `latest`
  release at install time) via mise's explicit `github:databricks/cli`
  backend, pinned in `mise.toml` — not `aqua:databricks/cli`, not the legacy
  `databricks-cli`/`databricks-sdk` PyPI packages, not a global mise
  selection, no sudo, no shell profile change. `mise install` verified GitHub
  artifact attestation for the downloaded release asset.
- User completed `databricks auth login` (OAuth, browser) against
  `https://dbc-3f70aae3-11d5.cloud.databricks.com` under profile
  `bedoux-databricks`. Token is stored in the OS keyring via
  `~/.databrickscfg` (outside the repo); no credential was requested, read,
  or printed by the agent.
- Bounded read-only checks, all against the live workspace:
  - `databricks auth describe --profile bedoux-databricks` (no `--sensitive`):
    succeeded, host/account/workspace IDs resolved, `auth_type: databricks-cli`,
    secure OS-keyring token storage confirmed.
  - `databricks catalogs list` and `databricks jobs list --limit 5`: both
    succeeded. The workspace already has deployed dev jobs from a prior
    session/CI attempt, including `[dev tsoglog_uli] bedoux_analytics_job`
    with `max_concurrent_runs: 1` as the runbook expects.
  - `databricks bundle validate --target dev --profile bedoux-databricks`:
    **Validation OK.** This validated the checkout's current working tree
    (including this session's uncommitted follow-up changes), not just the
    last commit.
- Remaining blockers: none for read-only access. Deploying, running the job,
  and the healthy → fault → restored → replay demonstration in
  [live-verification.md](live-verification.md) all still need separate,
  explicit authorization per step — this task only covered CLI setup and
  validation. `docs/development.md` now documents the install/profile/verify
  commands for future sessions.

## Credential capability and workspace starting state

Determined 2026-09-21 by read-only API calls under profile
`bedoux-databricks`. Detail and the exact consequences are in
[live-verification.md](live-verification.md) section 1.

- **PATs work.** `tokens list` and the admin `token-management list` both
  succeeded. Two tokens exist: `bedoux-databricks-project` (expires
  2027-07-30) and `CLI Access Token` (created 2026-09-21, expires
  2027-09-21). The user should confirm they recognize both and revoke any
  they do not. No token value was requested, read, or printed.
- **No service principal exists.** `service-principals list` returns an empty
  list; the endpoint answers, but creating one is a write action and was not
  attempted. OAuth M2M is therefore still unproven, and **CI stays on a PAT**
  with no workflow edit needed.
- The user's identity is in the workspace `admins` group, so token creation
  and revocation need no account console.
- **`dev` is not empty.** `[dev tsoglog_uli] bedoux_analytics_job` is deployed
  with `max_concurrent_runs: 1`, but its live task graph is the
  pre-chapter-02 bronze → silver → gold, **without** `bedoux_gate_task`.
  Deploying is what introduces the gate.
- All three `workspace.bedoux_gold.*` tables already exist, last written
  2026-07-30. Good: it makes the withheld stage's retention claim checkable.
  Also means the first-ever-run case cannot be demonstrated here without
  destroying that baseline — leave it as a design argument.

## CI verification (2026-09-21)

Run `35667369376`, `pull_request` event on `b8d630f`:

| Job | Result |
|---|---|
| Unit tests | success |
| Detect bundle changes | success |
| Validate bundle | success — `Validation OK!`, host masked as `***` |
| Deploy bundle | **skipped** |

`deploy` skipped because `push` is scoped to `branches: [main]`, so a chapter
branch only fires `pull_request`. Confirmed by workspace inspection after the
run: the deployed `[dev tsoglog_uli] bedoux_analytics_job` still has the
ungated bronze → silver → gold graph, and
`gold_campaign_performance.updated_at` is still 2026-07-30T20:41Z. CI reached
the workspace to read, and changed nothing.

## Checks

- `uv run --locked python -m pytest -q`: **92 passed** (CPython in project
  `.venv`). Includes actual notebook/Bronze source execution with API stubs,
  generator baseline/fault/restoration, and policy edge cases. **No Spark/DLT
  runtime** is exercised.
- `uv lock --check`: passed.
- YAML parse plus graph/config assertions: passed. Verified serial job,
  Silver → gate → Gold, default all-success conditions, dynamic timestamp
  parameter, and default/routed demo variable. Not CLI bundle validation.
- All Track 2 Python sources parsed; `git diff --check` passed.
- Relative Markdown links in changed documents: **17 checked, none broken**.
- Re-run at commit time: `uv sync --locked` then
  `uv run --locked python -m pytest -q` — **92 passed**; `git diff --check`
  clean; `databricks auth describe` and `bundle validate -t dev` re-confirmed.

## Exact next task

1. Done: the follow-up is reviewed and committed locally (see "Current
   checkpoint"). Nothing was pushed; PR #3 is untouched and still open.
2. Done: [live-verification.md](live-verification.md) section 1 is **closed**.
   Local OAuth works, the credential question is answered (PAT, no workflow
   edit), the secrets are set, and CI validates the current tree. Sections 3
   and 4 remain entirely unexecuted.
3. Before any deploy/run, obtain authorization covering the target,
   full-bundle deployment scope, and synthetic job runs. Preserve existing
   workspace ownership; no implicit binding, cleanup, or table deletion.
   Note that the first deploy replaces the live job graph with the gated one,
   and that a 2026-07-30 Gold baseline exists to preserve.
4. Run healthy → fault withheld → restored → replay. Record resolved gate
   parameters, task outcomes, counts and content comparisons. If interrupted
   at the bad-rate stage, prominently record the deployed 0.30 setting.
5. Only mark demonstrated after real evidence. Push/integration and remote
   retention/local-branch cleanup follow [branch-workflow.md](branch-workflow.md)
   within user authorization. Then chapter 03 starts from integrated main.

Use `sentinel-story` only when asked to draft posts. Jev remains optional;
AWS is deferred with no budget or deployment authorization. Earlier AWS reuse
context and preparation history remain available in Git.
