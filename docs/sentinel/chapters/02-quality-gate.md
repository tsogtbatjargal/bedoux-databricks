# Part 02 — Defend before damage spreads

Status: **Merged and integrated into `main`** (PR #3, merge commit `f8ae89d`;
first-ever CI deployment to the workspace verified: correct resource IDs, no
duplicates, correct job graph and config, Gold untouched by the deploy). A
follow-on external review of the merged code found a real latent gap and
two wording issues, since fixed and merged (PR #4, merge commit `b62bffa`,
verified with a second live run showing zero behavioral deviation) — see
"Review findings, round 2" below. Durable per-stage evidence for the live
demonstration is in
[chapter-02-evidence.md](../chapter-02-evidence.md); deferred structural
gaps are tracked in [known-gaps.md](../known-gaps.md).
**Demonstrated, not just implemented and locally tested**: a live baseline
run found a real defect — the gate initially passed a run that lost 100% of
its fact rows (see "Incident") — which this branch fixed, then proved via a
full live fault → restore → replay sequence: the withhold path correctly
stopped Gold on a genuine 32.8% quarantine rate, restoration was explicit
and verified, and a literal back-to-back replay showed no duplication. See
"Fault → restore → replay demonstration" below. No post draft yet.
Chapter 01 mapped the platform and found the gap
this chapter closes: `expect_or_drop` silently drops rows with no record of
what was dropped or why, no dedup exists on the fact tables, and an orphaned
`campaign_id` vanishes from Gold with no error. This chapter changes pipeline
code (`src/bedoux/bronze.py`, `silver.py`, `gold.py`) for the first time in
the series — see [branch workflow](../branch-workflow.md) and `AGENTS.md`:
merging this to `main` attempts validation and deploys only if checks succeed.
Integration remains a deployment decision for the user.

## Scope

- **Row-order identity (not batch identity).** Bronze stamps every
  `leads_raw`/`web_events_raw`/`ops_events_raw` row with `_row_id`: its
  position in that run's generated Python list, assigned before the Spark
  DataFrame is created (`bronze.py:_with_row_id`). `_ingest_ts`
  (`current_timestamp()`) is constant across every row of one table
  computation, so it ties and can't order duplicates deterministically —
  `_row_id` is what dedup keys off of instead. `_row_id` restarts at 0 every
  run and is not globally unique across runs — it resolves duplicates
  *within* one run's recompute, nothing more. **Real batch/run identity is
  not implemented anywhere in this pipeline**; see "Verification and limits"
  below.
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
silently degraded refresh. Thresholds are per source, but publication is
whole-Gold: all three required sources must pass, including `web_events`,
which no current Gold table reads. The job skips the entire Gold pipeline
on failure. This conservative coupling is deliberate for this chapter.

This is not transactional publication: once Gold starts, a runtime failure
could still leave its outputs at different refresh states. There is no
self-referencing read or atomic multi-table swap.

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

**Freshness, not exact run binding.** `gate_status` carries `_computed_ts`.
The task requires `{{job.start_time.timestamp_ms}}` and converts Spark timestamps
to epoch milliseconds before collection, then explicit UTC datetimes. Missing
or malformed run context now fails closed rather than disabling freshness.
Evidence older than the job start is rejected. This does not distinguish a
different writer's newer evidence: use a serialized full job with no concurrent
writers, deployments, or repair-only runs. Exact batch identity/version-pinned
reads are not implemented.

**Repeatable fault injection.** Bundle variable `bedoux_lead_invalid_rate`
sets Bronze's `bedoux.lead_invalid_rate`. The default is `0.02`; `0.30`
produces an above-threshold lead fixture with the fixed seed. Nonfinite and
out-of-range values fail. Leads have an explicit schema so the `1.0` case
does not rely on inferring a type from an entirely null `campaign_id` column.

### The tradeoff: whole-Gold, not per-table

