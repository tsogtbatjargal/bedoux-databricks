# Layer Contracts — Track 3: Regulated Gaming & Retail Lakehouse

Companion to [`contracts.md`](contracts.md) (Track 1) and
[`contracts-bedoux.md`](contracts-bedoux.md) (Track 2). Same contracts-first method,
applied to a **regulated** domain: a provincial agency that runs online gaming and
wholesales liquor and cannabis. It's shaped like a public-sector gaming and liquor
regulator. It is **not** any real organization's data, schema or system.

**All data in this track is synthetic and fictional.** Players, emails, birth dates,
licensees and orders come from a seeded generator (`src/aglc/generator.py`). Databricks
Free Edition is non-commercial, so this is a portfolio demonstration only.

What this track adds that Tracks 1–2 don't:

1. **Domain ownership.** Three domains (`gaming`, `liquor`, `cannabis`), each owning its
   tables, plus a shared retail fact that's row-filtered by domain.
2. **Sensitive data by design.** Player email and date of birth are PII. They're masked by
   Unity Catalog column masks, not by convention.
3. **Responsible-gaming controls.** Explainable rule flags, not a model, so every flag
   can be traced to a threshold.
4. **Legacy-to-lakehouse reconciliation.** A simulated legacy report (SSRS-style export)
   must match the new Gold table before "cutover".

Catalog: `${var.catalog}` (default `workspace`). One schema per layer: `aglc_bronze`,
`aglc_silver`, `aglc_gold`, plus `aglc_legacy` (simulated legacy exports) and
`aglc_governance` (mask and filter functions). Table names carry their domain prefix.

---

## Naming (locked)

| Layer  | Schema | Pattern | Example |
|---|---|---|---|
| Bronze | `aglc_bronze` | `<domain>_<source>_raw` | `gaming_wagers_raw` |
| Silver | `aglc_silver` | `<domain>_<source>_clean` | `gaming_wagers_clean` |
| Gold   | `aglc_gold`   | `gold_<question>` | `gold_rg_player_flags` |
| Legacy | `aglc_legacy` | `legacy_<report>` | `legacy_retail_sales_daily` |

`retail` is the shared prefix for liquor and cannabis together (`retail_orders_raw`).
Every retail row carries a `domain` column (`liquor` | `cannabis`).

---

## Source entities (synthetic)

| Entity | Domain | Grain | Notes |
|---|---|---|---|
| `players` | gaming | one row per player | `email`, `date_of_birth` are **PII**; `region`; `self_excluded` flag |
| `sessions` | gaming | one row per play session | `duration_minutes` |
| `wagers` | gaming | one row per wager | `game_type`, `stake`, `payout` |
| `deposits` | gaming | one row per deposit | `amount` |
| `licensees` | retail | one row per licensed retailer | `domain`, `region` |
| `orders` | retail | one row per wholesale order line | `domain`, `product_category`, `quantity`, `amount` |

Deliberately invalid rows (about 2%) are generated so Silver expectations have something
real to drop: null `player_id` on wagers, non-positive `stake`, negative
`duration_minutes`, null `licensee_id` or negative `amount` on orders.

The generator also **plants risky behaviour** in a small, fixed set of players (loss
chasing, deposit spikes, marathon sessions, play while self-excluded) so the
responsible-gaming flags are demonstrable. Which players are planted is deterministic
and exposed for tests (`generator.PLANTED`).

---

## Bronze — `aglc_bronze`

