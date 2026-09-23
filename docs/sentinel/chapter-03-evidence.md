# Chapter 03 evidence-log demonstration evidence

Durable record of the live `dev` workspace evidence collected while running
`workspace.bedoux_silver.gate_evidence_log` for the first time. Mirrors
[chapter-02-evidence.md](chapter-02-evidence.md)'s format: raw values, sourced
directly from `databricks jobs get-run` and the Statement Execution API at the
time each was collected, not reconstructed afterward.

Narrative and design are in
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#append-only-evidence-log-design-this-session).
Exact commands are in
[live-verification.md](live-verification.md#6-chapter-03-evidence-log-demonstration-confirmed-live).
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
for Runs 1 and 2 — a clean pass-state run was the point of that
demonstration; the gate blocking a failing run was already demonstrated
live in chapter 02 (see [chapter-02-evidence.md](chapter-02-evidence.md),
Stage 3). A later, separately authorized session deployed the fault rate
against `gate_evidence_log` specifically (Run 3, below) and then restored
it (Run 4), and ran the append-only negative test (Phase B, below).

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

## Run 3 — failing-gate demonstration (fault deploy, `bedoux_lead_invalid_rate=0.30`)

Separately authorized: deploying the `0.30` fault variable to `dev`,
running the job once under it, then restoring `0.02` and redeploying.
Timestamps below are CLI-local (America/Denver, MDT, UTC-6) with UTC
alongside, same convention as Runs 1–2 used implicitly via `run_start_ts`.

- Deploy: `databricks bundle deploy -t dev --profile bedoux-databricks --var="bedoux_lead_invalid_rate=0.30"`.
  `Files: 67 uploaded, 0 deleted`. `Resources: 0 created, 1 changed, 0
  deleted, 7 unchanged` (changed resource: `bedoux_bronze_pipeline`,
  carrying the new `bedoux.lead_invalid_rate` config).
- Run ID `180753859499836`. Same job ID. Run URL:
  `https://dbc-3f70aae3-11d5.cloud.databricks.com/jobs/133273744478391/runs/180753859499836`.
  Started 2026-09-22 21:00:11 MDT / 2026-09-23T03:00:11.535Z UTC, ended
  2026-09-22 21:05:23 MDT / 2026-09-23T03:05:23.716Z UTC.
- Per-task: `bedoux_bronze_task` `SUCCESS`, `bedoux_silver_task`
  `SUCCESS`, `bedoux_gate_task` **`FAILED`** (job-level retry fired: two
  attempts, both `FAILED`), `bedoux_gold_task` `SKIPPED`
  (`UPSTREAM_FAILED`) — matches the expected shape: leads-only fault
  breaches the gate, Gold never runs.
- Gate failure detail, verbatim from `databricks jobs get-run-output` on
  the final attempt:
  ```
  RuntimeError: Publication gate failed; withholding Gold refresh:
    - leads: gate_passed is false (quarantine rate 32.8%)
  ```
- Quarantine rate per source (from the written row's `sources`, confirmed
  against the failure detail above): `leads` 500 total / 164 quarantined /
  336 accepted / rate `0.328` / `gate_passed=false`; `ops_events` 365 / 8 /
  357 / `0.0219...` / `true`; `web_events` 2000 / 46 / 1954 / `0.023` /
  `true`. Only `leads` breached, as expected — `bedoux_lead_invalid_rate`
  feeds only `bronze.py`'s lead generation.
- **Row count went from 2 to 4, not 2 to 3 — confirming a limitation the
  design doc already predicted (`chapters/03-protect-evidence.md`'s
  "Known limitation, not solved this session"), not a new discovery.**
  `bedoux_gate_task`'s job-level retry (attempt 0, then attempt 1, both
  `FAILED`) ran the evidence-write-then-raise code on *both* attempts,
  appending two rows with identical `run_start_ms` (`1790132411535`) and
  identical content, differing only in `written_ts`
  (`2026-09-23T03:04:54.997Z` vs `2026-09-23T03:05:18.177Z`):
  - `run_start_ms` `1790132411535`, `run_start_ts` `2026-09-23T03:00:11.535Z`,
    `passed` `false`, `problems` `["leads: gate_passed is false (quarantine rate 32.8%)"]`.
  - `sources`: `leads` {quarantined_rows 164, quarantine_rate 0.328,
    gate_passed false, conserved true, total 500, accepted_rows 336};
    `ops_events` {quarantined_rows 8, quarantine_rate
    0.021917808219178082, gate_passed true, conserved true, total 365,
    accepted_rows 357}; `web_events` {quarantined_rows 46, quarantine_rate
    0.023, gate_passed true, conserved true, total 2000, accepted_rows
    1954}. All three `computed_ts` `2026-09-23T03:03:54.172Z` (both copies
    identical — the retry reread the same `gate_status`, it did not
    recompute Silver).
  - Runs 1 and 2's rows were confirmed byte-for-byte unchanged.
  - This is a real gap, named at design time and now empirically
    confirmed: a retried failing run produces a duplicate evidence row,
    not one. Append-only guards against *mutation*, not *duplication* —
    the property held exactly as designed and still let this through,
    because writing twice is not what it exists to prevent. See
    [known-gaps.md](known-gaps.md#durable-incident-evidence-is-manual) for
    where this is now tracked; not investigated or fixed here, since doing
    so is source code work outside a docs-only round's scope.

## Run 4 — restore (`bedoux_lead_invalid_rate=0.02`)

- Restore deploy: `Files: 0 uploaded, 0 deleted`. `Resources: 0 created, 1
  changed, 0 deleted, 7 unchanged`.
- Verified post-deploy via `databricks bundle summary -t dev --profile
  bedoux-databricks --output json`:
  `resources.pipelines.bedoux_bronze_pipeline.configuration."bedoux.lead_invalid_rate"`
  reads `0.02` — checked directly, not assumed from the deploy succeeding.
- Run ID `793561848702599`. Run URL:
  `https://dbc-3f70aae3-11d5.cloud.databricks.com/jobs/133273744478391/runs/793561848702599`.
  Started 2026-09-22 21:06:08 MDT / 2026-09-23T03:06:08.624Z UTC, ended
  2026-09-22 21:12:02 MDT / 2026-09-23T03:12:02.589Z UTC.
- Per-task, all four `SUCCESS` — the workspace is back to a healthy,
  gate-passing state.
- New row: `run_start_ms` `1790132768624`, `run_start_ts`
  `2026-09-23T03:06:08.624Z`, `passed` `true`, `problems` `[]`, `leads`
  quarantine rate `0.02` (matching baseline). Row count after Run 4: `5`.
- Job-run budget for this fault/restore sequence: exactly 2 runs, as
  authorized (Run 3 fault, Run 4 restore).

## Phase B — append-only negative test

Run once both a passing and a failing row already existed (after Run 3).
Targeted two real, existing, passing rows by `run_start_ms`.

1. `UPDATE workspace.bedoux_silver.gate_evidence_log SET passed = false
   WHERE run_start_ms = 1790121847100` (Run 1's row) — **FAILED**,
   verbatim:
   ```
   [DELTA_CANNOT_MODIFY_APPEND_ONLY] This table is configured to only
   allow appends. If you would like to permit updates or deletes, use
   'ALTER TABLE null SET TBLPROPERTIES (delta.appendOnly=false)'.
   ```
   `sql_state: 42809`.
2. `DELETE FROM workspace.bedoux_silver.gate_evidence_log WHERE
   run_start_ms = 1790122433585` (Run 2's row) — **FAILED**, identical
   error text and `sql_state`.
3. Re-`SELECT` after both attempts: row count still `5`; all rows,
   including the two targeted, confirmed byte-for-byte identical to their
   content before the attempts — full-column comparison, not just a row
   count.

This is the specific claim `known-gaps.md` flagged as unobserved: the
property's *presence* was confirmed live in Runs 1–2 (`SHOW
TBLPROPERTIES`); its *rejection behavior* under an actual mutation attempt
is confirmed here. Scope: `UPDATE` and `DELETE` only, against real rows.
No `MERGE`, `INSERT OVERWRITE`, `REPLACE TABLE`, `DROP`, or property
change was attempted — this proves the table rejects those two specific
operations, not that it is immutable against every possible operation.

## What this file does not contain

- Full `sources` array content for Run 2 (see Run 2 above) — only the
  distinguishing identity fields were transcribed, since Run 2's purpose
  was to prove append-not-replace, not to re-document identical source
  metrics already recorded for Run 1.
- A fix or further investigation of Run 3's duplicate-row-on-retry
  finding — recorded above and in `known-gaps.md`, not addressed, since a
  code fix is outside a docs-only round's scope.
- A test of `MERGE`, `INSERT OVERWRITE`, `REPLACE TABLE`, `DROP`, or an
  `ALTER TABLE ... SET TBLPROPERTIES` attempt against this table — Phase
  B's scope was `UPDATE`/`DELETE` only, per explicit authorization.