The old design gated per table: a `leads` failure withheld
`gold_campaign_performance` and `gold_client_funnel` while
`gold_ogi_ops_health` still refreshed from `ops_events`. Gold is one pipeline
and therefore one task, so failing the gate now withholds **all three**.

Per-table precision needs a different design, such as separately orchestrated
Gold outputs, outside this chapter's small scope. The previous imperative
in-dataset gate is not an option to restore. For this publication gate, withholding more than strictly necessary
is the safer direction to err. Recorded as a known limitation rather than
presented as ideal; splitting Gold stays available if per-source precision
later justifies it.

**Not covered:** running `bedoux_gold_pipeline` directly bypasses the gate
entirely. This is an orchestration control, not an invariant enforced inside
Gold. Chapter 06's permission work is where "who may refresh Gold" belongs.

## Incident: the gate passed a 100% row-loss run

The first live healthy-baseline run (`bedoux_lead_invalid_rate=0.02`,
2026-09-21) is the most valuable result this chapter has produced so far —
not because it succeeded, but because of exactly how it failed. **Do not
read what follows as a success story with a bug found along the way; a gate
that cannot detect total row loss is not a gate**, and that is what this
chapter shipped to `dev` on the first attempt.

**What happened.** All four job tasks (bronze, silver, gate, gold) reported
`SUCCESS`. But `leads_clean`, `leads_quarantine`, and the same pair for
`web_events`/`ops_events`, plus `quality_metrics`, were all **0 rows** —
every one of 2,865 Bronze fact rows vanished with no record in either table,
the precise failure this chapter exists to prevent. `gate_status` reported
`total=500/2000/365, quarantined=0, gate_passed=true` for all three sources —
numbers that looked clean and were completely wrong, because they were
computed from the same broken source as the empty tables. The gate did not
just fail to catch a problem; it actively certified a false pass. Gold then
refreshed on that false pass and overwrote the real 2026-07-30 baseline:
`gold_client_funnel` 132 → 0 rows, `gold_ogi_ops_health` 183 → 0 rows,
`gold_campaign_performance` kept 30 rows but every one now had `lead_count=0`
and `cost_per_lead=NULL`.

**Root cause.** `silver.py` built each `*_flagged` view's `_reasons` column
as `array_remove(array(when(...), when(...), ...), None)`. Each `when(...)`
with no `.otherwise()` evaluates to Spark `NULL` when its condition is
false — normal and expected, meant to be stripped by `array_remove`. But
Spark's `array_remove(array, element)` is **null-intolerant**: when the
*element* argument is `NULL`, the whole result is `NULL`, not the array with
nulls stripped. So `_reasons` was `NULL` on every single row, in all three
`*_flagged` views, unconditionally. Every downstream consumer of that NULL
inherited a different, self-consistent-looking wrong answer:
`size(_reasons) == 0` (the `_clean` filter) is `NULL`, matched nothing;
`size(_reasons) > 0` (the `_quarantine` filter) is also `NULL`, matched
nothing either; `explode(_reasons)` on a NULL array emits nothing, so
`quality_metrics` came out empty too; and `_row_counts`' original
`(size(_reasons) > 0).cast("int")` evaluated to `0`, so `gate_status`
computed `quarantined=0` — a rate of `0%`, comfortably under the 10%
threshold. No exception anywhere: NULL propagation is silent by design, and
the pipeline event log shows every flow completing with no WARN/ERROR event.
This was diagnosed by reading the two array functions' actual Spark
semantics side by side, not by re-running against live data — confirmed
first against the source (`array_remove(..., None)` at three call sites),
then reproduced live.

