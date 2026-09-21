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
- **Publication gate.** `gate_status` turns per-source row counts into a
  `quarantine_rate` and a `gate_passed` boolean, stamped with `_computed_ts`.
  The decision is enforced *before* Gold runs, by `bedoux_gate_task` between
  the Silver and Gold tasks. `gold.py` contains no gate logic at all.

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

## Review fixes (post-implementation, before push)

A review of the first implementation (commits `89c334c`/`95fceaa`) found one
correctness bug and three spec divergences between `quality.py` and
`silver.py`. All four are fixed in commit(s) on this branch after the review;
recorded here rather than silently folded into history, since the bug was
real and would have shipped a wrong gate decision.

1. **Gate double-counting (the real bug).** `gate_status` computed `total`
   and `quarantined` by summing `quality_metrics`' *exploded* per-reason
   `row_count` — so a row with two reasons (e.g. a duplicate that's also
   missing its `campaign_id`) counted twice in both numerator and
   denominator. Worked example: 100 leads, 10 of them duplicates that are
   also null-`campaign_id`, computed as `20/110 = 18.2%` instead of the true
   `10/100 = 10%` — wrongly crossing the threshold and withholding a refresh
   that should have published. Fixed by adding `_row_counts` (one row in,
   one row counted, straight from the `_flagged` views) and rewriting
   `gate_status` to use it instead of `quality_metrics`. `quality_metrics`
   itself is unchanged — its exploded per-reason breakdown is still useful
   for diagnosis, it's just no longer the gate's input. Regression test:
   `test_gate_rate_counts_rows_not_reasons_for_multi_reason_batch`
   (`tests/test_quality.py`), which reproduces the exact worked example and
   asserts the rate is `10%`, not `18.2%`.
2. **Duplicate reason codes diverged from the spec.** `quality.reconcile`
   previously gave a duplicate row only `duplicate_<key>`, discarding any
   classification reasons; `silver.py`'s Spark expressions evaluate
   classification and dedup independently and can emit both. Resolved in
   favor of `silver.py`'s richer behavior (a row's reasons are the union of
   every rule it fails) because the double-counting bug above only exists
   *because* a row can carry two reasons — collapsing to one would have hidden
   the bug's premise, not just its arithmetic. `quality.reconcile` rewritten
   to classify and dedup in one pass per row; `dedup_by_key` kept as a
   standalone utility, no longer used internally by `reconcile`. Pinned by
   `test_duplicate_row_that_also_fails_classification_gets_both_reasons`.
3. **`web_events` null duration accepted instead of quarantined.** The Spark
   expression was `col("session_duration_seconds") < 0`, which is `NULL`
   (not `True`) for a `NULL` input, so a null-duration row silently passed.
   Fixed to `.isNull() | (col(...) < 0)`, matching the pattern
   `ops_events_flagged` already used correctly. Pinned by
   `test_classify_web_event_quarantines_null_duration` (pins `quality.py`'s
   already-correct behavior that `silver.py` now matches).
4. **`leads` null stage accepted instead of quarantined — a regression.**
   `~col("stage").isin(*VALID_STAGES)` is `NULL` for a `NULL` stage, so the
   row passed through accepted, where the pre-chapter-02 `expect_or_drop`
   had dropped it. Fixed to `col("stage").isNull() | (~col("stage").isin(...))`.
   Pinned by `test_classify_lead_quarantines_null_stage`.

**Closing the testing gap that let these through:** the original test suite
only exercised `quality.py`, so a `quality.py`/`silver.py` divergence stayed
green. Added `test_silver_reason_constants_match_quality_spec`, which greps
`silver.py`'s source text for its (newly extracted) `REASON_*` constants and
`_duplicate_reason(...)` calls and checks them against `quality.py`'s reason
vocabulary — no Spark/`dlt` import needed, since `silver.py` can't be
imported in this environment anyway. Reason-code string literals were also
extracted out of the `lit(...)` call sites into named constants
(`REASON_NULL_CAMPAIGN_ID` etc.) in `silver.py`, with a comment block mapping
each to its `quality.py` counterpart, so a typo shows up once instead of at
every duplicated call site. This narrows, but does not close, the gap: the
Spark *logic* (joins, window functions, `when`/`array_remove` structure)
still has no automated cross-check against `quality.py` and remains
verified by code reading only, same as `gold.py` vs. `transforms.py` always
has been.

## Gate redesign: orchestration, not in-dataset checks

A second review found four defects in the first gate implementation, all in
`gold.py`. They shared one root cause: the decision was being made *inside*
declarative DLT dataset functions, which is the wrong place for it.

1. **`.count()` inside a dataset definition.** `_gate_passed` ran a
   driver-side action while the dataset graph was being resolved. Databricks
   explicitly warns against actions in dataset functions.
2. **Self-referencing read.** `_publish_or_withhold` read
   `workspace.bedoux_gold.<table>` while defining that same table, using
   `spark.read.table` to sidestep DLT's dependency graph. Whether DLT
   tolerates that was never established.
3. **First-run failure published anyway.** With no previous version to fall
   back to, the code returned the fresh — rejected — data. The one case where
   withholding matters most was the case it didn't withhold.
