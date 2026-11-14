# Track 4 live evidence: Azure Databricks

First workspace runs of `adp_platform_job`, 2026-11-13 (local time; table
timestamps are UTC, 2026-11-14 01:31–01:38). Fake data only; no model was called.

## Environment and commands

- Workspace `adb-adp-dev`, `https://adb-7405615454810108.8.azuredatabricks.net`,
  Azure canadacentral, trial (Premium) SKU. Inventory: `docs/adp/azure-setup.md`.
- Databricks CLI 1.17.0, profile `ADP_AZURE` (OAuth U2M), bundle target
  `azure_dev`, catalog `adb_adp_dev`. Bundle at commit `95dfe75`.
- `databricks bundle validate|plan|deploy --target azure_dev --profile ADP_AZURE`:
  validation OK; 13 resources created (4 jobs, 9 pipelines), all serverless,
  no schedules, no continuous pipelines. Nothing else was started.
- Runs: `databricks bundle run adp_platform_job --target azure_dev --profile ADP_AZURE --params <p>`.
  Job id `971448448678386`. Seed 7 (default) for all runs.
- Table checks: SQL statements on the Serverless Starter Warehouse (Small,
  auto-stop 10 min).

## Runs

| # | Params | Run id | Result | Run time | Task execution |
|---|---|---|---|---|---|
| 1 | `day=1` | `1032549350403236` | SUCCESS | 57 s | ingest 40 s, reconcile 11 s |
| 2 | `day=2` | `405637222205278` | SUCCESS | 51 s | ingest 36 s, reconcile 10 s |
| 3 | `day=2` (repeat) | `77696391076074` | FAILED, as designed | 70 s | ingest 38 s; reconcile 12 s + automatic retry 10 s |
| 4 | `day=3,defect=bad_unit_price,defect_day=3` | `767978114792943` | FAILED, as designed | 54 s | ingest 38 s, reconcile 11 s |
| 5 | same as 4 (retry check, after the fix) | `910590590998406` | FAILED, as designed | 68 s | ingest 50 s, reconcile 12 s, no retries |
| 6 | `day=3,defect=none` via GitHub Actions, target `azure_ci` | `892095403308316` | FAILED, as designed | 65 s | ingest 44 s, reconcile 14 s, no retries |

A failed run is the alert: run 3 opened `no_new_data` incidents, run 4 opened
`ingestion_failed`. The reconcile task ran after the failed ingest in run 4
(`run_if: ALL_DONE`), as the contract requires.

## Results vs the local engine

Every audit value below equals the output of the same sequence through
`src/adp` locally (seed 7; day 1, day 2, day 2, day 3 with `bad_unit_price`).

`adp_meta.ingest_runs`:

| Run | Dataset | Status | New | Ins | Upd | Quar | Watermark after |
|---|---|---|---|---|---|---|---|
| 1 | orders | succeeded | 80 | 80 | 0 | 0 | 2026-11-02T21:59:48, [42] |
| 1 | order_lines | succeeded | 198 | 198 | 0 | 0 | 2026-11-02T19:48:52, [42,2] |
| 1 | payments | succeeded | 48 | 48 | 0 | 0 | 2026-11-02T21:59:48, [28] |
| 2 | orders | succeeded | 131 | 80 | 51 | 0 | 2026-11-03T19:59:07, [156] |
| 2 | order_lines | succeeded | 204 | 204 | 0 | 0 | 2026-11-03T19:59:07, [156,2] |
| 2 | payments | succeeded | 14 | 14 | 0 | 0 | 2026-11-03T19:00:00, [59] |
| 3 | all three | succeeded | 0 | 0 | 0 | 0 | unchanged |
| 4 | orders | succeeded | 123 | 80 | 43 | 0 | 2026-11-04T19:41:23, [235] |
| 4 | order_lines | **failed** `quarantine_ratio_exceeded` | 0 | 0 | 0 | 27 | **unchanged** 2026-11-03T19:59:07, [156,2] |
| 4 | payments | succeeded | 43 | 43 | 0 | 0 | 2026-11-04T11:00:00, [90] |

What this shows in the workspace:

- **Incremental load:** day 2 read only rows past the day-1 cursor; 51 orders
  were updates (status changes), merged rather than duplicated.