**Why local tests did not catch it.** All 92 tests passing before this
incident is not a suite that got weaker; it is a suite that was never asked
this question. Every test in `tests/test_quality.py` and
`tests/test_gate_policy.py` exercises `quality.py` (pure Python) or
`quality.evaluate_gate` with hand-built row dicts — **`silver.py`'s actual
Spark expressions have never been executed in this environment**, because
there is no `pyspark`/`dlt` runtime available locally (see
`docs/development.md`). `array_remove(..., None)`'s null-intolerance is a
Spark runtime behavior; no amount of testing `quality.py` in pure Python
could exercise it, because `quality.py` has no equivalent bug — its
`reconcile()` builds a plain Python list and appends to it, which has no
null-propagation semantics to get wrong. The source-grep tests added after
the first review (`test_silver_reason_constants_match_quality_spec`) checked
that reason-code *literals* matched between the two files; they did not, and
structurally could not, check that the Spark *functions combining* those
literals behaved as intended. This incident is the same category of gap
that review flagged as unclosed, now landing for real. `Milestone 3`'s new
`test_silver_does_not_use_null_intolerant_array_remove` closes this specific
instance the same way — source-text/AST inspection, no Spark import — and
is subject to the identical limitation: it proves this exact function isn't
called again, not that no other Spark expression in this file has an
analogous NULL-propagation defect.

**The fix, in two parts, because one alone was not enough.**

1. **Milestone 1 (stop losing the rows).** Replaced `array_remove(array(...),
   None)` with `array_compact(array(...))` at all three `*_flagged` views —
   `array_compact` actually strips NULL elements rather than propagating a
   NULL element into a NULL result. Added
   `@dlt.expect_or_fail("reasons_not_null", "_reasons IS NOT NULL")` to each
   view so a future regression of this exact kind fails the pipeline update
   loudly instead of silently emptying three pairs of downstream tables.
2. **Milestone 2 (make the gate able to detect this class of bug, not just
   this instance of it) — the more important fix.** Milestone 1 alone would
   have fixed this specific bug but left the gate exactly as blind as
   before: `gate_status`'s only signal was a rate computed within the
   `*_flagged` view, and any future defect that corrupted that same view
   (this one, or a different one) would again compute a self-consistent,
   wrong, passing rate. `gate_status` now also reads the **persisted**
   `<source>_clean`/`<source>_quarantine` tables directly — the tables Gold
   and the quarantine record actually depend on — and adds
   `conserved = (accepted_rows + quarantined_rows == total)`. `total` still
   comes from the `_flagged` view; `accepted_rows`/`quarantined_rows` come
   from a completely independent read of what was actually written.
   `quality.evaluate_gate` now withholds unless `gate_passed` **and**
   `conserved` are both strictly true and `total` is a positive number
   (an empty batch is not a healthy pass, even though `0 + 0 == 0` is
   trivially "conserved"). Missing or null `conserved`/`total` fail closed
   like every other gate field. This is what would have actually caught the
   incident: even with `_reasons` NULL, `conserved` would have been `0 + 0
   == 500` → `False` → withhold.

**What this incident does not change:** the whole-Gold, not-transactional,
freshness-not-batch-identity limitations recorded elsewhere in this chapter
are unaffected. Conservation catches "the split doesn't add up to the
input"; it does not catch every possible way a Spark expression could be
subtly wrong while still conserving row counts (for example, a
misclassification that quarantines the right *count* of rows for the wrong
*reason* would still conserve). It closes the most severe failure mode —
total, silent data loss passing as healthy — not every possible one.

**Re-run result (2026-09-21, same day, post-fix):** all four tasks succeeded
again — but this time verified against the actual persisted tables, not just
job status, the same way the incident itself was found. `gate_status`:
`leads` total=500/quarantined=10/`conserved=true`, `web_events`
total=2000/quarantined=46/`conserved=true`, `ops_events`
total=365/quarantined=8/`conserved=true` — quarantine rates 2.0%/2.3%/2.2%,
all comfortably under the 10% threshold and close to the generator's ~2%
baseline. Directly queried `leads_clean`/`leads_quarantine` = 490/10,
`web_events_clean`/`quarantine` = 1954/46, `ops_events_clean`/`quarantine` =
357/8 — **exact matches to `gate_status`'s own numbers this time.**
`quality_metrics` shows a sane per-reason breakdown (`leads`:
`null_campaign_id` × 10; `web_events`: `invalid_duration` × 46; `ops_events`:
`invalid_latency` × 8). Gold refreshed: `gold_campaign_performance` 30 rows
with real non-zero `lead_count`/`won_count`/`conversion_rate` and non-NULL
`cost_per_lead`; `gold_client_funnel` 132 rows; `gold_ogi_ops_health` 183
rows. **All three Gold tables' order-independent content digests matched the
pre-incident 2026-07-30 baseline exactly**, confirming the handoff's
corrected claim: the destroyed baseline was fully recoverable because every
business row is deterministic from `SEED=42` and Gold carries no audit
timestamp column. See the handoff for run/update IDs.

