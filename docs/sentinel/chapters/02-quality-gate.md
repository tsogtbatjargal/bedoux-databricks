# Part 02 — Defend before damage spreads

Status: implemented on `series/02-quality-gate`, local only, not pushed or
merged. No post draft yet. Chapter 01 mapped the platform and found the gap
this chapter closes: `expect_or_drop` silently drops rows with no record of
what was dropped or why, no dedup exists on the fact tables, and an orphaned
`campaign_id` vanishes from Gold with no error. This chapter changes pipeline
code (`src/bedoux/bronze.py`, `silver.py`, `gold.py`) for the first time in
the series — see [branch workflow](../branch-workflow.md) and `AGENTS.md`:
merging this to `main` deploys, and is a decision for the user, not this
session.

## Scope

- **Batch identity.** Bronze stamps every `leads_raw`/`web_events_raw`/
  `ops_events_raw` row with `_row_id`: its position in that run's generated
  Python list, assigned before the Spark DataFrame is created
  (`bronze.py:_with_row_id`). `_ingest_ts` (`current_timestamp()`) is constant
  across every row of one table computation, so it ties and can't order
  duplicates deterministically — `_row_id` is what dedup keys off of instead.
- **Persistent quarantine with reasons.** Each fact table's Silver stage now
  reads a `_flagged` view (`leads_flagged`, `web_events_flagged`,
  `ops_events_flagged`) that computes a `_reasons` array per row, then splits
  into two tables: `<source>_clean` (empty reasons) and `<source>_quarantine`
  (non-empty reasons, with the reason codes and a `_quarantined_ts`). Nothing
  is dropped without a record.
- **Quality metrics.** `quality_metrics` aggregates every flagged row (from
  all three sources) by `(source, reason)` — `reason = "accepted"` for the
  rows that passed. Pure `groupBy`/`count`, no driver-side counting.
- **Publication gate.** `gate_status` turns `quality_metrics` into a
  per-source `quarantine_rate` and `gate_passed` boolean. `gold.py` checks it
  before publishing: if a table's source(s) failed the gate this run, the
  table returns its own previously published content unchanged instead of
  the freshly computed (degraded) one.

## The business decision: reject records, withhold refreshes only past a threshold

Two options were on the table: reject individual bad records, or withhold an
entire Gold refresh whenever *any* row fails. Neither alone fit:

- Reject-only means a systemic failure (e.g. a broken upstream campaign
  mapping that nulls out every `campaign_id`) still silently ships a
  near-empty Gold table to Genie/BI — technically no row was wrong, but the
  aggregate is meaningless.
- Withhold-only means the generator's own deliberate ~2% invalid rate
  (`generator.py:INVALID_RATE`) would block every single run, including
  healthy ones — the normal case would never publish.

**Decision: reject individual records by default; withhold the affected
Gold refresh only when a run's quarantine rate for a source exceeds
`QUARANTINE_RATE_THRESHOLD = 0.10`** (`quality.py`). Ten percent is five
times the generator's ~2% baseline invalid rate — past that point, the
deviation reads as a systemic pipeline problem (a broken mapping, a bad
deploy, a corrupted batch) rather than expected background noise, and
Genie/BI users are better served by stale-but-correct numbers than a
silently degraded refresh. The threshold is per-source and per-table:
`gold_campaign_performance`/`gold_client_funnel` gate on `leads`;
`gold_ogi_ops_health` gates on `ops_events`. No Gold table currently reads
`web_events_clean`, so `web_events`'s gate exists (for symmetry and future
use) but nothing depends on it yet.

