# Session handoff

Updated: 2026-09-22. **All three stages of the fault → restore → replay
demonstration are confirmed live — chapter 02 is now demonstrated, not just
implemented and locally tested.** `dev` is deployed at the normal
`bedoux_lead_invalid_rate=0.02`. See "Fault → restore → replay
demonstration" below for full evidence, and "Exact next task" for the
merge recommendation.

Earlier: **the blocking defect from the live baseline run
(below) is root-caused, fixed, unit-tested, confirmed live, and pushed —
PR #3 now reflects it and CI is green on the fixed code.** Root cause:
`silver.py` built `_reasons` with `array_remove(array(...), None)`, and
Spark's `array_remove` is null-intolerant on its *element* argument — a NULL
element makes the whole array result NULL, not stripped of NULLs — so
`_reasons` was NULL on every row, silently emptying
`leads_clean`/`leads_quarantine` (and the same pair for web_events/
ops_events) and `quality_metrics`, while `gate_status` computed a
self-consistent but wrong "pass" from that same NULL. Fixed with
`array_compact` plus `expect_or_fail` guards (Milestone 1), and — more
importantly — `gate_status` now independently checks row conservation
against the *persisted* clean/quarantine tables, which is what would have
actually caught this (Milestone 2). See "Incident" in
[chapters/02-quality-gate.md](chapters/02-quality-gate.md) for the full
writeup. **Correction to this file's own prior claim:** the destroyed Gold
baseline was not unrecoverable — every business row is deterministic from
`SEED=42` in `generator.py`; only audit timestamps (`_ingest_ts`,
`_quarantined_ts`, `_computed_ts`, table `updated_at`) were ever
irreproducible. The live re-run reproduced the 2026-07-30 baseline's Gold
content byte-for-byte, confirming this.
This file records context, not permission to merge, deploy, run jobs,
change secrets, bind resources, or publish. Inspect Git before continuing.

## Current checkpoint

- Branch: `series/02-quality-gate`, **pushed and in sync with origin**, head
  `15a2203` (plus one more doc-only commit landing with this update). PR #3
  is open, `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`, CI green on the
  fixed code.
- This session's commits: `26b9d99` (incident record), `9d3ca54` (the fix),
  `a80c914` (live re-run confirmation), `8331824` (commit-count correction),
  `f63f113` (push record), `52e09fb` (fault-stage safety checkpoint),
  `15a2203` (fault+restore evidence) — all pushed, each authorized (docs-only
  commits were pre-authorized this session; the code fix and earlier push
  were separately authorized in prior turns).
- Working tree clean. No merge or deploy of Track 1 has occurred. **Five**
  job runs occurred across this session and the prior one: healthy baseline
  (found the incident), healthy re-run (confirmed the fix), fault 0.30
  (confirmed withholding), restore 0.02, replay 0.02 (confirmed no
  duplication back-to-back). `dev` is currently deployed at the normal
  `bedoux_lead_invalid_rate=0.02`.
- Track 1 source/resources and CI policy are unchanged.
- Chapters 00/01 are integrated into main; remote chapter branches retained.
- **Not merged.** See "Exact next task" for the merge recommendation — a
  demonstrated chapter is not the same as authorization to merge; that
  remains yours to decide.

## Implementation now in the checkout

- Bronze/Silver generate fictional data, quarantine rejected facts with
  reasons, and count rows without double-counting multi-reason records.
- The ordinary `bedoux_gate_task` notebook runs after Silver and before Gold.
  Gold has no imperative gate or self-referencing fallback. Failed gate means
  the whole Gold pipeline should not run, including a first-ever run.
- `_flagged` views build `_reasons` with `array_compact(array(...))`
  (**not** `array_remove(..., None)` — see "Incident" below and the chapter
  doc) and are guarded by `@dlt.expect_or_fail("reasons_not_null", ...)`.
- `gate_status` computes `total`/`quarantined`/`quarantine_rate`/`gate_passed`
  from the `_flagged` views (unchanged since the double-counting fix), **and
  now also** reads the persisted `<source>_clean`/`<source>_quarantine`
  tables directly to compute `accepted_rows`/`quarantined_rows`/`conserved`.
- `quality.evaluate_gate` withholds unless `gate_passed`, `conserved` are both
  strictly true and `total > 0`, on top of the pre-existing absent/duplicate
  source, null/stale timestamp, and run-boundary checks.