## Fault → restore → replay demonstration

The procedure is specified in [live-verification.md](../live-verification.md).
This section records what was actually observed running it, in one
continuous session, against the confirmed-good `dev` baseline from the
post-fix re-run (`gold_campaign_performance` 30 rows, `gold_client_funnel`
132 rows, `gold_ogi_ops_health` 183 rows — same digests throughout, given
below truncated for readability).

**Stage 1 — Fault (`bedoux_lead_invalid_rate=0.30`).** Deployed, confirmed
the live config read back `"0.30"`, ran the job once (`330174171866992`).
`bedoux_bronze_task`/`bedoux_silver_task` succeeded; `bedoux_gate_task`
failed; `bedoux_gold_task` was skipped (`UPSTREAM_FAILED`). Critically, a
red job by itself proves nothing — `expect_or_fail` firing, a notebook bug,
and a real quarantine-rate failure all look identical from job status alone.
Queried `gate_status` directly: `leads` — total 500, accepted_rows 336,
quarantined_rows 164, rate 32.8%, `gate_passed=false`, **`conserved=true`**.
That last field is the point: a real, conserved, above-threshold rate, not
another silent-loss defect wearing a different number. Exact match to the
predicted 336/164/32.80% (`quality.py`'s reference rules and `silver.py`'s
Spark expressions agree). `web_events`/`ops_events` correctly unaffected
(2.3%/2.19%, both passing and conserved — only leads uses the override).
Queried all three Gold tables afterward: digests unchanged, and `updated_at`
**predated the run's start entirely** — not "unchanged since last checked,"
proof Gold was never touched.

**Stage 2 — Restore (`bedoux_lead_invalid_rate=0.02`).** Did not assume the
setting would revert; explicitly redeployed and confirmed the live config
read back `"0.02"` before running. Run `262274593519322`: all four tasks
succeeded. `gate_status`: leads back to 490/10 (2.0%), conserved and passing,
matching the confirmed-good baseline exactly. Gold's digests matched again —
and this time `updated_at` **advanced**, proving a genuine recomputation
landed on identical content, not that Gold sat untouched by coincidence.

**Stage 3 — Replay (`bedoux_lead_invalid_rate=0.02`, no config change).** Ran
the job again immediately: `98756061776337`. All four tasks succeeded;
`gate_status` identical to Stage 2 in every field except `_computed_ts`,
which advanced (`00:44:20.768Z` → `01:24:03.322Z`) — fresh evidence each
run, not stale evidence reused. Re-queried the persisted Silver tables
directly (not just `gate_status`): identical counts to Stage 2. Gold's
digests matched the baseline again, `updated_at` advanced again. This is the
literal back-to-back replay this chapter previously lacked: two consecutive
runs of the same healthy job, no configuration change between them,
identical business content and multiplicities, fresh audit timestamps each
time — direct evidence against duplication, not an architectural argument.

**What this does not establish**, stated plainly rather than sanded down:
`expect_or_fail` has still never fired (no run has produced a NULL
`_reasons`); `conserved=false` has still never been observed live, only
reproduced in policy tests against the incident's own numbers — so the
conservation check's *passing* behavior is proven live, its *own* failure
path is not. The chapter's other documented limits (whole-Gold not
per-table withholding, freshness not immutable batch identity, no atomic
multi-table publication, the untested first-run-failure case, the unfixed
`clients_clean`/`campaigns_clean` tie bug) are all unchanged by this
demonstration — see "Verification and limits" and "Related finding" below.