This is not whole-platform transactional publication — each Gold table
gates independently on the sources it actually reads, not on every source at
once, and the "previous content" fallback is a self-referencing read
(`spark.read.table` of the table's own current state), not a database
transaction. Do not describe this as ACID publication.

## Scenario coverage

Reusing chapter 01's three scenarios and normal control
(`chapters/01-know-your-platform.md`). All four are exercised as pure-Python
unit tests in `tests/test_quality.py`, since no PySpark/DLT runtime is
available in this environment (see Verification below) — the tests operate
on `quality.py`'s classify/dedup/reconcile functions, which `silver.py`'s
native Spark expressions are written to mirror exactly.

- **Scenario A (malformed batch, elevated null `campaign_id`):**
  `test_scenario_a_malformed_leads_are_quarantined_with_reason` — 15% null
  rate, all 15% land in quarantine with reason `null_campaign_id`, and
  `gate_passed` is `False` (15% > 10% threshold), so `gold_campaign_performance`
  and `gold_client_funnel` would withhold their refresh that run.
- **Scenario B (duplicate leads):**
  `test_scenario_b_duplicate_lead_id_quarantined_not_double_counted` — a
  replayed `lead_id` is quarantined with reason `duplicate_lead_id`; the
  accepted set contains the id exactly once, so `count("*")` over
  `leads_clean` can't double-count it.
- **Scenario C (missing campaign reference):**
  `test_scenario_c_unknown_campaign_id_quarantined_not_silently_dropped` and
  `test_classify_lead_distinguishes_null_from_unknown_campaign_id` — a
  non-null `campaign_id` that isn't in `campaigns_raw` is quarantined with
  reason `unknown_campaign_id`, distinct from `null_campaign_id`. It no
  longer vanishes from Gold with no record.
- **Normal control:** `test_normal_control_passes_the_gate` — a ~1% null
  rate (below the generator's own ~2% baseline) quarantines only those rows
  and `gate_passed` is `True`.
- **Reconciliation (no double-counting):** `test_reconcile_conserves_every_row`
  asserts `len(accepted) + len(quarantined) == len(input)` for every case —
  the property the acceptance criteria calls "account for accepted,
  quarantined, and duplicate records without double-counting."
- **Replay:** `test_replay_is_idempotent` calls `reconcile()` twice on an
  identical input and asserts identical output. This generalizes to the live
  pipeline because Bronze/Silver/Gold are all `@dlt.table` full recomputes,
  not streaming appends (see `docs/contracts-bedoux.md`) — reprocessing the
  same seeded batch recomputes to the same result rather than accumulating
  duplicates. That architectural property, not a live rerun, is what this
  test stands in for; it has not been demonstrated against an actual second
  pipeline run.

## Verification and limits

| Check | Status | Evidence |
| --- | --- | --- |
| `quality.py` classify/dedup/reconcile/gate logic | **Verified** | `uv run --locked python -m pytest -q` — 28 passed (17 prior + 11 new), this session. |
| Scenario A/B/C + normal control + replay, at the pure-function level | **Verified** | Same test run, see scenarios above. |
| `silver.py`/`gold.py` native Spark expressions matching `quality.py`'s logic | **Verified by code reading, untested against data** | Reviewed side by side; no automated sync check exists (same precedent as `gold.py` vs. `transforms.py` — no test enforces they match either). |
| `bronze.py`'s `_row_id` batch identity | **Verified by code reading, untested against data** | Reviewed; not exercised against a live Bronze run. |
| Publication gate (`gate_status`, `_publish_or_withhold`, self-referencing read) | **Untested against a live pipeline** | Implemented and reasoned through in code and above; no `DATABRICKS_HOST`/`DATABRICKS_TOKEN`, no `~/.databrickscfg`, no `databricks` CLI in this environment — same limitation chapter 01 recorded, still true. |
| `databricks bundle validate --target dev` | **Unavailable** | Same reason. |
| A live rerun demonstrating "replay does not duplicate" | **Untested** | Would require a live pipeline run; not attempted. Argued architecturally above instead. |

## Related finding, not fixed this chapter

`clients_clean`/`campaigns_clean` dedup by a window ordered on `_ingest_ts`
(`silver.py`, unchanged this chapter). Since `_ingest_ts` is
`current_timestamp()`, it's constant across every row of a single table
computation and ties whenever the same `client_id`/`campaign_id` appears more
than once in one run — `row_number()` over a tied window is not guaranteed
deterministic. This is the same class of bug `_row_id` was added to fix for
leads/web_events/ops_events, but touching `clients_clean`/`campaigns_clean`
was out of this chapter's stated scope (only "malformed values, duplicate
leads, and missing campaign references" were named) and neither table has
test coverage today to catch a regression. Left as a flagged, not fixed,
finding for a future chapter or a dedicated fix.

## Roadmap acceptance mapping

- "Account for accepted, quarantined, and duplicate records without
  double-counting" — `reconcile()`'s conservation assertion,
  `test_reconcile_conserves_every_row`.
- "A failed gate preserves the previously published data" —
  `_publish_or_withhold` in `gold.py`; untested against a live workspace.
- "Normal input passes" — `test_normal_control_passes_the_gate`.
- "Test repeated processing" — `test_replay_is_idempotent`, with the
  architectural argument above for why it generalizes to the live pipeline.
- "Do not claim whole-platform transactional publication unless actually
  implemented" — explicitly not claimed; see the business-decision section
  above.
