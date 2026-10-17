# ADR 0003: Reconcile against the legacy report before cutover

Status: accepted (Track 3), 2026-10-16

## Context
Moving reporting off a legacy stack (e.g. SSIS loads + SSRS reports) fails when
business users find a number that doesn't match the report they trusted. Translating
code is the easy part. Proving equivalence is what earns trust.

## Decision
Run old and new in parallel. A reconciliation task compares
`gold_retail_sales_daily` with `legacy_retail_sales_daily` on the business key:
missing keys either side, exact counts, revenue within 0.01. A failed
reconciliation fails the job ("cutover not allowed"), and every run is logged to
`aglc_legacy.reconcile_runs`. The legacy side is computed independently, and a demo
setting injects a known discrepancy to prove the gate catches it.

## Consequences
- Cutover becomes a measurable, auditable decision, not a judgement call.
- Differences get investigated as data (which keys, which columns), not anecdotes.
- Here, the "legacy" system is simulated. Tooling like Databricks Lakebridge
  (Analyzer, Transpiler, Reconcile) does this at real scale; this is the same idea, built small.
