# ADR 0007: One pure-Python engine, thin platform tasks

Status: accepted (Track 4), 2026-11-13

## Context
Track 4 has to run locally (tests, CI, the eval, the demo) and on Databricks:
the existing Free Edition workspace and an Azure Databricks workspace. Writing
ingestion logic inside notebooks would make the rules untestable without a
cluster and would fork the logic per platform.

## Decision
Ingestion, contracts, reconciliation, the monitor and the agents live in
`src/adp/` as pure Python with no import-time dependency on `spark` or
`dbutils`. The Databricks notebooks (`ingest_task.py`, `reconcile_task.py`)
only read state, call the engine and write Delta tables. Dataset behaviour is
metadata (`config/adp/datasets/*.yml`), validated on load.

## Consequences
- Every rule (cursor ties, lookback, failed runs, quarantine ratio) is a unit
  test that runs in about a second.
- The same bundle deploys to both workspaces; only the target differs.
- At this scale Bronze is overwritten from the engine's merged state. A large
  source would need Delta `MERGE` in the task; recorded as a known gap.
