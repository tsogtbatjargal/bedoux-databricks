# Layer Contracts — Track 2: Bedoux Ops & Marketing Analytics

Companion to [`contracts.md`](contracts.md) (Track 1, TPC-H). Same methodology,
applied to a fictional small-agency domain modeled on what Bedoux actually does:
run marketing campaigns for clients, track leads through a funnel, and — as its own
ops data source — operate `ogi`, an AI agent that runs a daily plan and answers
Telegram messages.

**All data in this track is synthetic and fictional.** Client names, campaigns, and
leads are generated, not real. This is a deliberate choice, not an oversight: Databricks
Free Edition's terms restrict the workspace to non-commercial use, so this track is
built and labeled as a portfolio demonstration, never as Bedoux's real operational data.

Source: a deterministic synthetic generator (`src/bedoux/generator.py`), fixed seed,
no external data source, no network access required.
Catalog: `workspace`. One schema per layer: `bedoux_bronze`, `bedoux_silver`,
`bedoux_gold` — distinct from Track 1's `bronze`/`silver`/`gold` schemas so the two
tracks never collide.

---

## Naming (locked)

| Layer  | Schema             | Table name pattern  | Example                  |
|--------|--------------------|----------------------|---------------------------|
| Bronze | `workspace.bedoux_bronze` | `<source>_raw`  | `leads_raw`               |
| Silver | `workspace.bedoux_silver` | `<source>_clean`| `leads_clean`             |
| Gold   | `workspace.bedoux_gold`   | `gold_<question>`| `gold_campaign_performance` |

A Bronze table never lives in Silver or Gold. A Silver table never lives in Bronze or
Gold. A Gold table never lives in Bronze or Silver.

---

## Source entities

| Entity | Description |
|---|---|
| `clients` | Fictional agency clients Bedoux runs marketing for. Slowly changing (name, tier can change). |
| `campaigns` | Marketing campaigns per client: channel, budget, start/end date. Slowly changing (budget/status can change). |
| `leads` | Leads generated per campaign, with a funnel stage: `new` → `qualified` → `won`/`lost`. Detail grain, immutable once landed. |
| `web_events` | Website session/pageview events, attributed to a campaign via a synthetic UTM-style tag. Detail grain. |
| `ops_events` | ogi's own operational log: one row per daily-plan run or Telegram message handled, with a success/failure flag and latency. Detail grain. |

---

## Bronze — `workspace.bedoux_bronze`

What it is: a raw landing zone from the synthetic generator. No interpretation,
no filtering. **Not append-only**: unlike Track 1's Bronze, which streams from
a live source and only ever adds rows, Track 2's Bronze is recomputed in full
every pipeline run — see the recompute rule below.

Rules:
- One Bronze table per source entity. 5 tables total: `clients_raw`, `campaigns_raw`,
  `leads_raw`, `web_events_raw`, `ops_events_raw`.
- Add exactly two audit columns:
  - `_ingest_ts` — `current_timestamp()` at load time
  - `_source_table` — the generator entity name, e.g. `bedoux_synthetic.leads`
- Fact tables also carry `_row_id`, the position within the generated list for
  deterministic deduplication. This is not a globally unique batch or run ID.
- Tables are materialized via `@dlt.table` and **recomputed in full each pipeline
  run** directly from the seeded generator — there's no real upstream stream to
  read incrementally, so unlike Track 1's Bronze (which streams from a live source),
  this is an idempotent full recompute by design, not append-only.
- The generator deliberately emits a small percentage (~2%) of invalid rows in
  `leads`, `web_events`, and `ops_events` (e.g. a null key, an out-of-range value) —
  Bronze keeps them as-is; Silver routes invalid fact rows to quarantine. This exists so
  the data-quality gate has something real to catch, not just decorative rules.
