# Chapter 02 demonstration evidence

Durable record of the live `dev` workspace evidence collected during chapter
02's incident, fix, and fault → restore → replay demonstration. Quarantine
tables are recomputed each run, so their fault-stage contents are already
gone from the live workspace — this file is the only surviving record of
several of these numbers, sourced from the session transcripts and the
chapter doc/handoff at the time each value was collected. **Not regenerated
for this file; no jobs were re-run to produce it.** Where a value was not
separately captured at the time, this says so explicitly rather than
reconstructing or estimating it.

Narrative and analysis are in
[chapters/02-quality-gate.md](chapters/02-quality-gate.md) ("Incident" and
"Fault → restore → replay demonstration" sections). This file is the
supporting raw evidence table.

## Commands used throughout (profile `bedoux-databricks`, target `dev`)

```bash
databricks bundle validate --target dev --profile bedoux-databricks --var bedoux_lead_invalid_rate=<rate>
databricks bundle plan --target dev --profile bedoux-databricks --var bedoux_lead_invalid_rate=<rate>
databricks bundle deploy --target dev --profile bedoux-databricks --var bedoux_lead_invalid_rate=<rate> --fail-on-active-runs
databricks bundle run bedoux_analytics_job --target dev --profile bedoux-databricks --var bedoux_lead_invalid_rate=<rate>
databricks jobs get-run <run_id> --profile bedoux-databricks -o json
databricks jobs list-runs --job-id 133273744478391 --active-only --profile bedoux-databricks -o json
```

Gate evidence and persisted-table counts, via the Statement Execution API
(`databricks api post /api/2.0/sql/statements`, warehouse
`e63747243511532c`):

```sql
SELECT * FROM workspace.bedoux_silver.gate_status ORDER BY source;

SELECT 'leads_clean' t, count(*) c FROM workspace.bedoux_silver.leads_clean
UNION ALL SELECT 'leads_quarantine', count(*) FROM workspace.bedoux_silver.leads_quarantine
UNION ALL SELECT 'web_events_clean', count(*) FROM workspace.bedoux_silver.web_events_clean
UNION ALL SELECT 'web_events_quarantine', count(*) FROM workspace.bedoux_silver.web_events_quarantine
UNION ALL SELECT 'ops_events_clean', count(*) FROM workspace.bedoux_silver.ops_events_clean
UNION ALL SELECT 'ops_events_quarantine', count(*) FROM workspace.bedoux_silver.ops_events_quarantine;
```

Gold digests, order-independent (via the same Statement Execution API):

```sql
SELECT count(*) as cnt,
       sha2(concat_ws('||', sort_array(collect_list(md5(to_json(struct(*)))))), 256) as digest
FROM workspace.bedoux_gold.<table>;
```

`updated_at` via `databricks tables get workspace.bedoux_gold.<table> -o json`.

## Reference values: confirmed-good baseline

These three digests recur, byte-for-byte identical, across every stage
except the incident run (Stage 1) — captured in full here once:

| Table | Rows | Digest (SHA-256, full) |
|---|---|---|
| `gold_campaign_performance` | 30 | `72575a78e486b264ea3dfbc694b22354922cc8a5312c655275ea4fce8a805dba` |
| `gold_client_funnel` | 132 | `636c7dd090679329760bedf55184d792c631fbb92ab61aee36af4672d7df1c2e` |
| `gold_ogi_ops_health` | 183 | `72aef48d2680f7120cc2bb60b14bd7ebae73db4f5cec4812bf9449192083e41d` |

Original pre-chapter-02 `updated_at` (before any chapter 02 deploy):
`gold_campaign_performance` 2026-07-30T20:41:58.494Z,
`gold_client_funnel` 2026-07-30T20:42:03.654Z,
`gold_ogi_ops_health` 2026-07-30T20:41:58.483Z.

## Stage 1 — Incident: first healthy-baseline run (0.02), found the defect

- Commit deployed: `281efe0c11389e043c1c7bc2082462864bde7acb`.
- Run ID `343186547330463`. Started 2026-09-21T23:37:51Z, ended 23:43:46Z (UTC).
- Per-task: `bedoux_bronze_task` SUCCESS, `bedoux_silver_task` SUCCESS,
  `bedoux_gate_task` SUCCESS (wrongly), `bedoux_gold_task` SUCCESS (wrongly
  ran and overwrote the baseline).
- `gate_status` (all wrong, product of the `array_remove(..., None)` defect):
  `leads`/`web_events`/`ops_events` each `total` matching Bronze's row count
  (500/2000/365), `quarantined=0`, `quarantine_rate=0.0`, `gate_passed=true`.
  `_computed_ts` 2026-09-21T23:40:51.869Z for all three. (This table did not
  yet have `accepted_rows`/`quarantined_rows`/`conserved` columns — those
  were added by the fix.)
