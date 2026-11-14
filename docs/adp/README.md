# Track 4 guide: Agentic Data Platform

Track 4 loads a synthetic retail order-to-cash domain (orders, order lines,
payments) incrementally into Unity Catalog, reconciles it to the cent, and uses
bounded agents to investigate incidents and modernize legacy SQL. Rules make
every decision; a model explains, and a person approves any change.

This guide is for someone who wants to run it, read its output, or judge the
evidence. The binding rules are in the [contract](../contracts-adp.md); the
decisions behind them are ADRs [0007](../adr/0007-shared-engine-thin-platform-tasks.md),
[0008](../adr/0008-rules-decide-models-explain.md) and
[0009](../adr/0009-agents-propose-humans-apply.md). All data is fictional.

<p align="center"><img src="diagrams/01-platform-overview.svg" width="960" alt="Track 4 overview: synthetic sources flow through the ingest task into Unity Catalog schemas adp_meta, adp_bronze and adp_gold; the reconcile task checks them; rules open incidents; Agent A investigates and its label is acted on only when it matches the rules; Agent C modernizes SQL; GitHub Actions deploys through OIDC."></p>

## Contents

1. [Try it locally](#1-try-it-locally)
2. [How one run works](#2-how-one-run-works)
3. [Reconciliation and incidents](#3-reconciliation-and-incidents)
4. [The agents](#4-the-agents)
5. [Run it on Azure Databricks](#5-run-it-on-azure-databricks)
6. [Read the results](#6-read-the-results)
7. [Evidence](#7-evidence)
8. [Limits](#8-limits)

## 1. Try it locally

No workspace or model is needed. Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv sync --locked
uv run --locked python -m pytest -q                 # unit tests
uv run --locked python scripts/adp_demo.py          # one incident end to end + one SQL migration
uv run --locked python scripts/adp_demo.py --defect late_arrival
uv run --locked python scripts/adp_eval.py          # offline evaluation (fake agent)
```

The demo prints three simulated days, the incident it opened, every tool call
the investigator made, the triage decision, the approval request, and a T-SQL
query translated and validated against a reference query. The default provider
is a deterministic fake, so the demo measures the harness, not a model.

## 2. How one run works

`adp_platform_job` runs `adp_ingest_task`, then `adp_reconcile_task`. The ingest
task processes each dataset spec in [`config/adp/datasets/`](../../config/adp/datasets/)
through the same engine the tests use ([`src/adp/ingest.py`](../../src/adp/ingest.py)).

<p align="center"><img src="diagrams/02-ingestion-run.svg" width="960" alt="One ingestion run: load spec, schema diff, read window, validate rows with quarantine, quarantine ratio check, merge, advance watermark; failures stop before writing and hold the watermark; every run writes an audit record."></p>

The watermark is a composite cursor, `(updated_at, primary key)`, and every
read starts 24 hours before it. Rows that share a timestamp are not skipped,
re-reading old rows changes nothing, and a row that arrives late but inside the
window is picked up. A row older than the window is missed on purpose and caught
by reconciliation instead.

<p align="center"><img src="diagrams/03-cursor-lookback.svg" width="960" alt="Timeline of the composite cursor and 24-hour lookback window, showing a tie resolved by primary key, a late row inside the window picked up, a late row outside it caught by reconciliation, and a re-read row that is a no-op."></p>

## 3. Reconciliation and incidents

After ingestion, the reconcile task rebuilds `adp_gold.daily_revenue` and runs
two exact Decimal checks. Rules, never a model, turn their results into
incidents. Any incident ends the run red on purpose: the failed run is the alert.

<p align="center"><img src="diagrams/04-reconciliation.svg" width="960" alt="Reconciliation: gold daily revenue, source-to-target daily payment totals with zero tolerance, and payments-versus-orders anti-joins, feeding six rule-based incident triggers."></p>

## 4. The agents

**Agent A, the incident investigator** ([`src/adp/investigator.py`](../../src/adp/investigator.py)),
may only call six read-only tools, at most five times, and every outbound
packet goes through Sentinel's guarded model path. Its root-cause label counts
only when it equals the rules classifier's label; then the incident is routed to
the runbook for that label and an approval request is logged. Nothing is applied
automatically.

<p align="center"><img src="diagrams/05-incident-triage.svg" width="960" alt="Agent A: an incident enters a bounded loop where the model requests allowlisted read-only tools through a gate and receives redacted evidence; its cited report is compared with the rules label; agreement routes to a runbook and an approval request, disagreement goes to a human."></p>

Every claim in a report must cite evidence the model was actually sent. One bad
citation refuses the whole report and sends the incident to a person.

<p align="center"><img src="diagrams/06-citation-guard.svg" width="960" alt="Citation guard decision flow: missing or malformed citations, unresolved paths and redacted values are refused; empty containers and visible values are allowed; a report that leaks a sensitive value is refused."></p>

**Agent C, the SQL modernizer** ([`src/adp/modernize.py`](../../src/adp/modernize.py)),
is deterministic today. It refuses procedural T-SQL, applies rewrite rules where
a plain transpile would change results, and accepts a translation only when it
returns exactly what an independently written reference query returns on the
fixtures.

<p align="center"><img src="diagrams/07-sql-modernizer.svg" width="960" alt="SQL modernizer pipeline: blocker scan, SQLGlot transpile, semantic hazard check, rewrite rules, and validation on DuckDB fixtures against a reference query, with outcome statuses."></p>

```bash
uv run --locked python -c "
from src.adp import modernize
r = modernize.modernize('SELECT customer_id, LEN(name) AS n FROM customers ORDER BY customer_id',
                        'SELECT customer_id, length(rtrim(name)) AS n FROM customers ORDER BY customer_id',
                        modernize.fixture_connection())
print(r['status'], r['rewrites']); print(r['databricks_sql'])"
# validated ['len_ignores_trailing_spaces']  ->  LENGTH(RTRIM(CAST(name AS STRING)))
```

## 5. Run it on Azure Databricks

<p align="center"><img src="diagrams/08-cicd-deploy.svg" width="960" alt="CI/CD: pull requests run tests and validation and main deploys Free Edition; the manual deploy-azure workflow signs in through GitHub OIDC to a managed identity, then validates, deploys and runs the azure_ci target as a service principal."></p>

**From GitHub (recommended).** Run the *Deploy to Azure Databricks* workflow
from `main`. It signs in through OIDC, so no secret is stored.

| Input | Meaning |
|---|---|
| `deploy` | Unchecked: tests and `bundle validate` only. Checked: also deploy target `azure_ci`. |
| `run_day` | `1`, `2` or `3`: after deploying, run `adp_platform_job` for that simulated day. Empty: don't run. |
| `defect` | `none` or one of `bad_unit_price`, `removed_column`, `added_column`, `null_key`, `invalid_status`, `duplicate_key`, `duplicate_charge`, `missing_payment`, `stale_source`, `late_arrival`. Injected on `run_day`; the generator accepts defects only on day 2 or 3 (`late_arrival` only on day 3). |

```bash
gh workflow run deploy-azure.yml --ref main -f deploy=false
gh workflow run deploy-azure.yml --ref main -f deploy=true -f run_day=2 -f defect=duplicate_charge
```

**From your machine.** You need workspace access and a Databricks CLI profile
(setup and the verified environment: [`azure-setup.md`](azure-setup.md)).

```bash
databricks bundle validate --target azure_ci --profile ADP_AZURE
databricks bundle deploy   --target azure_ci --profile ADP_AZURE
databricks bundle run adp_platform_job --target azure_ci --profile ADP_AZURE --params day=3,defect=late_arrival,defect_day=3
```

Run days in order. Re-running a day is safe: unchanged rows are no-ops and the
watermark only moves after success. Starting over means dropping the
`adp_meta`, `adp_bronze` and `adp_gold` schemas, which deletes the evidence
tables; do it deliberately.

## 6. Read the results

Everything a run did is in the catalog (`adb_adp_dev` on Azure):

```sql
-- One audit row per dataset per run
SELECT run_id, status, get_json_object(record, '$.failure_code') AS failure,
       get_json_object(record, '$.rows_new') AS rows_new,
       get_json_object(record, '$.quarantined') AS quarantined,
       get_json_object(record, '$.watermark_after') AS watermark
FROM adb_adp_dev.adp_meta.ingest_runs ORDER BY saved_ts DESC;

-- Rejected rows keep their raw values and reasons
SELECT run_id, raw, problems FROM adb_adp_dev.adp_meta.quarantine ORDER BY saved_ts DESC LIMIT 20;

-- Incidents opened by the rules, and reconciliation reports
SELECT saved_ts, incident_key, trigger FROM adb_adp_dev.adp_meta.incidents ORDER BY saved_ts DESC;
SELECT saved_ts, day, passed FROM adb_adp_dev.adp_meta.reconcile_runs ORDER BY saved_ts DESC;

SELECT * FROM adb_adp_dev.adp_gold.daily_revenue ORDER BY business_date;
```

| Status or code | Means |
|---|---|
| `succeeded`, `succeeded_with_quarantine` | Loaded; bad rows (if any) quarantined under the 2 % limit; watermark advanced. |
| `failed` + `quarantine_ratio_exceeded` | Too many bad rows; nothing written; watermark held. Fix the source and re-run. |
| `failed` + `schema_required_column_missing` | A required column vanished; failed before reading. |
| incident `no_new_data` | The day had already been loaded (or the source is stale). |
| triage `routed_to_runbook` | The model's label matched the rules; an approval request was logged. |
| triage `needs_human_triage` | Disagreement, a refused citation or suspicious evidence; a person decides. |

## 7. Evidence

Six job runs in Azure, each checked against the local engine for the same
inputs ([`live-evidence.md`](live-evidence.md)):

<p align="center"><img src="diagrams/09-live-runs-timeline.svg" width="960" alt="Timeline of six Azure runs: day 1 and day 2 succeed, a repeat finds no new data, a bad-price defect is quarantined with the watermark held, a retry check confirms one attempt per task, and a CI run as the service principal recovers the fixed source."></p>

A real model, Azure OpenAI `gpt-5.4-mini`, ran the 30 incident cases five times
under a hard spend cap ([`evaluation-results-azure-openai.md`](evaluation-results-azure-openai.md)).
The scripted fake agent's results are kept apart in
[`evaluation-results.md`](evaluation-results.md).

<p align="center"><img src="diagrams/10-eval-variance.svg" width="960" alt="Stacked bars for five evaluation runs of 30 cases: correct labels routed, wrong labels sent to a human, and refused citations; run one used the old citation guard; runs two to five average 26.5 routed with zero forbidden tool executions."></p>

## 8. Limits

- All data is synthetic, and the incident cases were written alongside the rules
  classifier, so its accuracy on them is expected rather than a generalization result.
- Bronze is overwritten from the engine's merged state, and engine state is one
  JSON row per run: fine at this scale, not how a large source should load.
- SQL validation runs on DuckDB; Databricks SQL execution would be the stronger check.
- Real-model results describe one smaller model over five runs; Claude has not
  been evaluated.
- The full list is in the contract's [known gaps](../contracts-adp.md#known-gaps).

The diagrams are hand-written animated SVG in [`diagrams/`](diagrams/); they
follow your system's light or dark setting and stop moving when reduced motion
is requested (except for small moving markers).