- The synthetic lead invalid rate is configurable through
  `bedoux.lead_invalid_rate`, deployed from bundle variable
  `bedoux_lead_invalid_rate` (default `0.02`). Values must be finite and between
  `0` and `1`; malformed settings fail rather than silently falling back. Only
  leads use this override. Restore `0.02` after a fault-injection demonstration.
  Seeds and non-audit business rows are reproducible; audit timestamps are not.

---

## Silver — `workspace.bedoux_silver`

What it is: a clean, conformed copy of Bronze. Still detail grain — no business
logic, no KPIs.

Rules:
- One Silver table per Bronze table, named `<source>_clean`.
- Reads from `workspace.bedoux_bronze` only.
- Clean up: trim strings, cast columns to sensible types, drop rows that fail basic
  validity.
- `clients` and `campaigns` are small, deterministic dimensions — plain
  materialized `@dlt.table`s, deduplicated on their primary key. **Deliberately
  not using Auto CDC here**: CDC/SCD machinery exists to handle genuine
  incremental change capture, which this synthetic, fully-recomputed-each-run
  source doesn't have. Track 1's `customer_clean`/`orders_clean` is the correct
  place Auto CDC is demonstrated, against data that actually changes
  incrementally — forcing the same pattern here would be cargo-culting it onto
  data it doesn't fit.
- `leads`, `web_events`, `ops_events` are materialized tables (`@dlt.table`,
  reading Bronze in batch via `spark.read.table`), with **data quality rules**
  on their key fields: not-null/known `campaign_id`, valid funnel stage
  values, non-negative amounts/latency, and a dedup rule on each table's
  natural key (`lead_id`/`event_id`/`ops_event_id`), keyed on Bronze's
  `_row_id` batch-order identity rather than the tied `_ingest_ts`. Rows that
  fail any rule are **quarantined, not dropped**: `<source>_quarantine` holds
  the rejected row with its reason code(s) and a `_quarantined_ts` — nothing
  vanishes without a record. `<source>_clean` holds the rest. **Not streaming
  tables**: Track 1's equivalent tables are genuine DLT streaming reads
  because Track 1's Bronze is append-only. Track 2's Bronze is a full
  recompute each run (see above), so a streaming read over it isn't the right
  tool — these tables read Bronze in batch instead.
- `quality_metrics` aggregates every fact-table row by `(source, reason)`
  across a run (`reason = "accepted"` for rows that passed). Independently,
  `gate_status` counts each flagged row once (not each reason) to produce a
  per-source `quarantine_rate` and `gate_passed` boolean:
  `false` when the rate exceeds `0.10` (five times the generator's ~2%
  baseline invalid rate). See `docs/sentinel/chapters/02-quality-gate.md` for
  the reasoning.