Raw landing from the generator. Materialized, idempotent recompute (same reasoning as
Track 2: there's no real upstream stream). Each row gets `_ingest_ts`, `_source_table`
and `_row_id`. No filtering.

## Silver — `aglc_silver`

Typed, validated, conformed. DLT expectations **drop** invalid rows:

| Table | Expectation (drop) |
|---|---|
| `gaming_players_clean` | `player_id IS NOT NULL` |
| `gaming_sessions_clean` | `player_id IS NOT NULL AND duration_minutes >= 0` |
| `gaming_wagers_clean` | `player_id IS NOT NULL AND stake > 0 AND payout >= 0` |
| `gaming_deposits_clean` | `player_id IS NOT NULL AND amount > 0` |
| `retail_licensees_clean` | `licensee_id IS NOT NULL AND domain IN ('liquor','cannabis')` |
| `retail_orders_clean` | `licensee_id IS NOT NULL AND amount >= 0 AND quantity > 0` |

PII stays in `gaming_players_clean`, protected by column masks (see Governance).
Downstream Gold tables carry `player_id` only, never email or DOB.

## Gold — `aglc_gold`

| Table | Grain | Purpose |
|---|---|---|
| `gold_gaming_player_daily` | player × day | stake, payout, net loss, deposits, session minutes |
| `gold_rg_player_flags` | player | responsible-gaming flags + risk level + explanation |
| `gold_retail_sales_daily` | domain × region × category × day | order count, units, revenue. **Row-filtered by domain.** |

### Responsible-gaming rules (illustrative thresholds, not clinical guidance)

Reference implementation: `src/aglc/rules.py` (pure Python, unit-tested). The Gold DLT
code must produce the same result.

| Flag | Rule |
|---|---|
| `flag_chasing_losses` | at least `3` days where `net_loss > 0` and `deposit_count >= 2` |
| `flag_deposit_spike` | at least `5` deposit days, and max daily deposit total `> 3×` the player's median daily deposit total |
| `flag_long_session` | any session `>= 240` minutes |
| `flag_self_exclusion_breach` | player is `self_excluded` and has any wager |

`risk_level`: `high` if self-exclusion breach or `>= 2` other flags; `medium` if 1; else `low`.
`explanation`: the triggered rules in plain words, for the compliance reviewer.

## Legacy — `aglc_legacy`

`legacy_retail_sales_daily` simulates a report exported from the old BI stack
(SSIS-loaded, SSRS-rendered). It's computed **independently** in plain Python from the
same synthetic orders (`src/aglc/legacy.py`), applying the legacy report's own rule: it
excluded invalid rows the same way. A deploy-time variable can inject a known
discrepancy to prove the reconciliation catches it.

## Reconciliation (cutover gate)

`src/aglc/reconcile.py` compares `gold_retail_sales_daily` with
`legacy_retail_sales_daily` on the key (`domain, region, product_category, order_date`):

- keys missing on either side
- `order_count`, `units` exact match; `revenue` within `0.01`

The result is a report (`passed`, counts, first N mismatches). Cutover is allowed only
when `passed` is true. This is the parallel-run step of a migration, written as code.

---

## Governance (Unity Catalog)

Functions live in `aglc_governance`. Statements are generated by
`src/aglc/governance.py` (unit-tested) and applied by a job task.

| Control | Applies to | Rule |
|---|---|---|
| Column mask `mask_email` | `gaming_players_clean.email` | clear for `aglc_compliance`, else `***@domain` |
| Column mask `mask_dob` | `gaming_players_clean.date_of_birth` | clear for `aglc_compliance`, else birth year only |
| Row filter `filter_domain` | `gold_retail_sales_daily(domain)` | `aglc_engineer`/`aglc_compliance` see all; `aglc_liquor_analyst` sees liquor; `aglc_cannabis_analyst` sees cannabis |
| Grants | schemas | analysts: `SELECT` on `aglc_gold` only; engineers: all layers; compliance: `aglc_gold` + `gaming_players_clean` |

Groups are checked with `is_account_group_member()`. On Free Edition, group creation and
mask/filter support are **unverified**. Verify before relying on them; see
[`adr/0004`](adr/0004-uc-masks-not-separate-pii-table.md).

## Status

Planned and partly implemented. See `docs/sentinel/handoff.md` and Git history for what's
implemented versus demonstrated live.
