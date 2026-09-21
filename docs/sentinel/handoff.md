# Session handoff

Updated: 2026-09-21. **A live healthy-baseline run just found a blocking
defect**: the job reports full success, but `leads_clean`/`leads_quarantine`
(and the same pair for web_events/ops_events) and `quality_metrics` are all
empty, `gate_status` reports a pass that is inconsistent with that emptiness,
and Gold overwrote its prior real baseline with empty/degenerate content for
two of three tables. See "Baseline run result: BLOCKING DEFECT found" below —
read that before doing anything else with this chapter. Do not redeploy, rerun,
or start fault injection until this is understood; nothing was worked around.
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

## Deployment and baseline run (2026-09-21, this session)

Scope authorized: controlled preflight, one deploy to `dev` at
`bedoux_lead_invalid_rate=0.02`, one job run. No fault injection.

**Preflight** (all under profile `bedoux-databricks`, target `dev`):
- Commit `281efe0c11389e043c1c7bc2082462864bde7acb`, identity
  `tsoglog.uli@gmail.com`, working tree clean, local/remote in sync.
- No active runs on `bedoux_analytics_job` (133273744478391) or
  `tpch_medallion_pipeline_job` (32014554262162); no in-progress updates on
  any of the six pipelines. Confirmed read-only, then enforced with
  `--fail-on-active-runs` on deploy (not just checked).
- `databricks bundle plan -t dev --var bedoux_lead_invalid_rate=0.02`:
  `0 to add, 2 to change, 0 to delete, 6 unchanged` — only
  `jobs.bedoux_analytics_job` (adds the gate task) and
  `pipelines.bedoux_bronze_pipeline` (adds the invalid-rate config) change.
  No deletions/replacements, Track 1 untouched.
- Pre-deploy Gold baseline captured via the serverless SQL warehouse
  (`e63747243511532c`), order-independent digest
  (`sha2(concat_ws('||', sort_array(collect_list(md5(to_json(struct(*)))))), 256)`):

  | Table | Rows | `updated_at` (UTC) | Digest |
  |---|---|---|---|
  | `gold_campaign_performance` | 30 | 2026-07-30T20:41:58.494Z | `72575a78...a805dba` |
  | `gold_client_funnel` | 132 | 2026-07-30T20:42:03.654Z | `636c7dd0...7df1c2e` |
  | `gold_ogi_ops_health` | 183 | 2026-07-30T20:41:58.483Z | `72aef48d...2083e41d` |

  (Full digests are in this session's transcript; truncated here for
  readability, not secrecy.) This is the pre-chapter-02 baseline being
  replaced by the healthy gated run below — expected and accepted per this
  task's scope, not a loss.
- `databricks bundle validate -t dev`: Validation OK, both before and
  immediately before deploy.

**Deploy:** `databricks bundle deploy -t dev --var bedoux_lead_invalid_rate=0.02
--fail-on-active-runs` (no `--auto-approve`). Result: `0 created, 2 changed, 0
deleted, 6 unchanged` — matched the plan exactly. Confirmed post-deploy by
reading the live job/pipeline definitions back:
- `bedoux_analytics_job` task graph: `bedoux_bronze_task` →
  `bedoux_silver_task` → `bedoux_gate_task` (notebook) → `bedoux_gold_task`.
  `max_concurrent_runs: 1`.
- `bedoux_bronze_pipeline` configuration: `bedoux.lead_invalid_rate: "0.02"`.

This is the first deploy that introduces the gate to `dev` — the job's live
graph was previously the ungated bronze → silver → gold from before chapter 02.

## Baseline run result: BLOCKING DEFECT found, not a clean pass

Run `343186547330463` (job 133273744478391), `bedoux_lead_invalid_rate=0.02`,
started 2026-09-21T23:37:51Z, ended 23:43:46Z.
Run URL: `https://dbc-3f70aae3-11d5.cloud.databricks.com/jobs/133273744478391/runs/343186547330463?o=7474656218808128`.

**All four tasks reported `SUCCESS`** (bronze, silver, gate, gold), and the
pipeline event log shows every flow completing with no WARN/ERROR events and
no exceptions. **Job-level success is not trustworthy evidence here** — the
underlying data tells a different story, confirmed with fresh queries several
minutes apart (not a caching artifact) and with a byte-for-byte diff of the
deployed `silver.py` against the local checkout (identical — not a stale-code
artifact):

- Bronze populated correctly: `leads_raw` 500, `web_events_raw` 2000,
  `ops_events_raw` 365 rows. `clients_clean`/`campaigns_clean` (unrelated
  dimension logic) also correct: 10 / 30 rows.
- **`leads_clean`, `leads_quarantine`, `web_events_clean`,
  `web_events_quarantine`, `ops_events_clean`, `ops_events_quarantine`, and
  `quality_metrics` are all 0 rows** — despite `dataset_life_cycle` events
  confirming each was freshly (re)created/refreshed by this exact run
  (`updated_at` timestamps match the run window). 2,865 fact rows
  (500+2000+365) went into Bronze and **zero came out the other side of the
  clean/quarantine split, in either table** — the precise "nothing vanishes
  without a record" failure mode chapter 02 was built to close, now observed
  live on a run the job reported as a full success.
