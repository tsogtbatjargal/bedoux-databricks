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