- Persisted Silver counts: `leads_clean` 0, `leads_quarantine` 0,
  `web_events_clean` 0, `web_events_quarantine` 0, `ops_events_clean` 0,
  `ops_events_quarantine` 0, `quality_metrics` 0 rows — all empty despite
  2,865 Bronze rows (500+2000+365) as input.
- Gold after this run: `gold_campaign_performance` 30 rows (every row
  `lead_count=0`, `cost_per_lead=NULL`), `gold_client_funnel` 0 rows,
  `gold_ogi_ops_health` 0 rows. **Digest of this broken state: not
  captured** — the incident was characterized via row counts and sampled
  row content (`lead_count`/`cost_per_lead` values), not a digest query, and
  this state no longer exists to re-query.
- Pipeline update IDs: bronze `bd8fee68-1a78-4f95-b5e7-8fb123e224d7`, silver
  `adc3328b-e2cc-4caa-88a2-a420099f34c4`, gold
  `664c30db-3e65-44e0-ae2b-bba1a04b97e7`.

## Stage 2 — Re-run after the fix (0.02), confirms the fix live

- Commit deployed: `9d3ca54`, verified by diffing the deployed `silver.py`
  byte-for-byte against the local checkout (identical).
- Run ID `470702296963638`. CLI-local timestamps 2026-09-21 18:09:32 (start)
  – 18:15:15 (end) [as displayed by `databricks bundle run`, not converted].
- Per-task: all four `SUCCESS`.
- `gate_status`: `leads` total 500 / quarantined 10 / accepted_rows 490 /
  quarantined_rows 10 / rate 0.02 / `gate_passed=true` / `conserved=true`;
  `web_events` total 2000 / quarantined 46 / accepted_rows 1954 /
  quarantined_rows 46 / rate 0.023 / true / true; `ops_events` total 365 /
  quarantined 8 / accepted_rows 357 / quarantined_rows 8 / rate
  0.021917808219178082 / true / true. `_computed_ts`
  2026-09-22T00:12:43.113Z (UTC) for all three.
- Persisted Silver counts, directly queried: `leads_clean` 490,
  `leads_quarantine` 10, `web_events_clean` 1954, `web_events_quarantine`
  46, `ops_events_clean` 357, `ops_events_quarantine` 8, `quality_metrics`
  6 rows — exact match to `gate_status`'s own numbers.
- Gold: all three digests match the reference values above. `updated_at`:
  `gold_campaign_performance` 2026-09-22T00:15:07.964Z, `gold_client_funnel`
  2026-09-22T00:15:07.146Z, `gold_ogi_ops_health` 2026-09-22T00:15:07.112Z.

## Stage 3 — Fault (`bedoux_lead_invalid_rate=0.30`)

- Commit deployed: HEAD was `f63f113` at the time (no `src/bedoux/*.py`
  changes landed between `9d3ca54` and `f63f113` — the intervening commits
  were documentation-only — so the deployed pipeline code was unchanged from
  Stage 2's byte-for-byte-verified state; **not independently re-diffed this
  specific stage**).
- Run ID `330174171866992`. CLI-local timestamps 2026-09-21 18:33:28 –
  18:38:31.
