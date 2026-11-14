# ADR 0006: Cost defaults, triggered serverless and no schedule

Status: accepted (Track 3), 2026-10-16

## Context
The fastest way to waste platform money is always-on compute and refresh rates
nobody asked for. Lessons from a production Snowflake platform (author's prior
role): tuning idle compute and auto-suspend cut idle spend about 56%, and setting
refresh lag by business priority saved about 30% of credits on lower-priority tables.

## Decision
Serverless DLT, `continuous: false`, no job schedule (manual or orchestrated
trigger). Materialized recompute is fine at synthetic scale. Refresh frequency
would be set per table by how fresh each consumer actually needs it, not globally.

## Consequences
- Near-zero idle cost. Free Edition quota respected.
- At real scale, Bronze would move to incremental ingestion (Auto Loader / Auto
  CDC, as in Track 1) and Gold refresh would be scheduled per domain SLA.
- The numbers above are from a different platform and role, cited as experience,
  not measured here.
