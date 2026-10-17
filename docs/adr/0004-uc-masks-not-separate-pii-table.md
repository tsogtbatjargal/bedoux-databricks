# ADR 0004: Protect PII with Unity Catalog masks, not a separate copy

Status: accepted (Track 3), 2026-10-16. Free Edition support unverified.

## Context
Player email and date of birth are PII. The common alternatives are a separate
restricted table, hashed copies, or masking views. Copies drift, and views can be
bypassed by anyone who can read the base table.

## Decision
Keep PII in one place (`gaming_players_clean`) and attach Unity Catalog column
masks in the DLT table definition: clear values for `aglc_compliance`, partial
(`***@domain`, birth year) for everyone else. Gold never carries PII. Retail Gold
uses a row filter so domain analysts see only their domain. Functions are created
before the pipelines, because a pipeline-managed table can't be ALTERed to add a
mask later.

## Consequences
- Policy lives with the data: every query path gets the same mask.
- One source of truth for PII, so deletion and retention are simple.
- Free Edition: support for account groups, masks and filters is unverified.
  `aglc_enforce_governance` and `aglc_apply_grants` let the pipelines run
  without them. Verify before claiming any of this works live.
- Audit (`system.access.audit`) is likely unavailable on Free Edition. In
  production, audit queries over that table would close the loop.