- Per-task: `bedoux_bronze_task` SUCCESS, `bedoux_silver_task` SUCCESS,
  `bedoux_gate_task` FAILED (two attempts, both failed identically —
  `run_id` `1120999432455002` attempt 0 and `225588360547798` attempt 1;
  Databricks' own retry, not configured by this pipeline), `bedoux_gold_task`
  SKIPPED (`UPSTREAM_FAILED`).
- `gate_status`: `leads` total 500 / quarantined 164 / accepted_rows 336 /
  quarantined_rows 164 / rate 0.328 (32.8%) / **`gate_passed=false`** /
  **`conserved=true`**; `web_events` total 2000 / quarantined 46 / rate
  0.023 / true / true; `ops_events` total 365 / quarantined 8 / rate
  0.021917808219178082 / true / true. `_computed_ts`
  2026-09-22T00:37:05.554Z (UTC) for all three.
- Predicted (before the run): leads 336 accepted / 164 quarantined / 32.80%.
  Observed: exact match.
- Persisted Silver counts: **not independently re-queried this stage** —
  `gate_status`'s own `accepted_rows`/`quarantined_rows` fields (336/164)
  are the evidence of record; the persisted-table cross-check was done
  explicitly in Stages 2 and 5, not repeated here.
- Gold: all three digests **unchanged** from the reference values (confirmed
  by direct query after this run). `updated_at` unchanged from Stage 2's
  values (2026-09-22T00:15:07.9xxZ) — **predating this run's start
  entirely**, not merely "unchanged since last checked."

## Stage 4 — Restore (`bedoux_lead_invalid_rate=0.02`, explicit)

- Did not assume reversion: explicitly re-validated, re-planned, redeployed,
  and confirmed the live pipeline config read back `"0.02"` before running.
- Commit deployed: HEAD `f63f113` (same basis as Stage 3).
- Run ID `262274593519322`. CLI-local timestamps 2026-09-21 18:40:19 –
  18:46:24.
- Per-task: all four `SUCCESS`.
- `gate_status`: `leads` total 500 / quarantined 10 / accepted_rows 490 /
  quarantined_rows 10 / rate 0.02 / true / true; `web_events` total 2000 /
  quarantined 46 / rate 0.023 / true / true; `ops_events` total 365 /
  quarantined 8 / rate 0.021917808219178082 / true / true. `_computed_ts`
  2026-09-22T00:44:20.768Z (UTC).
- Persisted Silver counts: **not independently re-queried this stage**
  (see Stage 3's note — same basis).
- Gold: all three digests match the reference values. `updated_at`
  **advanced**: `gold_campaign_performance` 2026-09-22T00:46:17.881Z,
  `gold_client_funnel` 2026-09-22T00:46:18.063Z, `gold_ogi_ops_health`
  2026-09-22T00:46:18.041Z — a genuine re-derivation onto identical content,
  not Gold sitting untouched by coincidence.

## Stage 5 — Replay (`bedoux_lead_invalid_rate=0.02`, no config change)

- Ran immediately after Stage 4 with no deploy in between (nothing changed
  to deploy).
- Commit deployed: HEAD `f63f113` (unchanged from Stages 3–4).
- Run ID `98756061776337`. CLI-local timestamps 2026-09-21 19:20:43 –
  19:26:50.
- Per-task: all four `SUCCESS`.
- `gate_status`: identical to Stage 4 in every numeric field (`leads`
  500/10/490/10/0.02/true/true; `web_events` 2000/46/.../true/true;
  `ops_events` 365/8/.../true/true), but `_computed_ts`
  **2026-09-22T01:24:03.322Z** — advanced from Stage 4's
  2026-09-22T00:44:20.768Z, confirming fresh evidence each run, not stale
  evidence reused.
- Persisted Silver counts, directly re-queried: `leads_clean` 490,
  `leads_quarantine` 10, `web_events_clean` 1954, `web_events_quarantine`
  46, `ops_events_clean` 357, `ops_events_quarantine` 8 — exact match to
  Stage 4.
- Gold: all three digests match the reference values again. `updated_at`
  advanced again: `gold_campaign_performance` 2026-09-22T01:26:34.331Z,
  `gold_client_funnel` 2026-09-22T01:26:34.823Z, `gold_ogi_ops_health`
  2026-09-22T01:26:34.840Z.

## First-ever CI deployment (post-merge, `main`)

- Merge commit `f8ae89d097c58139fab6808083925a9ca2199a5c` (PR #3). CI run
  triggered on push to `main`.
- `Deploy bundle` job ran `databricks bundle deploy --target dev` via the
  configured PAT and succeeded; `run_job` correctly stayed skipped (not
  opted into that dispatch).
- Verified afterward, read-only, against the live workspace: `job_id`
  `133273744478391` (`bedoux_analytics_job`) unchanged, no duplicate job;
  all three `bedoux_*_pipeline` `pipeline_id`s unchanged, no duplicates;
  job graph still `bedoux_bronze_task` → `bedoux_silver_task` →
  `bedoux_gate_task` → `bedoux_gold_task`; Bronze pipeline configuration
  still `bedoux.lead_invalid_rate: "0.02"`. Gold's three digests unchanged
  (deploy does not run anything). **Deployed source was not re-diffed
  file-by-file for this step** — verified via matching resource IDs/config
  plus CI's own `Unit tests`/`Validate bundle` passing from that exact
  commit, not a separate `workspace export` diff.

## What this file does not contain

- The incident run's (Stage 1) broken Gold digest — never captured, and the
  state no longer exists to re-query.
- Persisted Silver table counts for Stages 3 and 4 as a separately-run
  query — only `gate_status`'s own fields are recorded for those two
  stages; Stages 2 and 5 have the independent cross-check.
- Anything about a fault run against the *fixed* code that also exercised
  `expect_or_fail` or produced `conserved=false` — neither has ever
  happened live; see `docs/sentinel/known-gaps.md`.
