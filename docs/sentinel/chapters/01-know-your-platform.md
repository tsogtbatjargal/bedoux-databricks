# Part 01 — Know your platform

Status: integrated into `main` (merge commit `442c7a8`, PR #2). This is a historical
baseline before later chapters added controls. This chapter is a mapping
exercise: it describes what Track 2 (Bedoux) already does, states three
synthetic incident scenarios and a normal control that later chapters will
exercise, and records which claims below are verified against code versus
untested against a live workspace. Editorial drafts and publication tracking
are maintained outside this repository; see [repository scope](../repository-scope.md).

## Existing vs. planned

Everything in "Platform map" through "Trust boundaries" below describes the
chapter 01 baseline (verified by reading `src/bedoux/*.py`,
`resources/bedoux_*.yml`, and `databricks.yml`). Nothing in this chapter adds
new pipeline behavior. The "Planned" column in each table is what later
chapters (02–06) would add; those controls did not exist in this baseline.

## Platform map

| Layer / component | What it is today | Owner / operator | Business impact if wrong or missing |
| --- | --- | --- | --- |
| Generator (`src/bedoux/generator.py`) | Deterministic synthetic data, stdlib `random`, fixed seed `42`, no network access. Emits `clients`, `campaigns`, `leads`, `web_events`, `ops_events`. ~2% of `leads`/`web_events`/`ops_events` rows are deliberately invalid (null key, negative duration, missing latency). | Repo owner (sole maintainer of this portfolio project) | None directly — it's the synthetic source of truth, not a real feed. Its deliberate invalid-row rate is what gives Silver's expectations something real to catch. |
| Bronze (`bedoux_bronze_pipeline` → `workspace.bedoux_bronze`) | 5 raw tables, one per entity. `@dlt.table`, **recomputed in full every run** from the generator (not append-only — see the contract fix below). Adds `_ingest_ts`/`_source_table` only; no filtering. | Same pipeline job, `bedoux_analytics_job`, run as `tsoglog.uli@gmail.com` (the only identity configured in `databricks.yml`; Free Edition has no service principals) | If broken: no data reaches Silver/Gold at all — a full outage of this track, not a partial one, since every downstream table is recomputed from this layer each run. |
| Silver (`bedoux_silver_pipeline` → `workspace.bedoux_silver`) | Clean, conformed copies of Bronze. `clients_clean`/`campaigns_clean` are deduplicated by primary key (window function). `leads_clean`/`web_events_clean`/`ops_events_clean` apply `expect_or_drop` expectations and **have no dedup logic at all**. All five are `@dlt.table`s reading Bronze in batch (`spark.read.table`) — none are genuine DLT streaming tables; see the contract fix below. | Same job/identity as Bronze | Silently dropped or duplicated rows here change every Gold metric downstream with no record of what was dropped or why (no quarantine table exists yet — see Scenario A). |
| Gold (`bedoux_gold_pipeline` → `workspace.bedoux_gold`) | 3 business tables, one per question, reading Silver only: `gold_campaign_performance` (per campaign), `gold_client_funnel` (per client per month), `gold_ogi_ops_health` (per day). Formulas in `src/bedoux/transforms.py` are the tested reference; `gold.py` reimplements them as native Spark column expressions. | Same job/identity | Directly consumed by Genie/BI — a wrong number here is what a (fictional) client or the agency owner would actually see and act on. |
| Genie / BI | One shared 2X-Small SQL warehouse (Free Edition limit) queries both tracks' Gold layers via natural language. | Repo owner | Wrong Gold data flows straight through with no additional check at this layer. |
| CI/CD (`.github/workflows/ci.yml`) | Every PR/push runs `uv run --locked pytest`. A pinned `dorny/paths-filter` action gates `Validate bundle`/`Deploy bundle` on changes to `src/**`, `resources/**`, `databricks.yml`. PRs never deploy; only a bundle-path push to `main` or an opted-in manual dispatch deploys. Auth is a personal access token stored as a GitHub Actions secret (`DATABRICKS_HOST`/`DATABRICKS_TOKEN`), scoped to the one workspace identity above. | Repo owner | A leaked PAT is a full-workspace-identity compromise — there is no narrower service-principal scope available on Free Edition. This is a known, accepted trade-off (documented in `docs/architecture.md`), not an oversight. |

## Dataset dependencies

- `campaigns.client_id` → `clients.client_id`.
- `leads.campaign_id` → `campaigns.campaign_id`; `web_events.campaign_id` →
  `campaigns.campaign_id`.
- `ops_events` has no foreign key to any other entity — it's `ogi`'s own
  operational log, independent of client/campaign data.
- Gold reads Silver only, never Bronze and never a mix of layers (contract
  rule, verified against every `gold.py` function — all read from
  `workspace.bedoux_silver.*`).
- `leads.email_domain` is a domain string only (`gmail.com`, `yahoo.com`,
  `outlook.com`, `company.com` — see `generator.py:EMAIL_DOMAINS`), not an
  email address or phone number. Track 2 currently carries no email/phone PII
  anywhere in the pipeline; do not describe it as having any until a field
  that actually holds one is added (chapter 03's fictional sensitive fields
  will be the first).

## Trust boundaries

1. **Generator → Bronze.** Fully trusted today — synthetic, no external actor,
   no network call. This is also the boundary chapter 07's "instruction
   embedded in an ops message" scenario will eventually attack: `ops_events`
   currently has no free-text field at all (`event_type`, `success`,
   `latency_seconds`, `event_ts` only — checked against `generator.py`), so
   that scenario needs a schema addition before it can be exercised; out of
   scope for this chapter, noted for chapter 06/07 planning.
2. **Bronze → Silver.** The only validation boundary that exists today.
   `expect_or_drop` drops rows failing an expectation; there is no dead-letter
   table, no reason code, and no count of what was dropped — a quality
   incident today is invisible unless someone diffs row counts by hand. This
   is exactly the gap chapter 02 is scoped to close.
3. **CI/CD → Databricks workspace.** A single PAT-authenticated identity for
   both tracks; no per-track or per-job scoping (Free Edition constraint,
   documented already in `docs/architecture.md`).
4. **Databricks workspace → Genie/BI.** Any principal with warehouse/Genie
   space access can query both tracks' Gold tables; no row-level security is
   implemented or currently needed at this grain.
5. **(Planned, chapter 03) Evidence → model call.** Does not exist yet. No
   pipeline data is ever sent to a model today.
6. **(Planned, chapter 04/06) Agent → job/replay actions.** Does not exist
   yet. No agent has any access to this workspace today.

## Synthetic incident scenarios and normal control

These four scenarios reuse the roadmap's shared scenario set
(`docs/sentinel/roadmap.md`, "Shared scenario and deferred work"). The three
incident scenarios below are the ones chapter 02 is scoped against
("malformed values, duplicate leads, and missing campaign references"); the
other two shared scenarios (an unexpected sensitive field, an instruction
embedded in an ops message) belong to chapters 03 and 06/07 respectively and
are out of scope here.

### Scenario A — Malformed lead batch

- **Input:** a `leads` batch with an elevated null-`campaign_id` rate (the
  seeded generator already produces this at ~2% via `INVALID_RATE`; a test
  fixture can raise the rate to make the effect obvious, e.g. 15%).
- **Expected today:** `leads_clean`'s `expect_or_drop("valid_campaign_id", ...)`
  drops every null-`campaign_id` row. Gold aggregates over the reduced set.
  Nothing records how many rows were dropped or why — verified by reading
  `silver.py:59-75`, which has no output path for rejected rows.
- **Expected after chapter 02:** rejected rows land in a persistent quarantine
  table with a reason code; quality metrics report the reject count instead of
  silently shrinking the aggregate.

### Scenario B — Duplicate leads

- **Input:** the same `lead_id` present twice in a Bronze run (e.g., a
  duplicated job trigger or a replayed generator batch — plausible today
  because Bronze has no incremental identity tracking; it's a full recompute
  each run).
- **Expected today:** no dedup logic exists on `leads_clean` — verified by
  reading `silver.py`: `clients_clean`/`campaigns_clean` dedup via a
  `row_number()` window over `_ingest_ts`, but `leads_clean`,
  `web_events_clean`, and `ops_events_clean` apply only `expect_or_drop` and
  no window function. A duplicate `lead_id` would be counted twice in every
  Gold aggregate that touches `leads_clean` (`count("*")`,
  `sum(when(stage == 'won', ...))` in both `gold_campaign_performance` and
  `gold_client_funnel`).
- **Expected after chapter 02:** deterministic row-order identity (`_row_id`,
  not batch/run identity) is added so a duplicate is recognized and excluded
  from double-counting.

### Scenario C — Missing campaign reference

- **Input:** a `leads` (or `web_events`) row whose `campaign_id` is non-null
  but does not exist in `campaigns_clean` (e.g., a campaign that was deleted
  or never generated in that run).
- **Expected today:** `valid_campaign_id` only checks `IS NOT NULL`, not
  existence in `campaigns_clean` — verified in `silver.py:63`. Downstream,
  `gold_client_funnel` inner-joins `leads` to `campaigns`
  (`gold.py:60`), so the orphaned lead is silently dropped from that table.
  `gold_campaign_performance` left-joins from `campaigns` as the driving side
  (`gold.py:32`), so an orphaned lead's aggregate row in `lead_agg` simply has
  no matching `campaigns` row to attach to and is excluded the same way. In
  both cases the lead disappears from Gold with no error, log line, or count
  — verified by reading the join logic; not exercised against a live fixture
  this session.
- **Expected after chapter 02:** the referenced acceptance criteria requires
  an explicit decision — reject the individual record or withhold the
  affected Gold refresh — documented with a business reason once chapter 02
  is scoped.

### Normal control — Healthy batch

- **Input:** the default seeded generator run (`seed=42`, `N_LEADS=500`,
  `N_WEB_EVENTS=2000`, `N_OPS_EVENTS=365`), unmodified — the same run Bronze
  already performs. `generate_leads`/`generate_web_events` draw `campaign_id`
  only from the `campaign_ids` list passed in, so every non-null
  `campaign_id` is valid by construction; the only invalidity the generator
  introduces is a null key at the fixed ~2% rate, never a wrong one.
- **Expected:** Bronze recompute succeeds; Silver's expectations drop only the
  deliberately-invalid ~2% (verified count: `tests/test_generator.py` checks
  generator output shape, not the dropped count itself — the exact number
  after Silver's expectations run has not been measured this session, since
  that needs a live pipeline execution); Gold computes with no anomaly. This
  is the baseline every incident scenario above is a deviation from.

## Capability checks

| Check | Status | Evidence |
| --- | --- | --- |
| Local unit tests (`generator`, `transforms`) | **Verified** | `uv run --locked python -m pytest -q` — 17 passed, this session. |
| Scenario B claim (no dedup on `leads_clean`/`web_events_clean`/`ops_events_clean`) | **Verified** | Read `src/bedoux/silver.py` directly; confirmed absence of any `row_number()`/window dedup on those three tables. |
| Scenario C claim (join behavior on an orphaned `campaign_id`) | **Verified against code, untested against data** | Read the join logic in `src/bedoux/gold.py`; not exercised with an actual orphaned-row fixture this session. |
| Contract self-contradiction (Bronze "append-only" vs. "full recompute") | **Verified and fixed** | Read `docs/contracts-bedoux.md` lines 49 and 58–61 side by side; corrected in this chapter. |
| Contract/code mismatch (Silver "streaming tables" vs. batch `@dlt.table`) | **Verified and fixed** | Compared `docs/contracts-bedoux.md` line 87 against `src/bedoux/silver.py`'s module comment and actual `@dlt.table`/`spark.read.table` usage; corrected in this chapter. |
| `databricks bundle validate --target dev` | **Unavailable** | No `DATABRICKS_HOST`/`DATABRICKS_TOKEN` in this environment, no `~/.databrickscfg`, and the `databricks` CLI itself is not installed locally. |
| Live Bronze → Silver → Gold pipeline run | **Unavailable** | Same reason; no workspace credentials in this session. |
| Genie space query behavior over `bedoux_gold` | **Unavailable** | Same reason. |
| Exact row counts after a live Silver expectation run (normal control) | **Untested** | Would require the live pipeline run above; not attempted. |

No live baseline was recorded this session because workspace access is
unavailable in this environment, not because it was skipped by choice. The
local work above (contract fixes, code-verified scenario claims, unit tests)
stands on its own; live behavior remains explicitly unverified until a
session with workspace credentials records it.