- **Repeat run:** the day-2 repeat found 0 new rows and changed nothing.
- **Watermark rule:** the failed `order_lines` run left its watermark where it was.
- **Quarantine:** `adp_meta.quarantine` holds 27 rows for `sales.order_lines:day3:4`,
  each with problem `unit_price: cast_failed` and the raw value `N/A`.
- **Bronze after run 4:** orders 240, order_lines 402, payments 105; no duplicate
  keys in any table (`count(*) - count(DISTINCT key) = 0`).
- **Gold** `adp_gold.daily_revenue`: 2026-11-02 → 62 orders, 6197.60;
  2026-11-03 → 43 orders, 4297.71. Matches local.
- **Reconciliation:** `source_to_target` and `payments_vs_orders` passed for
  every run (`adp_meta.reconcile_runs`).
- **Late arrival:** day 2 includes a payment stamped on day 1 that arrives on day 2.
  It loaded within the 24 h lookback (payments: 14 new on day 2, as locally).
  The beyond-lookback case (`late_arrival` defect) was not run in the workspace.
- PyYAML imported on serverless notebook compute (the spec loader ran).

## Finding: automatic retry duplicated audit rows

Run 3's reconcile task raised its incident error, and serverless auto-optimization
retried it once (attempt 1). Both attempts appended to `adp_meta.reconcile_runs`
and `adp_meta.incidents`, so day 2 has three `reconcile_runs` rows (one per
attempt across runs 2–3) and six `no_new_data` incident rows instead of three.
Run 4 was not retried.

Fix: `disable_auto_optimization: true` and `max_retries: 0` on both tasks in
`resources/adp.yml`. These failures are deliberate signals, not transient errors.
Redeployed; `databricks jobs get 971448448678386` shows both settings on both
tasks. The duplicate rows written before the fix remain in the tables.

Retry check, run 5 (`910590590998406`, `day=3,defect=bad_unit_price,defect_day=3`
again): FAILED as designed in 68 s; ingest and reconcile each ran attempt 0
only. It added exactly one `reconcile_runs` row and one row per incident
(`day3:sales.order_lines:ingestion_failed`, `day3:sales.orders:no_new_data`,
`day3:sales.payments:no_new_data`). `order_lines` failed again on the same 27
`N/A` prices (quarantined under `sales.order_lines:day3:5`) with its watermark
still at 2026-11-03T19:59:07; orders and payments read 0 new rows.

## CI deploy and run as the service principal

Run 6 is the first deploy and job run by GitHub Actions: workflow run
`43552132296` (`deploy-azure.yml`, `deploy=true`, `run_day=3`, `defect=none`)
signed in with OIDC, validated and deployed target `azure_ci` (26 created:
13 resources and their permissions) and ran `adp_platform_job` (job
`1023469102611052`, `run_as` = `id-adp-github-deploy`). Before it, the Track 4
schemas and tables were handed to the service principal (16 grant statements,
`docs/adp/azure-setup.md` §3) and the personal `azure_dev` deployment was
destroyed (13 deleted; tables kept).

It shows recovery after a fixed source, matching the local engine for the same
sequence: `sales.order_lines:day3:6` succeeded with 198 new rows, its watermark
moved from 2026-11-03T19:59:07 to 2026-11-04T19:41:23 [235,3]; bronze
order_lines 402 → 600; orders and payments read 0 rows and opened
`day3:sales.orders:no_new_data` and `day3:sales.payments:no_new_data` (one row
each), which ends the run red by design. Reconciliation passed; gold unchanged
(order dates 2026-11-02 and 2026-11-03 only).

## Cost evidence

- Compute used: serverless job compute, 6 runs, about 365 s of total run time
  (task execution 326 s); serverless SQL warehouse (Small) for the checks, which
  stops after 10 idle minutes.
- `system.billing.usage` is not readable by this user (no `USE SCHEMA` on
  `system.billing`), and Azure Cost Management had no data yet for the new
  subscription. No measured cost is recorded here.
- Always-on regardless of runs: the workspace's NAT gateway and public IP in
  `rg-adp-dev-bedoux-agentic`.

## Not covered

- Real-model investigation (Claude adapter): not run.
- Defects other than `bad_unit_price` in the workspace; tables were not reset
  between scenarios.
- Tracks 1–3 resources deployed to Azure but not run.
- GitHub OIDC deploy workflow: not configured or run.
