# Track 4 contract: Agentic Data Platform (order-to-cash)

Track 4 adds a metadata-driven ingestion engine, deterministic reconciliation
and three bounded agent workflows to this bundle, targeting Azure Databricks
as well as the existing Free Edition workspace. All data is synthetic.

It reuses earlier tracks instead of copying them:

| Reused | From | Used for |
|---|---|---|
| `bedoux.model_call` (`prepare_payload`, `send_payload`) | Sentinel ch. 03–04 | Every outbound investigator packet: redaction, canary/leak checks, citation resolution |
| `bedoux.boundaries` | Sentinel ch. 06 | Prohibited tool names, instruction-in-evidence signal |
| `bedoux.incidents.IncidentLog` | Sentinel ch. 04 | Append-only incident, tool-call, triage and approval events |
| `aglc.reconcile.reconcile` | Track 3 | Source-to-target daily totals, zero money tolerance |
| `aglc.governance.ident` | Track 3 | Identifier checks in the Databricks tasks |

## Datasets

Specs live in `config/adp/datasets/*.yml` and are validated on load
(`src/adp/metadata.py`). A spec that would make the engine guess fails.

| Dataset | Key | Cursor | Source (simulated) |
|---|---|---|---|
| `sales.orders` | `order_id` | `updated_at` | PostgreSQL table |
| `sales.order_lines` | `order_id, line_no` | `updated_at` | PostgreSQL table |
| `sales.payments` | `payment_id` | `updated_at` | Settlement CSV |

Column types: `int`, `decimal` (exact, quantized to scale), `date`,
`timestamp`, `enum`, `bool`, `string`. Values arrive as strings and are cast;
a value that can't be cast is quarantined, never defaulted.

## Ingestion rules (`src/adp/ingest.py`)

1. Composite cursor `(updated_at, *primary_key)`; rows sharing a timestamp are
   not skipped at a batch boundary.
2. Read window starts `lookback_hours` before the watermark. Replays are
   no-ops: a version replaces the stored one only if its cursor is newer.
3. Missing required column: run fails before any row is read.
   Added column: recorded in `schema_diff`, run continues.
4. Quarantine above `max_quarantine_ratio` of the window fails the run and
   writes nothing.
5. The watermark advances only after a successful run.
6. `is_deleted = true` is a tombstone: the row is kept and excluded from Gold.

## Gold and reconciliation (`src/adp/reconcile.py`)

- `daily_revenue`: paid or shipped orders by order date, Decimal sums.
- `source_to_target`: daily payment totals from the raw extract vs the
  ingested table (Track 3's `reconcile`, tolerance 0).
- `payments_vs_orders`: unpaid, overpaid, underpaid orders and orphan
  payments, with order ids as evidence.

## Monitor and incidents (`src/adp/pipeline.py`)

Rules only. Triggers: `ingestion_failed`, `rows_quarantined`, `no_new_data`,
`schema_drift_additive`, `source_to_target_mismatch`,
`payments_vs_orders_mismatch`. A model never opens or closes an incident.

## Agents

| Agent | Module | What decides | What the model may do |
|---|---|---|---|
| A. Incident investigator | `investigator.py` | `classify()` rules, triage policy, runbook table | Request allowlisted read-only tools; write a cited report with one label |
| B. Quality & reconciliation | `reconcile.py` exposed as the `get_reconciliation` tool | Deterministic checks | Read and explain the report |
| C. SQL modernization | `modernize.py` | Blocker and hazard scan, rewrite rules, fixture validation | Not used; the workflow is deterministic today |

Triage routes an incident to its runbook only when the report validates, its
label equals the rules label and no instruction-like text appeared in the
evidence. Otherwise `needs_human_triage`. Runbooks are keyed by the rules
label. `request_approval` records an approval request; nothing applies a
change (ADR 0009).

Root-cause labels: `SCHEMA_TYPE_CHANGE`, `SCHEMA_COLUMN_REMOVED`,
`SCHEMA_COLUMN_ADDED`, `NULL_PRIMARY_KEY`, `INVALID_DOMAIN_VALUE`,
`DUPLICATE_SOURCE_KEY`, `DUPLICATE_CHARGE`, `MISSING_PAYMENT`, `STALE_SOURCE`,
`LATE_ARRIVAL_BEYOND_LOOKBACK`.

## SQL modernization statuses

`validated` (exact match with an independent reference query on fixtures),
`mismatch`, `execution_error`, `transpile_error`, `needs_manual_redesign`
(procedural constructs, non-deterministic clock functions, or a known
semantic hazard such as `DATEDIFF` with a non-day unit).

## Databricks tables (`resources/adp.yml`)

`adp_platform_job`: `adp_ingest_task` then `adp_reconcile_task` (`run_if:
ALL_DONE`). Job parameters `seed`, `day`, `defect`, `defect_day`.

| Table | Written by | Mode |
|---|---|---|
| `adp_meta.engine_state` | ingest | append (latest row is the state) |
| `adp_meta.ingest_runs` | ingest | append |
| `adp_meta.quarantine` | ingest | append |
| `adp_bronze.bronze_orders`, `bronze_order_lines`, `bronze_payments` | ingest | overwrite from merged state |
| `adp_gold.daily_revenue` | reconcile | overwrite |
| `adp_meta.reconcile_runs`, `adp_meta.incidents` | reconcile | append |

## Known gaps

- Demonstrated in one Azure workspace for days 1–3 with `bad_unit_price`
  (`docs/adp/live-evidence.md`). Other defects, the Free Edition target and the
  GitHub OIDC workflow have not run.
- Audit and incident rows are appended, not keyed by job run. A task retry
  duplicates them; retries are disabled on both tasks for that reason.
- Bronze is overwritten from the engine's merged state rather than written with
  Delta `MERGE`. Correct at this scale; not how a large source should load.
- Engine state is a JSON row. Concurrent runs are prevented by
  `max_concurrent_runs: 1`, not by a transactional watermark table.
- SQL validation runs on DuckDB after a second transpilation. Differences that
  DuckDB shares with T-SQL can hide; `sql17` was one, now blocked by a hazard
  rule. Only Databricks SQL execution would close this.
- The rules classifier and the seeded defects were written together, so its
  accuracy on the eval set is expected, not a generalization result.
- The Claude provider has not been run; no real model results are recorded.