- The task requires `{{job.start_time.timestamp_ms}}`. It converts Spark
  timestamps with `unix_millis` before Python collection and uses explicit
  UTC datetimes. Missing/unresolved widgets cannot disable freshness.
- Bundle variable `bedoux_lead_invalid_rate` feeds pipeline configuration
  `bedoux.lead_invalid_rate`; default 0.02, demo fault 0.30, valid range 0..1.
  This is a deploy-time override, not a job-run parameter. Currently deployed
  at `0.02` (the normal setting) after this session's two runs.

## Important limits

- Timestamp freshness is **not exact run/batch binding**. The supported demo
  assumes one full serialized job and no other writers, direct pipeline runs,
  repair-only runs, or deployments mid-run. Exact batch/version binding is
  not implemented. Direct Gold execution bypasses the gate.
- Gold withholding is whole-pipeline, not per-table. Successful gate approval
  does not make subsequent multi-table Gold publication atomic.
- Row conservation catches "the split doesn't add up to the input"; it does
  not catch every possible Spark-logic defect that still conserves row
  counts (e.g. a misclassification that quarantines the right count of rows
  for the wrong reason). See the chapter doc's incident writeup for the exact
  scope of what this closes.
- CI credentials are configured and **proven working** (PAT, repo secrets;
  see "CI verification" below). Merging PR #3 would deploy, since bundle-path
  changes + working credentials both apply on a `main` push. PR #3 now
  reflects the incident and the fix (pushed this session) and CI is green on
  the fixed code — but a green PR is still not a merge decision.
- Full `bundle deploy` includes both tracks. Do not confuse unchanged Track 1
  source with a Track-2-only deployment.
- Databricks CLI is installed locally and OAuth-authenticated (see
  "Databricks CLI access" below). `bundle validate`/`bundle plan`/
  `bundle deploy`/`bundle run` have all now executed successfully multiple
  times against `dev`, across two full job runs.

## Deployment and baseline run (2026-09-21, this session)

Scope authorized: controlled preflight, one deploy to `dev` at
`bedoux_lead_invalid_rate=0.02`, one job run. No fault injection.

**Preflight** (all under profile `bedoux-databricks`, target `dev`):
- Commit `281efe0c11389e043c1c7bc2082462864bde7acb`, identity
  `tsoglog.uli@gmail.com`, working tree clean, local/remote in sync.
- No active runs on `bedoux_analytics_job` (133273744478391) or
  `tpch_medallion_pipeline_job` (32014554262162); no in-progress updates on
  any of the six pipelines. Confirmed read-only, then enforced with
  `--fail-on-active-runs` on deploy (not just checked).
- `databricks bundle plan -t dev --var bedoux_lead_invalid_rate=0.02`:
  `0 to add, 2 to change, 0 to delete, 6 unchanged` — only
  `jobs.bedoux_analytics_job` (adds the gate task) and
  `pipelines.bedoux_bronze_pipeline` (adds the invalid-rate config) change.
  No deletions/replacements, Track 1 untouched.
- Pre-deploy Gold baseline captured via the serverless SQL warehouse
  (`e63747243511532c`), order-independent digest
  (`sha2(concat_ws('||', sort_array(collect_list(md5(to_json(struct(*)))))), 256)`):

  | Table | Rows | `updated_at` (UTC) | Digest |
  |---|---|---|---|
  | `gold_campaign_performance` | 30 | 2026-07-30T20:41:58.494Z | `72575a78...a805dba` |
  | `gold_client_funnel` | 132 | 2026-07-30T20:42:03.654Z | `636c7dd0...7df1c2e` |
  | `gold_ogi_ops_health` | 183 | 2026-07-30T20:41:58.483Z | `72aef48d...2083e41d` |

  (Full digests are in this session's transcript; truncated here for
  readability, not secrecy.) This is the pre-chapter-02 baseline being
  replaced by the healthy gated run below — expected and accepted per this
  task's scope, not a loss.
- `databricks bundle validate -t dev`: Validation OK, both before and
  immediately before deploy.