4. **Fail-open on missing or null evidence.** `gate.filter(~col("gate_passed"))`
   finds nothing when a source has no `gate_status` row at all, and `~NULL` is
   `NULL`, so a null `gate_passed` was also filtered out. Absent evidence and
   undecided evidence both read as "passed".

### The replacement

`bedoux_gate_task`, a notebook task between `bedoux_silver_task` and
`bedoux_gold_task`, runs `src/bedoux/gate_check.py`. It collects `gate_status`,
calls `quality.evaluate_gate`, and raises on failure. Gold's dataset functions
went back to plain `return fresh`.

This is ordinary job code, not a dataset definition, so `.collect()` is legal
there — the imperative check moved to the one place an imperative check
belongs. Each original defect closes as a consequence:

| Defect | How the redesign removes it |
| --- | --- |
| `.count()` in a dataset function | No gate code in `gold.py`; the check runs in a job task |
| Self-referencing Gold read | Nothing reads a Gold table; withholding = not running the task |
| First-run failure published | Gold task never starts, so the table is never created |
| Missing/null evidence passed | `evaluate_gate` is fail-closed: absent, duplicated, null, or stale evidence all withhold |

**Run binding.** `gate_status` now carries `_computed_ts`, and the task
receives `{{job.start_time.iso_datetime}}`. Evidence computed before this run
started is rejected as stale, so a leftover row cannot authorize publishing a
different batch. Outside the job there is no run boundary and freshness is not
enforced — deliberate, and why the job always passes `run_start_iso`.

### The tradeoff: whole-Gold, not per-table

The old design gated per table: a `leads` failure withheld
`gold_campaign_performance` and `gold_client_funnel` while
`gold_ogi_ops_health` still refreshed from `ops_events`. Gold is one pipeline
and therefore one task, so failing the gate now withholds **all three**.

Keeping per-table precision would mean either gate logic back inside the
dataset functions — the unsupported thing this redesign removed — or splitting
Gold into several pipelines, which Free Edition's one-active-pipeline-per-type
limit discourages and which is a larger architecture change than this chapter
should make. For a publication gate, withholding more than strictly necessary
is the safer direction to err. Recorded as a known limitation rather than
presented as ideal; splitting Gold stays available if per-source precision
later justifies it.

**Not covered:** running `bedoux_gold_pipeline` directly bypasses the gate
entirely. This is an orchestration control, not an invariant enforced inside
Gold. Chapter 06's permission work is where "who may refresh Gold" belongs.

## Verification and limits

| Check | Status | Evidence |
| --- | --- | --- |
| `quality.py` classify/dedup/reconcile logic | **Verified (policy only)** | `uv run --locked python -m pytest -q` — 53 passed, this session. |
| `quality.evaluate_gate` decision policy: normal input, failing gate, missing source, duplicate rows, null `gate_passed`, stale/null `_computed_ts`, first-run failure, repeat evaluation | **Verified (policy only)** | `tests/test_gate_policy.py`, 20 tests. These prove what the policy *decides*; they do not prove Spark produces the rows, that the job graph stops Gold, or that a withheld table retains its data. |
| `gate_check.py` wiring: notebook header, fail-closed raise, run binding passed through | **Verified (source-grep, no Spark/dlt import)** | `test_gate_check_task_fails_closed_and_binds_the_run`. |
| Job graph: `gold` depends on `gate`, not directly on `silver` | **Verified (YAML parse)** | `resources/bedoux_jobs.yml` parsed and asserted this session. |
| Scenario A/B/C + normal control + replay, at the pure-function level | **Verified** | Same test run, see scenarios above. |
| Gate rate arithmetic counts rows, not exploded reasons | **Verified (regression-tested)** | `test_gate_rate_counts_rows_not_reasons_for_multi_reason_batch`, added after the review found the original bug. |
| `silver.py` reason-code literals match `quality.py`'s vocabulary | **Verified (source-grep, no Spark import)** | `test_silver_reason_constants_match_quality_spec`. |
| `silver.py`/`gold.py` native Spark *logic* (joins, windows, control flow) matching `quality.py`'s semantics | **Verified by code reading, untested against data** | Reviewed side by side; no automated check of the Spark expression structure itself exists (same precedent as `gold.py` vs. `transforms.py` — no test enforces the formulas match either). |
| `bronze.py`'s `_row_id` batch identity | **Verified by code reading, untested against data** | Reviewed; not exercised against a live Bronze run. |
| **A gate failure actually withholds the Gold refresh** | **Untested against a live pipeline** | The whole point of the chapter, and the thing no local test reaches. Requires a run where `bedoux_gate_task` fails and Gold is observed to keep its previous content. |
| `notebook_task` with `base_parameters` runs on Free Edition serverless | **Untested** | The gate task type has never executed here. If Free Edition rejects it, the task type changes — the policy in `quality.py` would not. |
| `{{job.start_time.iso_datetime}}` resolves and parses as ISO 8601 | **Untested** | Dynamic value reference assumed from documentation, not observed. A malformed value makes `datetime.fromisoformat` raise, which fails closed. |
| `_computed_ts` from Spark compares correctly against the parsed run start | **Untested** | Timezone handling in particular: a naive/aware mismatch would raise, which fails closed, but this has not been observed. |
| Whether Gold tables genuinely retain prior content when their pipeline does not run | **Untested** | Expected DLT behavior; unverified here. |
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