## Review findings, round 2 (after merge, PR #4)

An external review of the merged code (PR #3) found five issues. One
(architecture diagram missing the gate node; contract wording saying the
job "runs three pipelines" when it runs four tasks) was already fixed by
`8c10bbf`, confirmed against the file contents before assuming. The other
four:

1. **Campaign-reference gap (real, was latent).** `leads_flagged`/
   `web_events_flagged` validated `campaign_id` against
   `workspace.bedoux_bronze.campaigns_raw` — Bronze, unfiltered — instead of
   `campaigns_clean`, the Silver dimension `campaigns_clean`'s own
   `@dlt.expect_or_drop` rules (`client_id IS NOT NULL`, `budget >= 0`)
   actually publish from. A campaign that fails those rules is dropped from
   `campaigns_clean`, but a lead referencing it was still checked against
   the *unfiltered* Bronze set, found "known," and accepted. That lead then
   conserves (it really was accepted, correctly counted), passes the gate
   (a real, conserved rate), and only then vanishes — permanently and
   silently — from `gold_client_funnel`'s inner join to `campaigns_clean`,
   since the campaign it references was never published there. Every layer
   of chapter 02's own machinery (quarantine, conservation, the gate) worked
   exactly as designed and still let this happen, because the defect was
   one step upstream of all of them: checking existence against the wrong
   table. This directly contradicts "nothing vanishes without a record."
   **Fixed**: both `_flagged` views now call `dlt.read("campaigns_clean")`
   instead of `spark.read.table(".../campaigns_raw")`. Pinned with
   `quality.eligible_campaign_ids` (mirrors `campaigns_clean`'s two
   `expect_or_drop` predicates in pure Python) and two adversarial tests
   (`test_lead_referencing_a_campaign_campaigns_clean_would_reject_is_quarantined`,
   the `web_events` equivalent) that construct a campaign with a negative
   budget and assert a lead referencing it quarantines as
   `unknown_campaign_id` — and, for contrast, that the *un-filtered* Bronze
   set would have wrongly accepted it, so the test pins a real behavioral
   difference, not a vacuous check. The seeded generator never produces a
   droppable campaign (`budget` is always `uniform(200, 5000)`, `client_id`
   is always set) — this fixture, not the fixture data, is what keeps the
   gap closed; the generator's defaults were deliberately left alone.
2. **Batch-identity terminology (wording only).** `_row_id` was called "the
   batch identity" in `bronze.py`'s docstring and "Batch identity" as this
   chapter's own Scope-section heading and a verification-table row. It
   restarts at `0` every run and only orders duplicates *within* one run's
   recompute — it establishes nothing across runs, and real batch/run
   identity is not implemented anywhere in this pipeline (see
   `docs/contracts-bedoux.md`, which already had this right: "not a
   globally unique batch or run ID"). Retitled to "row-order identity"
   everywhere the imprecise term appeared — `bronze.py`, this chapter's
   Scope section and verification table, `roadmap.md`'s chapter 02
   description, and chapter 01's "Expected after chapter 02" note. Left
   alone everywhere the term already correctly stated the absence of batch
   identity (`live-verification.md`, `quality.py`, two other spots in this
   chapter).
3. **Durable evidence.** Recorded in `chapter-02-evidence.md` — see the
   "Status" note above.
4. **Deferred gaps.** Recorded in `known-gaps.md` — see the "Status" note
   above.

**Verification (Milestone 5):** local suite (101 passed, was 98), then one
live run of `bedoux_analytics_job` at the default `bedoux_lead_invalid_rate
= 0.02`. Predicted, before running: leads 490 clean / 10 quarantined
(unchanged from the confirmed baseline), since no seeded campaign is
droppable — the fix should be a behavioral no-op on current data while
closing a real structural gap. Observed: exact match, zero deviation —
`gate_status` leads 490/10/`conserved=true`, persisted Silver counts
490/10/1954/46/357/8, all three Gold digests identical to the reference
values in `chapter-02-evidence.md`. Merged (PR #4, `b62bffa`); the
resulting CI deployment to `main` was verified the same way as PR #3's:
same resource IDs, no duplicates, correct job graph and Bronze config.

## Verification and limits

**A note on what "local" proves, restated after the incident:** every row
below labeled "policy only" or "no Spark runtime" means exactly that —
these tests execute pure Python (`quality.py`) or hand-built dicts, never
`silver.py`'s actual Spark expressions. That gap is what let the
`array_remove(..., None)` defect ship in the first place (see "Incident"
above). The new tests added for this fix close specific instances of that
gap (source-text/AST checks that specific functions/constants are used
correctly); they do not, and cannot, execute `silver.py`'s Spark logic
end to end. Only a live pipeline run does that.

| Check | Status | Evidence |
| --- | --- | --- |
| Local suite: policy, generator, notebook/Bronze wiring | **Verified locally** | `uv run --locked python -m pytest -q` — 98 passed after this fix (was 92); no Spark runtime — see note above. |
| `quality.evaluate_gate`: normal, failed, missing, duplicate, null, stale, missing run context, timezone handling, **row conservation, empty batch** | **Verified (policy only)** | `tests/test_gate_policy.py`; does not prove that Spark produces those rows or that the scheduler stops Gold. |
| `gate_check.py` wiring, exception propagation, new `conserved`/`accepted_rows`/`quarantined_rows` fields | **Verified with API stubs** | `tests/test_gate_notebook.py` executes the actual notebook with synthetic Spark/dbutils substitutes; not serverless execution. |
| Job graph: `gold` depends on `gate`, not directly on `silver` | **Verified (YAML parse)** | `resources/bedoux_jobs.yml` parsed and asserted this session. |
| Scenario A/B/C + normal control + replay, at the pure-function level | **Verified** | Same test run, see scenarios above. |
| Gate rate arithmetic counts rows, not exploded reasons | **Verified (regression-tested)** | `test_gate_rate_counts_rows_not_reasons_for_multi_reason_batch`, added after the first review found that bug. |
| `silver.py` reason-code literals match `quality.py`'s vocabulary | **Verified (source-grep, no Spark import)** | `test_silver_reason_constants_match_quality_spec`. |
| `silver.py` no longer calls null-intolerant `array_remove(..., None)`; uses `array_compact` at all three sites; `expect_or_fail` guards `_reasons` | **Verified (AST-checked, no Spark import)** | `test_silver_does_not_use_null_intolerant_array_remove`, added after the incident. Proves this exact function isn't called again; does not prove no analogous NULL-propagation defect exists elsewhere in the file. |
| Row-conservation check (`accepted_rows + quarantined_rows == total`) is what would have caught the incident | **Verified against the incident's own numbers** | `test_unconserved_source_withholds_even_though_gate_passed_and_rate_look_clean` reproduces `gate_passed=True, rate=0.0, accepted_rows=0, quarantined_rows=0, total=500` and asserts the gate now withholds. |
| `silver.py`/`gold.py` native Spark *logic* (joins, windows, control flow) matching `quality.py`'s semantics | **Verified by code reading, untested against data — this is exactly the category the incident came from** | Reviewed side by side; no automated check of the Spark expression structure itself exists (same precedent as `gold.py` vs. `transforms.py`). The array_remove defect survived this same kind of review once already. |
| `bronze.py`'s `_row_id` row-order identity (dedup ordering within one run — not batch/run identity, which is not implemented) | **Verified by code reading, untested against data** | Reviewed; not exercised against a live Bronze run. |
| A healthy run's gate correctly PASSES with conserved, accurate evidence | **Verified live, post-fix, twice** | Milestone-4 re-run and the replay stage (below) both show `gate_status` conserved=true for all three sources, with directly-queried `_clean`/`_quarantine` counts matching exactly (490/10, 1954/46, 357/8) both times. |
| **A failing gate actually withholds the Gold refresh, leaving prior content intact** | **Verified live** | Fault stage (`bedoux_lead_invalid_rate=0.30`, run `330174171866992`): `leads` quarantine rate 32.8% (predicted 32.80%, exact match), `gate_passed=false`, **`conserved=true`** — a genuine high-but-conserved rate, not a conservation false-positive. `bedoux_gate_task` FAILED, `bedoux_gold_task` SKIPPED (`UPSTREAM_FAILED`). Gold's three digests were unchanged and `updated_at` predated the run entirely — not merely "unchanged since last checked," proof it was never touched. |
| `notebook_task` with `base_parameters` runs on Free Edition serverless | **Verified, five times** | Executed successfully across the baseline, Milestone-4 re-run, fault, restore, and replay runs, including raising an exception correctly on the fault run and exiting cleanly on the others. |
| `{{job.start_time.timestamp_ms}}` resolves in the workspace | **Verified** | `run_start_ms` resolved and `min_computed_ts` computed without error on every run this chapter has made. |
| Spark `unix_millis(_computed_ts)` feeds UTC comparison | **Verified** | `_computed_ts` values were fresh and compared correctly against the run boundary on every run, including advancing correctly between the restore and replay stages (`00:44:20.768Z` → `01:24:03.322Z`), proving stale evidence isn't reused. |
| Whether Gold tables genuinely retain prior content when their pipeline does not run | **Verified live** | Fault stage: all three Gold digests unchanged, `updated_at` predated the run. Restore/replay stages: Gold *did* refresh (new `updated_at` each time) and landed on the identical baseline digests both times — refresh vs. retention is now distinguished by direct evidence, not inferred from job status. |
| `databricks bundle validate --target dev` | **Verified, repeatedly** | `bundle validate`/`bundle plan`/`bundle deploy`/`bundle run` all executed successfully against `dev` across five separate runs this chapter. |
| A live rerun demonstrating "replay does not duplicate" | **Verified, literal back-to-back replay** | Restore run (`262274593519322`) and replay run (`98756061776337`), same `0.02` config, run consecutively with no change between them: identical `gate_status` counts (490/10, 1954/46, 357/8 both times), identical persisted Silver counts, identical Gold digests, `_computed_ts` and `updated_at` both advancing each time — fresh evidence each run, same business content, no duplication. This supersedes the earlier "suggestive, not conclusive" comparison against a different/older run. |

## Related finding, not fixed this chapter

`clients_clean`/`campaigns_clean` dedup by a window ordered on the
constant-per-run `_ingest_ts`, the same class of bug `_row_id` was added to
fix for the fact tables, but touching those two dimension tables was out of
this chapter's stated scope. Moved to
[known-gaps.md](../known-gaps.md#clients_cleancampaigns_clean-dedup-ties-on-a-constant-timestamp)
so the register is the single home for cross-chapter gaps rather than
duplicating the writeup here.

## Roadmap acceptance mapping

- "Account for accepted, quarantined, and duplicate records without
  double-counting" — `reconcile()`'s conservation assertion,
  `test_reconcile_conserves_every_row`, **and live-verified** via
  `gate_status`'s `conserved` field matching directly-queried persisted
  table counts on every run, including the fault run.
- "A failed gate preserves the previously published data" — **live-verified**:
  the fault-stage run failed `bedoux_gate_task`, and Gold's digests were
  confirmed unchanged with `updated_at` predating the run entirely.
- "Normal input passes" — `test_normal_control_passes_the_gate`, and
  live-verified on the baseline, Milestone-4, restore, and replay runs.
- "Test repeated processing" — `test_replay_is_idempotent` at the
  pure-function level, and **live-verified** with a literal back-to-back
  replay (Stage 2 → Stage 3): identical business content and
  multiplicities, advancing audit timestamps, no duplication.
- "Do not claim whole-platform transactional publication unless actually
  implemented" — explicitly not claimed; see the business-decision section
  above. Unchanged by this demonstration.
