# ADR 0001: Medallion layers, with tables owned by domain

Status: accepted (Track 3), 2026-10-16

## Context
A regulator that also runs commercial lines (gaming, liquor, cannabis) has three
business domains with different owners, rules and sensitivity. One flat model
mixes their concerns. Fully separate platforms duplicate the plumbing.

## Decision
One medallion (`aglc_bronze` → `aglc_silver` → `aglc_gold`), with every table
prefixed by its domain (`gaming_`, `retail_` + a `domain` column for liquor and
cannabis). Each domain owns its contract section, expectations and Gold tables.
Cross-domain access is governed by Unity Catalog, not by copying data.

## Consequences
- Shared tooling (bundle, CI, quality gates) and one governance model.
- Domain boundaries are visible in names and enforceable with grants and row filters.
- Not a full data mesh: no separate catalogs or domain-run pipelines. At a larger
  scale, the next step would be a catalog per domain.