- **`gate_status` itself is internally inconsistent with that reality**: it
  reports `total=500/2000/365, quarantined=0, gate_passed=true` for
  leads/web_events/ops_events (`_computed_ts` 2026-09-21T23:40:51.869Z) —
  plausible-looking numbers that match Bronze's counts, but they cannot be
  correct, because `_row_counts` reads the exact same `dlt.read(view_name)`
  the (also-empty) `_clean`/`_quarantine` tables read, with the same
  `size(_reasons)` predicate. Both cannot be right; the persistent tables
  (0 rows, physically verified) are the ones that matter, so gate_status's
  "pass" is not trustworthy evidence that the gate is protecting anything
  right now.
- **Gold cascaded the damage**: because gate_status said pass, `bedoux_gold_task`
  ran and overwrote the previous 2026-07-30 baseline.
  `gold_campaign_performance` still has 30 rows (one per campaign, from
  `campaigns_clean` which is healthy) but every row now has `lead_count=0`,
  `won_count=0`, `conversion_rate=0.0`, `cost_per_lead=NULL` — confirmed by
  direct query. `gold_client_funnel` went from 132 rows to **0**.
  `gold_ogi_ops_health` went from 183 rows to **0**. The prior baseline's
  content is gone from these two tables, replaced with empty tables, not
  with a new valid healthy baseline.
- Update IDs for the record: bronze `bd8fee68-1a78-4f95-b5e7-8fb123e224d7`,
  silver `adc3328b-e2cc-4caa-88a2-a420099f34c4`, gold
  `664c30db-3e65-44e0-ae2b-bba1a04b97e7`, all `COMPLETED`.

**Root cause not yet identified.** Ruled out: job/task failure (none),
stale query cache (re-queried ~6 minutes apart, same result), stale deployed
code (diffed deployed `silver.py` byte-for-byte against the checkout —
identical). What's left points at the DLT/Lakeflow Declarative Pipelines
runtime itself — likely something about how a `@dlt.view` (`leads_flagged`
etc., non-materialized, recomputed per reference) behaves when read via
`dlt.read()` from several sibling `@dlt.table`s in the same update, on this
serverless configuration — but the pipeline event log has no WARN/ERROR/
exception to point at, and CLI-level read-only tools don't expose Spark
driver logs or per-flow row-count metrics. This needs either Spark UI /
driver log access through the workspace UI, or a deliberately instrumented
diagnostic run, neither of which this task's scope covers.

**Left in this state deliberately, not rerun.** Per this task's instructions
not to repeatedly rerun or bypass the gate on a failure — and this is worse
than the anticipated "gate task fails" case, since here it silently reported
success while losing data. Current live `dev` state: Bronze and the two
dimension tables are healthy; all three fact-source clean/quarantine tables
and `quality_metrics` are empty; `gate_status` shows a false-looking pass;
Gold has empty/degenerate content for all three tables where it previously
had a real 2026-07-30 baseline. Rollback (redeploy from `main`) would restore
the *ungated* graph, not fix this, and would not restore the destroyed Gold
baseline (no backup of it beyond the digests recorded above).

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
   edit), the secrets are set, and CI validates the current tree.
3. Done, but **not clean**: preflight and one healthy-baseline deploy + run
   executed exactly as scoped (see "Deployment and baseline run" and
   "Baseline run result: BLOCKING DEFECT found" above). The run did not
   demonstrate a working gate — it demonstrated a silent data-loss defect
   that the gate's own passing status did not catch.
4. **Not proposed: fault injection.** Running `bedoux_lead_invalid_rate=0.30`
   on top of a pipeline that already loses 100% of fact rows at 0.02 would
   not test anything meaningful and would compound the damage to Gold. The
   next authorized step should be **root-causing why `leads_clean`/
   `leads_quarantine`/`quality_metrics` come out empty while `gate_status`
   reports counts inconsistent with that emptiness** — most likely via Spark
   UI / driver log access on the silver pipeline update
   (`adc3328b-e2cc-4caa-88a2-a420099f34c4`) through the workspace UI, which
   this CLI-only task didn't have. Only once a healthy run actually produces
   correct, self-consistent clean/quarantine/gate_status content should
   fault → restore → replay be attempted.
5. The destroyed `gold_client_funnel`/`gold_ogi_ops_health` baseline content
   cannot be un-lost; only the pre-run digests above remain. A real fix will
   need a genuinely fresh baseline, not a restore.
6. Only mark demonstrated after real evidence of a *correct* run. Push/
   integration and remote retention/local-branch cleanup follow
   [branch-workflow.md](branch-workflow.md) within user authorization. Chapter
   03 should not start from this branch's current state until this defect is
   resolved.

Use `sentinel-story` only when asked to draft posts. Jev remains optional;
AWS is deferred with no budget or deployment authorization. Earlier AWS reuse
context and preparation history remain available in Git.