**Deploy:** `databricks bundle deploy -t dev --var bedoux_lead_invalid_rate=0.02
--fail-on-active-runs` (no `--auto-approve`). Result: `0 created, 2 changed, 0
deleted, 6 unchanged` — matched the plan exactly. Confirmed post-deploy by
reading the live job/pipeline definitions back:
- `bedoux_analytics_job` task graph: `bedoux_bronze_task` →
  `bedoux_silver_task` → `bedoux_gate_task` (notebook) → `bedoux_gold_task`.
  `max_concurrent_runs: 1`.
- `bedoux_bronze_pipeline` configuration: `bedoux.lead_invalid_rate: "0.02"`.

This is the first deploy that introduces the gate to `dev` — the job's live
graph was previously the ungated bronze → silver → gold from before chapter 02.

## Baseline run result: BLOCKING DEFECT found, not a clean pass

Run `343186547330463` (job 133273744478391), `bedoux_lead_invalid_rate=0.02`,
started 2026-09-21T23:37:51Z, ended 23:43:46Z.
Run URL: `https://dbc-3f70aae3-11d5.cloud.databricks.com/jobs/133273744478391/runs/343186547330463?o=7474656218808128`.

**All four tasks reported `SUCCESS`** (bronze, silver, gate, gold), and the
pipeline event log shows every flow completing with no WARN/ERROR events and
no exceptions. **Job-level success is not trustworthy evidence here** — the
underlying data tells a different story, confirmed with fresh queries several
minutes apart (not a caching artifact) and with a byte-for-byte diff of the
deployed `silver.py` against the local checkout (identical — not a stale-code
artifact):

- Bronze populated correctly: `leads_raw` 500, `web_events_raw` 2000,
  `ops_events_raw` 365 rows. `clients_clean`/`campaigns_clean` (unrelated
  dimension logic) also correct: 10 / 30 rows.
- **`leads_clean`, `leads_quarantine`, `web_events_clean`,
  `web_events_quarantine`, `ops_events_clean`, `ops_events_quarantine`, and
  `quality_metrics` are all 0 rows** — despite `dataset_life_cycle` events
  confirming each was freshly (re)created/refreshed by this exact run
  (`updated_at` timestamps match the run window). 2,865 fact rows
  (500+2000+365) went into Bronze and **zero came out the other side of the
  clean/quarantine split, in either table** — the precise "nothing vanishes
  without a record" failure mode chapter 02 was built to close, now observed
  live on a run the job reported as a full success.
- **`gate_status` itself is internally inconsistent with that reality**: it
  reports `total=500/2000/365, quarantined=0, gate_passed=true` for
  leads/web_events/ops_events (`_computed_ts` 2026-09-21T23:40:51.869Z) —
  plausible-looking numbers that match Bronze's counts, but they cannot be
  correct, because `_row_counts` reads the exact same `dlt.read(view_name)`
  the (also-empty) `_clean`/`_quarantine` tables read, with the same
  `size(_reasons)` predicate. Both cannot be right; the persistent tables
  (0 rows, physically verified) are the ones that matter, so gate_status's
  "pass" is not trustworthy evidence that the gate is protecting anything
  right now.
- **Gold cascaded the damage**: because gate_status said pass, `bedoux_gold_task`
  ran and overwrote the previous 2026-07-30 baseline.
  `gold_campaign_performance` still has 30 rows (one per campaign, from
  `campaigns_clean` which is healthy) but every row now has `lead_count=0`,
  `won_count=0`, `conversion_rate=0.0`, `cost_per_lead=NULL` — confirmed by
  direct query. `gold_client_funnel` went from 132 rows to **0**.
  `gold_ogi_ops_health` went from 183 rows to **0**. The prior baseline's
  content is gone from these two tables, replaced with empty tables, not
  with a new valid healthy baseline.
- Update IDs for the record: bronze `bd8fee68-1a78-4f95-b5e7-8fb123e224d7`,
  silver `adc3328b-e2cc-4caa-88a2-a420099f34c4`, gold
  `664c30db-3e65-44e0-ae2b-bba1a04b97e7`, all `COMPLETED`.

