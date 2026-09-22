# Layer Contracts

The engineering rules for this Medallion pipeline. The AI reads this file before writing or changing any pipeline code. You enforce it when you verify the output.

Source data: `samples.tpch` — 8 tables: `customer`, `orders`, `lineitem`, `part`, `supplier`, `partsupp`, `nation`, `region`.
Catalog: `workspace`. One schema per layer: `bronze`, `silver`, `gold`. Every schema has a description.

---

## Naming (locked)

| Layer  | Schema             | Table name pattern  | Example                          |
|--------|--------------------|---------------------|----------------------------------|
| Bronze | `workspace.bronze` | `<source>_raw`      | `orders_raw`                     |
| Silver | `workspace.silver` | `<source>_clean`    | `orders_clean`                   |
| Gold   | `workspace.gold`   | `gold_<question>`   | `gold_customer_lifetime_value`   |

A Bronze table never lives in `silver` or `gold`. A Silver table never lives in `bronze` or `gold`. A Gold table never lives in `bronze` or `silver`.

---

## Bronze — `workspace.bronze`

What it is: a raw, append-only landing zone. A faithful copy of the source, plus a couple of audit columns. No interpretation.

Rules:
- One Bronze table per source table. 8 tables total.
- Keep every source column exactly as it is. No renames, no casts, no filters, no joins, no aggregations.
- Add exactly two audit columns:
  - `_ingest_ts` — `current_timestamp()` at load time
  - `_source_table` — the fully qualified source name, e.g. `samples.tpch.orders`
- Append-only. Bronze tables are streaming tables; rows are added, never updated or rewritten.

---

## Silver — `workspace.silver`

What it is: a clean, conformed copy of Bronze. Still detail grain — no business logic, no KPIs.

Rules:
- One Silver table per Bronze table, named `<source>_clean`.
- Reads from `workspace.bronze` only. Never from `samples.tpch`.
- Clean up: trim strings, cast columns to sensible types, drop rows that fail basic validity.
- Tables that change over time — `customer` and `orders` — are loaded incrementally with **Auto CDC** (SCD type 1, keyed on the primary key, sequenced by `_ingest_ts`). Do not rebuild them from scratch each run, and do not dedup them with a window function — Auto CDC handles that.
- Detail and reference tables — `lineitem`, `part`, `supplier`, `partsupp`, `nation`, `region` — are streaming tables with **data quality expectations** on their key fields: not-null keys, valid ranges (e.g. `l_quantity > 0`, `l_discount` between 0 and 1), non-negative amounts. Rows that fail are dropped.

---

## Gold — `workspace.gold`

What it is: business-ready tables, one per business question, shaped for analytics and BI.

Rules:
- Reads from `workspace.silver` only. Never from `workspace.bronze`, never from `samples.tpch`. Never a mix of layers.
- One table per business question. Each table's grain is fixed and documented in its comment.
- Revenue is defined consistently everywhere as `sum(l_extendedprice * (1 - l_discount))`.

Required Gold tables:

| Table                              | Grain                          | Question it answers                                              |
|------------------------------------|--------------------------------|------------------------------------------------------------------|
| `gold_monthly_revenue_by_region`   | one row per region per month   | How much revenue did each region make each month?                |
| `gold_customer_lifetime_value`     | one row per customer           | Per customer: total orders, total revenue, average order value, first and last order date, and a value segment |
| `gold_top_products`                | one row per product            | Per product: total revenue, total quantity, order count, and a revenue rank |

If `gold.py` is missing any of these three tables, Gold is not done.

---

## Pipelines and the job

- One pipeline per layer. Each pipeline runs that layer's file (`bronze.py`, `silver.py`, `gold.py`) and targets that layer's schema in the `workspace` catalog. Serverless compute.
- One job that runs the three pipelines in order: Bronze, then Silver, then Gold. Bronze must finish before Silver starts; Silver before Gold. The job can be scheduled (e.g. daily).

---

## Track 1 stays

Removing Track 1 was considered and rejected. It stays because it's the
project's only demonstration of **Auto CDC against genuinely incremental
data** (`customer`/`orders`, above) — `docs/contracts-bedoux.md` explicitly
cites this file as "the correct place Auto CDC is demonstrated" when
justifying why Track 2's `clients`/`campaigns` dimensions deliberately use
plain materialized tables instead of CDC. That justification only holds up
with a real CDC example present to compare against; without Track 1, Track
2's choice to skip CDC would read as an omission rather than a decision.

**Candidate for extraction into its own repo later**, not now. If that
happens, extraction means moving: `src/bronze.py`, `src/silver.py`,
`src/gold.py`, `src/transforms.py`, `resources/jobs.yml`,
`resources/pipelines.yml`, this file, and Track 1's tests
(`tests/test_transforms.py` and the Track-1-specific parts of any shared
test file).

**The constraint that makes this non-trivial:** `databricks.yml` includes
`resources/*.yml` — both tracks currently share **one bundle**. Deleting
`resources/jobs.yml`/`resources/pipelines.yml` and deploying would not just
remove them from this repo; Databricks Asset Bundles delete resources that
leave the bundle definition, so that deploy would **destroy the live
TPC-H job and pipelines in the workspace** — not archive them, not leave
them alone. Extraction is therefore a workspace decision (bind the
existing resources to a new, separate bundle first, or accept recreating
them from scratch) as much as a code move, and it needs to be planned as
one before any file leaves this repo. A future session should not have to
rediscover this by deploying and watching Track 1 disappear.

**The same one-bundle fact also creates live coupling today**, independent
of any future extraction: every Track 2 bundle deployment can
create/update Track 1 resources, because `bundle deploy` operates on the
whole bundle, not per track. This is already called out where deployment
actually happens — see
[`sentinel/live-verification.md`](sentinel/live-verification.md), section
2 — rather than restated here.
