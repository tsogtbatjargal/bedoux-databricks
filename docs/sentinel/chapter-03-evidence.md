# Chapter 03 evidence-log demonstration evidence

Durable record of the live `dev` workspace evidence collected while running
`workspace.bedoux_silver.gate_evidence_log` for the first time. Mirrors
[chapter-02-evidence.md](chapter-02-evidence.md)'s format: raw values, sourced
directly from `databricks jobs get-run` and the Statement Execution API at the
time each was collected, not reconstructed afterward.

Narrative and design are in
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#append-only-evidence-log-design-this-session).
Exact commands are in
[live-verification.md](live-verification.md#6-chapter-03-evidence-log-demonstration-partially-run).
This file is the supporting raw evidence table.

Deployed code: commit `7856b78` (PR #11, the sixth CI deployment, merged
before this session). No `src/bedoux/*.py` changes landed between that
deploy and these runs — the two doc-only commits made this session
(`edca215` on `chore/evidence-log-demo`, and `af309b1`/`b7e8bb9` already on
`main`) did not touch bundle paths and did not redeploy.

## Commands used (profile `bedoux-databricks`, target `dev`)

```bash
databricks bundle run bedoux_analytics_job --profile bedoux-databricks
databricks jobs get-run <run_id> --profile bedoux-databricks
databricks api post /api/2.0/sql/statements --profile bedoux-databricks --json '{
  "warehouse_id": "e63747243511532c",
  "statement": "SELECT run_start_ms, run_start_ts, written_ts, passed, problems, sources FROM workspace.bedoux_silver.gate_evidence_log ORDER BY written_ts"
}'
databricks api post /api/2.0/sql/statements --profile bedoux-databricks --json '{
  "warehouse_id": "e63747243511532c",
  "statement": "SHOW TBLPROPERTIES workspace.bedoux_silver.gate_evidence_log"
}'
```

The `bedoux_lead_invalid_rate` fault variable was left at its default `0.02`
for both runs — a clean pass-state run is the point of this demonstration;
the gate blocking a failing run was already demonstrated live in chapter 02
(see [chapter-02-evidence.md](chapter-02-evidence.md), Stage 3).

## Run 1 — first-ever write to `gate_evidence_log`

- Run ID `649621694823474`. Job ID `133273744478391`. Run URL:
  `https://dbc-3f70aae3-11d5.cloud.databricks.com/jobs/133273744478391/runs/649621694823474`.
  Started 2026-09-22 18:04:07, ended 18:13:01 (CLI-local timestamps as
  displayed by `databricks bundle run`).
- Per-task, all four `SUCCESS`: `bedoux_bronze_task`, `bedoux_silver_task`,
  `bedoux_gate_task`, `bedoux_gold_task`.
- `gate_evidence_log` row written this run:
  - `run_start_ms` `1790121847100`, `run_start_ts` `2026-09-23T00:04:07.100Z`,
    `written_ts` `2026-09-23T00:09:03.848Z`, `passed` `true`, `problems` `[]`.
  - `sources`: `leads` total 500 / quarantined 10 / accepted_rows 490 /
    quarantined_rows 10 / rate 0.02 / `gate_passed=true` / `conserved=true`;
    `web_events` total 2000 / quarantined 46 / accepted_rows 1954 /
    quarantined_rows 46 / rate 0.023 / true / true; `ops_events` total 365 /
    quarantined 8 / accepted_rows 357 / quarantined_rows 8 / rate
    0.021917808219178082 / true / true. All three `computed_ts`
    `2026-09-23T00:08:00.507Z`.
- Cross-checked against `gate_status` from the same run, queried
  separately: identical `total`/`quarantined`/`accepted_rows`/
  `quarantined_rows`/`quarantine_rate`/`gate_passed`/`conserved` for all
  three sources, and identical `_computed_ts` (`2026-09-23T00:08:00.507Z`).
  The evidence log does not disagree with the gate it is logging.
- Table properties (`SHOW TBLPROPERTIES`), confirmed live on the table as
  actually created by this run's write, not merely present in the creation
  code: `delta.appendOnly` = `true`. (Also present: `delta.minWriterVersion`
  `7`, `delta.minReaderVersion` `3`, `delta.enableRowTracking` `true`,
  `delta.enableDeletionVectors` `true`, `delta.feature.appendOnly` =
  `supported` — all consistent with a genuine Delta table property, not a
  string stored in a comment or elsewhere.)
- Row count after Run 1: `1`.

## Run 2 — confirms append, not replace

- Run ID `102698121895581`. Same job ID. Run URL:
  `https://dbc-3f70aae3-11d5.cloud.databricks.com/jobs/133273744478391/runs/102698121895581`.
  Started 2026-09-22 18:13:53, ended 18:19:39.
- Per-task, all four `SUCCESS` again.
- Row count after Run 2: `2` — not `1`. Full ordered query
  (`run_start_ms`, `run_start_ts`, `written_ts`, `passed`):
  - `1790121847100` / `2026-09-23T00:04:07.100Z` /
    `2026-09-23T00:09:03.848Z` / `true` — Run 1's row, **byte-for-byte
    unchanged** from the values recorded above.
  - `1790122433585` / `2026-09-23T00:13:53.585Z` /
    `2026-09-23T00:17:50.502Z` / `true` — Run 2's row, distinguishable from
    Run 1 by `run_start_ms`/`run_start_ts`/`written_ts`.
- Full `sources` content for Run 2 was not re-transcribed here beyond the
  distinguishing fields above — the same `SELECT ... ORDER BY written_ts`
  query used for Run 1 returned it as the second array element; the point
  of this run was to prove appended-not-replaced, which the row count and
  unchanged first row already establish. `problems` was `[]` and `passed`
  was `true` for Run 2 as well (default fault rate, same as Run 1).
- This is the specific property that distinguishes `gate_evidence_log` from
  the `<source>_quarantine` tables that made the durable-evidence gap real
  in chapter 02 (`known-gaps.md`, "Durable incident evidence is manual") —
  those are recomputed and overwritten each run; this table accumulated a
  second row instead of replacing the first.

## What this file does not contain

- A negative test of `delta.appendOnly`'s enforcement (an attempted
  `UPDATE`/`DELETE`/`MERGE` against the table, expected to fail). That is
  destructive SQL and was not run this session — not authorized without a
  separate explicit decision. The property's *presence*, genuinely set on
  the live table (not merely requested in the creation code), is confirmed
  above via `SHOW TBLPROPERTIES`; its *rejection behavior* under a mutation
  attempt remains unobserved live. See
  [known-gaps.md](known-gaps.md#durable-incident-evidence-is-manual).
- A failing-gate run's `gate_evidence_log` row. Both runs this session used
  the default `bedoux_lead_invalid_rate=0.02` (a passing configuration) —
  deliberately, per this session's scope: the gate blocking a failing run
  was already demonstrated live in chapter 02, and widening the fault
  setting was explicitly not authorized this session.
- Full `sources` array content for Run 2 (see above) — only the
  distinguishing identity fields were transcribed, since Run 2's purpose
  was to prove append-not-replace, not to re-document identical source
  metrics already recorded for Run 1.