- `gate_status` also independently re-derives `accepted_rows` and
  `quarantined_rows` from the *persisted* `<source>_clean`/`<source>_quarantine`
  tables (not the `_flagged` view the rate is computed from) and publishes
  `conserved = (accepted_rows + quarantined_rows == total)`. A rate computed
  entirely from the `_flagged` view can look healthy even when nothing was
  actually written to the persisted tables — this happened live (see the
  chapter doc's incident writeup) — so the rate threshold alone is not the
  gate. `quality.evaluate_gate` withholds publication unless `gate_passed`
  **and** `conserved` are both strictly true and `total` is a positive
  number; missing or null `conserved`/`total` fail closed like every other
  gate field.

---

## Gold — `workspace.bedoux_gold`

What it is: business-ready tables, one per business question.

Rules:
- Reads from `workspace.bedoux_silver` only. Never a mix of layers.
- One table per business question. Each table's grain is fixed and documented in
  its comment.

Required Gold tables:

| Table | Grain | Question it answers |
|---|---|---|
| `gold_campaign_performance` | one row per campaign | Spend, leads generated, conversion rate, cost-per-lead per campaign |
| `gold_client_funnel` | one row per client per month | Funnel stage counts (new/qualified/won/lost) per client per month |
| `gold_ogi_ops_health` | one row per day | Daily-plan run success rate, Telegram messages handled, average response latency |

Business logic:
- Conversion rate: `count(leads where stage = 'won') / count(leads)` per campaign.
- Cost-per-lead: `campaign.budget / count(leads)` per campaign; `NULL` (not zero) if
  the campaign generated no leads, since a $0 cost-per-lead would misleadingly imply
  free acquisition rather than "no data."
- Ops success rate: `count(ops_events where success = true) / count(ops_events)`
  per day.

Publication gate: Gold tables contain **no gate logic**. The decision is made
before the Gold pipeline runs at all, by `bedoux_gate_task` between the Silver
and Gold tasks (see "Pipelines and the job" below). Gold's dataset functions
simply compute and return their result. Within the supported job path, the gate
has passed before they run; a direct pipeline run bypasses that check.

The gate is **fail-closed and whole-Gold**. It publishes only when every
required source (`leads`, `web_events`, `ops_events`) has exactly one
`gate_status` row, with `gate_passed` strictly true, `conserved` strictly
true, `total` a positive number, computed at or after the current job run's
start time. Missing rows, duplicate rows, null `gate_passed`/`conserved`,
an empty (`total <= 0`) batch, and evidence carried over from an earlier run
all withhold publication. A quarantine-rate threshold alone is not the gate:
`conserved` independently checks the persisted `<source>_clean`/
`<source>_quarantine` tables against `total`, because a rate computed only
from the `_flagged` view can report a clean pass while nothing was actually
written to those persisted tables. `campaigns` has no `gate_status` row — it
is a dimension governed
by `expect_or_drop` with no quarantine table — so it is not a gate input.

The notebook requires `{{job.start_time.timestamp_ms}}`, converts Spark
timestamps to epoch milliseconds before collection, and compares explicit UTC
datetimes. Missing run context is a failure, including manual notebook execution.
This is a freshness boundary, **not exact run/batch binding**. The supported
demonstration uses `max_concurrent_runs: 1`, full job runs, and no other writers
or deployments between Silver, gate, and Gold. Concurrent/direct pipeline runs,
other jobs, and repair-only execution are outside that guarantee. Immutable
run IDs and version-pinned reads would be needed to remove those assumptions.

When the gate fails, `bedoux_gate_task` fails, `bedoux_gold_task` never starts,
and every Gold table keeps its last published content. On a first-ever run the
Gold tables are simply never created, so rejected data is never published —
there is no "publish anyway because there is nothing to fall back to" path.

The tradeoff is deliberate: because Gold is one pipeline and therefore one
task, a failure in any single source withholds **all** Gold tables, including
ones that do not depend on the failing source. Per-table withholding would
need a different publication design, for example separately orchestrated Gold
outputs. The former in-dataset implementation was unsupported; it is not the
only conceivable per-table design. Withholding more than strictly necessary is the safer error for a
publication gate. See `docs/sentinel/chapters/02-quality-gate.md`.

---

## Pipelines and the job

- One pipeline per layer: `bedoux_bronze_pipeline`, `bedoux_silver_pipeline`,
  `bedoux_gold_pipeline`. Serverless compute.
- One job, `bedoux_analytics_job`, runs the three pipelines in order: Bronze,
  then Silver, then **`bedoux_gate_task`**, then Gold. The gate task is a
  notebook task (`src/bedoux/gate_check.py`), not a pipeline: it reads
  `gate_status` and raises if the batch is not publishable, which stops the run
  before Gold refreshes. It receives the run's start time so it can reject
  gate evidence left over from an earlier run. No automatic schedule —
  triggered manually or via the `workflow_dispatch` GitHub Action, to stay well
  inside Free Edition's compute quota.
- A gate failure makes the job run fail. That is the intended signal, not a
  defect: Gold keeps its last published data and the reason is in the task log
  and the `<source>_quarantine` tables.
- Running `bedoux_gold_pipeline` directly, outside the job, bypasses the gate.
  The gate is an orchestration control, not a constraint inside Gold itself.