**Root cause found and fixed — correcting the guess below.** At the time
this incident was first recorded, the cause hadn't been identified from
CLI-level tools, and the paragraph below speculated it was a DLT/Lakeflow
runtime quirk needing Spark UI/driver-log access. **That guess was wrong.**
The actual cause was found directly in the source, no Spark UI needed:
`silver.py` built `_reasons` with `array_remove(array(...), None)`, and
Spark's `array_remove(array, element)` is null-intolerant on its *element*
argument — when `element` is NULL, the result is NULL (not the array with
NULLs stripped). Every `when(...)` with no `.otherwise()` evaluates to NULL
when false, so `array(...)` always contained a NULL, and
`array_remove(..., None)` therefore made `_reasons` NULL on **every row, in
all three `*_flagged` views, unconditionally** — silently, since NULL
propagation raises no exception, which matches the clean pipeline event log
observed below. Every downstream reader inherited a different
self-consistent-looking wrong answer from that same NULL: `size(_reasons) ==
0`/`> 0` are both NULL so neither `_clean` nor `_quarantine` matched
anything, `explode(NULL)` emitted nothing for `quality_metrics`, and the
original `(size(_reasons) > 0).cast("int")` evaluated to `0` for every row,
which is exactly why `gate_status` reported a clean `quarantined=0`. Fixed
with `array_compact` (which does strip NULLs) plus `expect_or_fail` guards,
and — the more important part — `gate_status` now cross-checks against the
persisted `_clean`/`_quarantine` tables independently of the `_flagged`-view
arithmetic, so a future defect in that same view wouldn't again produce a
self-consistent false pass. (Before this was found, a stale-cache explanation
was ruled out by re-querying ~6 minutes apart with the same result, and a
stale-deployed-code explanation was ruled out by diffing the deployed
`silver.py` byte-for-byte against the checkout — identical; both are still
valid, just superseded by the real cause above.) Full writeup:
[chapters/02-quality-gate.md](chapters/02-quality-gate.md#incident-the-gate-passed-a-100-row-loss-run).

**Left in this state deliberately, not rerun.** Per this task's instructions
not to repeatedly rerun or bypass the gate on a failure — and this is worse
than the anticipated "gate task fails" case, since here it silently reported
success while losing data. Current live `dev` state: Bronze and the two
dimension tables are healthy; all three fact-source clean/quarantine tables
and `quality_metrics` are empty; `gate_status` shows a false-looking pass;
Gold has empty/degenerate content for all three tables where it previously
had a real 2026-07-30 baseline. Rollback (redeploy from `main`) would restore
the *ungated* graph, not fix this. **Correction:** an earlier version of this
note called the destroyed baseline unrecoverable; that overstated it. Every
business row is deterministic from `generator.py`'s fixed `SEED = 42`, and
(re-confirmed live) none of the three Gold tables' schemas carry an audit
timestamp column — `gold_campaign_performance`, `gold_client_funnel`, and
`gold_ogi_ops_health` are pure business content. So a correct healthy run at
`bedoux_lead_invalid_rate=0.02` should reproduce the 2026-07-30 baseline's
Gold content **exactly**, and the pre-run digests recorded above are a valid
exact-match check for that, not just a fingerprint of something gone. (Silver
does carry audit columns — `_ingest_ts`, `_quarantined_ts` — so a
row-for-row Silver digest would differ across runs even when correct; the
digests above were only taken for Gold, where this doesn't apply.)

## Re-run result: fix confirmed live (2026-09-21, same session)

After Milestones 1–3 (root cause, fix, tests — see `9d3ca54`), ran the exact
Milestone-4 sequence: `bundle validate` → `bundle plan` (`0 to add, 0 to
change, 0 to delete, 8 unchanged` — this fix only changes library file
contents, not resource definitions, so the plan correctly shows no resource
diff) → confirmed no active runs → `bundle deploy -t dev --var
bedoux_lead_invalid_rate=0.02 --fail-on-active-runs` (no `--auto-approve`) →
diffed the deployed `silver.py` byte-for-byte against the checkout
(identical) → `bundle run bedoux_analytics_job`.

Run `470702296963638`, started 2026-09-21T18:09:32Z, ended 18:15:15Z. **All
four tasks `SUCCESS`, and this time verified against the actual data, not
just job status** — the same discipline that caught the incident:

| Source | `gate_status` total/quarantined/conserved/gate_passed | Directly queried `_clean`/`_quarantine` counts | Match? |
|---|---|---|---|
| leads | 500 / 10 / true / true | 490 / 10 | **yes, exactly** |
| web_events | 2000 / 46 / true / true | 1954 / 46 | **yes, exactly** |
| ops_events | 365 / 8 / true / true | 357 / 8 | **yes, exactly** |

Quarantine rates: leads 2.0%, web_events 2.3%, ops_events 2.2% — all close to
the generator's ~2% baseline and comfortably under the 10% threshold.
`quality_metrics` breakdown is sane: `leads`/`null_campaign_id`×10,
`web_events`/`invalid_duration`×46, `ops_events`/`invalid_latency`×8, plus
the three `accepted` counts. Gold refreshed: `gold_campaign_performance` 30
rows with real non-zero `lead_count`/`won_count`/`conversion_rate` and
non-NULL `cost_per_lead` (e.g. campaign 1: 15 leads, 4 won, 26.7% conversion,
$236.13/lead); `gold_client_funnel` 132 rows; `gold_ogi_ops_health` 183 rows.

**All three Gold tables' order-independent content digests matched the
pre-incident 2026-07-30 baseline exactly** (`gold_campaign_performance`
`72575a78...a805dba`, `gold_client_funnel` `636c7dd0...7df1c2e`,
`gold_ogi_ops_health` `72aef48d...2083e41d` — same digests recorded in the
preflight section above). This confirms live the correction made above: the
destroyed baseline was fully recoverable, byte-for-byte, because of
`SEED=42` determinism and Gold's lack of audit columns.

Update IDs for the record: bronze/silver/gold pipelines each ran a fresh
`COMPLETE_RECOMPUTE` update under this run; `gate_status._computed_ts` =
`2026-09-22T00:12:43.113Z` for all three sources (one shared computation, as
expected for a single `gate_status` table refresh).

**What this run does and does not establish:** it proves a healthy run now
correctly passes with self-consistent, conserved evidence, and that the fix
didn't regress anything Milestone 4's acceptance criteria named. At the time
this section was written, the withhold path was still unexercised. It has
since been — see "Fault → restore → replay demonstration" below, done in a
later turn of this same continued session.

## Fault → restore → replay demonstration (2026-09-21/22, one session)

Authorized scope: three job runs (fault 0.30, restore 0.02, replay 0.02),
chained without stopping between fault and restore. All three completed in
this session. Baseline digests (recorded above, re-confirmed clean
immediately before Stage 1) —
`gold_campaign_performance` `72575a78...a805dba` (30 rows),
`gold_client_funnel` `636c7dd0...7df1c2e` (132 rows),
`gold_ogi_ops_health` `72aef48d...2083e41d` (183 rows).

### Stage 1 — FAULT (0.30)

Preflight: no active runs; `bundle plan` showed only
`pipelines.bedoux_bronze_pipeline` changing (the invalid-rate config), 0
deletions. Deployed with `--fail-on-active-runs`, no `--auto-approve`;
confirmed the live pipeline config read back `bedoux.lead_invalid_rate:
"0.30"` before running.

Run `330174171866992`, 2026-09-21T18:33:28–18:38:31 (local). Job-level
result: **FAILED** — `bedoux_gate_task` raised
`RuntimeError: Publication gate failed; withholding Gold refresh: - leads:
gate_passed is false (quarantine rate 32.8%)`. Per-task: `bedoux_bronze_task`
SUCCESS, `bedoux_silver_task` SUCCESS, `bedoux_gate_task` FAILED (two
attempts, both failed identically — Databricks' own retry, not something
this pipeline configured), `bedoux_gold_task` SKIPPED (`UPSTREAM_FAILED`).

A red job alone is not proof of withholding (an `expect_or_fail` firing, a
notebook bug, or a conservation false-positive would look identical from job
status). Queried `gate_status` directly — the actual evidence, not the
notebook's stdout, which `jobs get-run-output` doesn't capture for a
notebook that never calls `dbutils.notebook.exit()`:

| source | total | quarantined | accepted_rows | quarantined_rows | rate | gate_passed | conserved |
|---|---|---|---|---|---|---|---|
| leads | 500 | 164 | 336 | 164 | 32.8% | **false** | **true** |
| web_events | 2000 | 46 | 1954 | 46 | 2.3% | true | true |
| ops_events | 365 | 8 | 357 | 8 | 2.19% | true | true |

**Exact match to the predicted 336/164/32.80%** — no divergence between
`quality.py`'s reference rules and `silver.py`'s Spark expressions to
investigate. `conserved=true` on the failing row is the specific thing this
chapter needed to prove: a genuinely high, *conserved* rate, not another
silent-loss defect wearing a different number. web_events/ops_events
correctly unaffected (only leads uses the override) and both still conserved
and passing.

Directly queried all three Gold tables afterward: **digests unchanged**
(`72575a78...`, `636c7dd0...`, `72aef48d...` — identical to the pre-stage
baseline) and `updated_at` (00:15:07.9/7.1/7.1Z) **predates this run's start
entirely** — not just "unchanged since a recent check," proof Gold was never
touched, not coincidentally regenerated to the same values.

### Stage 2 — RESTORE (0.02)

Did not assume reversion; explicitly re-validated, re-planned (`bundle plan`
showed the same single-resource change back), and redeployed
`bedoux_lead_invalid_rate=0.02` with `--fail-on-active-runs`. Confirmed the
live pipeline config read back `"0.02"` before running.

Run `262274593519322`, 2026-09-21T18:40:19–18:46:24. All four tasks
**SUCCESS**. `gate_status`:

| source | total | quarantined | accepted_rows | quarantined_rows | rate | gate_passed | conserved |
|---|---|---|---|---|---|---|---|
| leads | 500 | 10 | 490 | 10 | 2.0% | true | true |
| web_events | 2000 | 46 | 1954 | 46 | 2.3% | true | true |
| ops_events | 365 | 8 | 357 | 8 | 2.19% | true | true |

Back to the same 490/10 as the confirmed-good Milestone-4 run. Gold's three
digests matched the baseline **again, exactly** — and this time `updated_at`
**advanced** (to 00:46:17–18Z, after this run's `gate_status._computed_ts`
00:44:20.768Z) confirming Gold genuinely re-derived the content rather than
being left alone — a real recomputation landing on identical business
content, not a no-op.

### Stage 3 — REPLAY (0.02)

No config change, no deploy — ran `bedoux_analytics_job` again immediately.
Run `98756061776337`, 2026-09-21T19:20:43–19:26:50. All four tasks
**SUCCESS**. `gate_status`:

| source | total | quarantined | accepted_rows | quarantined_rows | rate | gate_passed | conserved |
|---|---|---|---|---|---|---|---|
| leads | 500 | 10 | 490 | 10 | 2.0% | true | true |
| web_events | 2000 | 46 | 1954 | 46 | 2.3% | true | true |
| ops_events | 365 | 8 | 357 | 8 | 2.19% | true | true |

Identical to Stage 2 in every field except `_computed_ts`, which
**advanced** from `00:44:20.768Z` (Stage 2) to `01:24:03.322Z` (Stage 3) —
fresh evidence each run, not stale evidence reused. Directly re-queried the
persisted Silver tables (not just `gate_status`): `leads_clean`/
`leads_quarantine` 490/10, `web_events_clean`/`quarantine` 1954/46,
`ops_events_clean`/`quarantine` 357/8 — exact match to Stage 2. Gold's three
digests matched the baseline **again**, and `updated_at` **advanced again**
(01:26:34Z, after this run's own `_computed_ts`) — a third independent
recomputation landing on byte-identical business content.

This is the literal back-to-back replay evidence that was missing before:
two consecutive runs of the exact same healthy job (Stage 2 → Stage 3, no
config change between them) produced identical business content and
multiplicities with fresh, advancing audit timestamps — not the
"compared against a different, older run" caveat that applied to the first
post-fix confirmation.

**All three stages of the fault → restoration → replay demonstration are
now confirmed live**, closing every gap this file previously listed as
untested: the withhold path fired correctly on a genuine (not
false-positive) high rate, restoration was explicit and verified rather than
assumed, and replay was observed back-to-back rather than argued
architecturally. Full per-check status is in the chapter doc's verification
table.

## Databricks CLI access

- Installed the official Databricks CLI `v1.17.0` (matched GitHub's `latest`
  release at install time) via mise's explicit `github:databricks/cli`
  backend, pinned in `mise.toml` — not `aqua:databricks/cli`, not the legacy
  `databricks-cli`/`databricks-sdk` PyPI packages, not a global mise
  selection, no sudo, no shell profile change. `mise install` verified GitHub
  artifact attestation for the downloaded release asset.
- User completed `databricks auth login` (OAuth, browser) against
  `https://dbc-3f70aae3-11d5.cloud.databricks.com` under profile
  `bedoux-databricks`. Token is stored in the OS keyring via
  `~/.databrickscfg` (outside the repo); no credential was requested, read,
  or printed by the agent.
- Bounded read-only checks, all against the live workspace:
  - `databricks auth describe --profile bedoux-databricks` (no `--sensitive`):
    succeeded, host/account/workspace IDs resolved, `auth_type: databricks-cli`,
    secure OS-keyring token storage confirmed.
  - `databricks catalogs list` and `databricks jobs list --limit 5`: both
    succeeded. The workspace already has deployed dev jobs from a prior
    session/CI attempt, including `[dev tsoglog_uli] bedoux_analytics_job`
    with `max_concurrent_runs: 1` as the runbook expects.
  - `databricks bundle validate --target dev --profile bedoux-databricks`:
    **Validation OK.** This validated the checkout's current working tree
    (including this session's uncommitted follow-up changes), not just the
    last commit.
- Remaining blockers: none for read-only access. Deploying, running the job,
  and the healthy → fault → restored → replay demonstration in
  [live-verification.md](live-verification.md) all still need separate,
  explicit authorization per step — this task only covered CLI setup and
  validation. `docs/development.md` now documents the install/profile/verify
  commands for future sessions.

## Credential capability and workspace starting state

Determined 2026-09-21 by read-only API calls under profile
`bedoux-databricks`. Detail and the exact consequences are in
[live-verification.md](live-verification.md) section 1.

- **PATs work.** `tokens list` and the admin `token-management list` both
  succeeded. Two tokens exist: `bedoux-databricks-project` (expires
  2027-07-30) and `CLI Access Token` (created 2026-09-21, expires
  2027-09-21). The user should confirm they recognize both and revoke any
  they do not. No token value was requested, read, or printed.
- **No service principal exists.** `service-principals list` returns an empty
  list; the endpoint answers, but creating one is a write action and was not
  attempted. OAuth M2M is therefore still unproven, and **CI stays on a PAT**
  with no workflow edit needed.
- The user's identity is in the workspace `admins` group, so token creation
  and revocation need no account console.
- **`dev` is not empty.** `[dev tsoglog_uli] bedoux_analytics_job` is deployed
  with `max_concurrent_runs: 1`, but its live task graph is the
  pre-chapter-02 bronze → silver → gold, **without** `bedoux_gate_task`.
  Deploying is what introduces the gate.
- All three `workspace.bedoux_gold.*` tables already exist, last written
  2026-07-30. Good: it makes the withheld stage's retention claim checkable.
  Also means the first-ever-run case cannot be demonstrated here without
  destroying that baseline — leave it as a design argument.

## CI verification (2026-09-21)

Run `35667369376`, `pull_request` event on `b8d630f`:

| Job | Result |
|---|---|
| Unit tests | success |
| Detect bundle changes | success |
| Validate bundle | success — `Validation OK!`, host masked as `***` |
| Deploy bundle | **skipped** |

`deploy` skipped because `push` is scoped to `branches: [main]`, so a chapter
branch only fires `pull_request`. Confirmed by workspace inspection after the
run: the deployed `[dev tsoglog_uli] bedoux_analytics_job` still has the
ungated bronze → silver → gold graph, and
`gold_campaign_performance.updated_at` is still 2026-07-30T20:41Z. CI reached
the workspace to read, and changed nothing.

### Push and re-validation (2026-09-22)

Pushed the four local commits (`26b9d99`, `9d3ca54`, `a80c914`, `8331824`) to
`origin/series/02-quality-gate`. Before this, `origin` and PR #3 still had
the buggy `array_remove(..., None)` code with a stale green CI run from
before the incident was found — reviewed independently and flagged as the
more misleading state to leave live. Pushing was authorized explicitly by
the user this turn; not done unilaterally.

Run `35672003481`, `pull_request` event on `8331824` (head after push):

| Job | Result |
|---|---|
| Detect bundle changes | success |
| Unit tests | success — 98 passed, matching local |
| Validate bundle | success — `databricks bundle validate --target dev` |
| Deploy bundle | **skipped** (PRs never deploy) |

`gh pr view 3`: `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN` (was
`UNSTABLE` before this push). PR #3 now reflects the incident, the fix, and
the live re-run confirmation — it is no longer validating the buggy code.
**Still not merged** — merging remains a separate deployment decision.

## Checks

- `uv run --locked python -m pytest -q`: **98 passed** after the fix (was
  92 before this session's incident/fix work — +6: 5 new conservation-policy
  tests in `test_gate_policy.py`, 1 AST-based `array_remove` regression test
  in `test_quality.py`). **No Spark/DLT runtime** is exercised — these are
  policy/pure-Python/AST-source checks; see the chapter doc's explicit note
  on what this does and doesn't prove, given that's exactly the gap the
  incident came through.
- `uv sync --locked`, `uv lock --check`: passed.
- `git diff --check`: clean, both before committing the fix and now.
- Live, post-fix (this session): `bundle validate`/`bundle plan`/
  `bundle deploy`/`bundle run` all succeeded; deployed source diffed
  byte-for-byte against the checkout; the actual persisted Silver tables and
  Gold digests were queried and cross-checked, not just job status — see
  "Re-run result" above.

## Exact next task

**All prior next-task items are done.** In order: live-verification section 1
closed; healthy baseline found the incident; root-caused and fixed (98 tests,
was 92); fix confirmed live; pushed with PR #3 green; and now **fault (0.30)
→ restore (0.02) → replay (0.02) all confirmed live in one session** — see
"Fault → restore → replay demonstration" above for full evidence (run IDs,
per-task outcomes, complete `gate_status` rows, Silver counts, Gold digests
and `updated_at` for every stage).

### Status: planned / implemented / demonstrated, precisely

- **Demonstrated, live, with ground-truth verification (not just job
  status):** healthy run passes with conserved evidence; a genuinely
  above-threshold *and conserved* rate correctly fails the gate and leaves
  Gold provably untouched (`updated_at` predates the run); restore is
  explicit, verified, and not assumed; replay is a real back-to-back rerun
  with advancing `_computed_ts` and byte-identical business content.
- **Implemented and unit-tested, not live-exercised:** `expect_or_fail`
  firing (never triggered — `_reasons` was never NULL in any of five runs);
  `conserved=false` (never observed in the workspace, only in policy tests
  reproducing the incident's own numbers) — meaning the conservation check's
  *passing* behavior is live-proven, but its own failure path is not.
- **Known, documented, not in scope for this chapter:** whole-Gold
  withholding (not per-table); freshness-based binding (not immutable
  batch/run identity — another writer's newer data could pass); no atomic
  multi-table Gold publication; `clients_clean`/`campaigns_clean`'s
  `_ingest_ts`-tie dedup (separate latent bug, flagged not fixed); a
  first-ever-run failure (untestable here without destroying the real
  baseline). Row conservation catches "the split doesn't add up to the
  input," not every possible correctly-conserved misclassification.

### Recommendation on merging PR #3

**Lean toward merging**, with the caveat that it's your call, not mine to
make. Reasoning: `main` would receive the exact code that has now run
successfully five times in `dev` under direct observation, including the
specific failure mode (silent data loss passing as healthy) that motivated
this whole session — found, root-caused, fixed, and then the fix's own
correctness re-verified under both the healthy and the fault condition.
Merging would deploy this same code path via CI (bundle-path push + working
PAT), which is a real action but not a new one — `dev` already runs it.
Leaving PR #3 open longer doesn't reduce risk; it just delays chapter 03,
which per `AGENTS.md` should start from integrated `main`. Counter-argument,
for balance: this session made real changes to the gate's contract
(`conserved`, `accepted_rows`, `quarantined_rows`), and while `dev` proves
they work, nothing has proven the *deploy-from-main* path specifically
(versus the manual `bundle deploy` this session used) — though that gap is
identical for every prior chapter and isn't specific to this one.

Push/integration and remote retention/local-branch cleanup follow
[branch-workflow.md](branch-workflow.md) within your authorization either
way. Chapter 03 should start from integrated `main` once you've decided.

Use `sentinel-story` only when asked to draft posts. Jev remains optional;
AWS is deferred with no budget or deployment authorization. Earlier AWS reuse
context and preparation history remain available in Git.
