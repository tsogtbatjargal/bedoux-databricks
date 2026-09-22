# Session handoff

This file records current state and the next task, not permission to merge,
deploy, run jobs, change secrets, bind resources, or publish. Inspect Git
before continuing. Detailed session-by-session history lives in Git log and
`docs/sentinel/chapters/02-quality-gate.md`, not here.

## Current state

- **Chapter 02 is merged and integrated into `main`** (PR #3, merge commit
  `f8ae89d`). **A follow-on external review then found five more issues**
  against the merged code; four are fixed on a new branch
  `series/02-quality-gate-fixes` (created from `main`, per
  `branch-workflow.md`'s "make later fixes on a new branch from main, treat
  a published branch as a snapshot" — `series/02-quality-gate` itself is
  not reopened). The fifth was already fixed by `8c10bbf` before this
  round — verified directly against the file contents, not assumed.
  **Not yet merged; verification run (Milestone 5) and merge are the next
  task**, see below.
  1. **Fixed — campaign-reference gap (real, was latent):**
     `leads_flagged`/`web_events_flagged` checked campaign existence against
     `campaigns_raw` (Bronze), not `campaigns_clean` (the eligible,
     publishable Silver dimension). A campaign `campaigns_clean` itself
     rejects (its own `expect_or_drop`: `client_id IS NOT NULL`, `budget >=
     0`) would still count as "known," so a lead referencing it passed
     Silver, conserved, passed the gate, and vanished from
     `gold_client_funnel`'s inner join with no record — contradicting this
     chapter's own "nothing vanishes without a record" claim. Fixed: both
     views now read `dlt.read("campaigns_clean")`. Latent on the seeded
     generator's data (budget always `uniform(200, 5000)`, `client_id`
     always set) — an adversarial fixture (`quality.eligible_campaign_ids`
     + two new tests) pins it closed without changing the generator.
  2. **Fixed — batch-identity terminology (wording only, no behavior
     change):** `_row_id` was called "batch identity" in `bronze.py`'s
     docstring and two spots in the chapter doc. It restarts at 0 every run
     and resolves duplicate ordering *within* one run's recompute — it is
     not a batch or run identifier, and real batch/run identity is not
     implemented anywhere in this pipeline. Retitled to "row-order
     identity" everywhere the imprecise term appeared (`bronze.py`, the
     chapter doc, `roadmap.md`, chapter 01's doc); left alone everywhere it
     already correctly stated the *absence* of batch identity.
  3. **Captured — durable evidence:** the demonstration's per-stage
     evidence (run IDs, `gate_status` rows, persisted counts, full Gold
     digests, exact commands) only survived in session transcripts; the
     fault-stage quarantine contents are already gone from the live
     workspace (recomputed since). Committed
     [chapter-02-evidence.md](chapter-02-evidence.md), sourced from
     transcripts and prior chapter-doc/handoff records — no jobs re-run to
     produce it. Values never separately captured (the incident run's
     broken Gold digest; persisted-table counts for the fault/restore
     stages specifically) are marked "not captured," not reconstructed.
  4. **Noted, not fixed:** [known-gaps.md](known-gaps.md) is a new durable
     cross-chapter register (linked from this file and
     `docs/sentinel/README.md`) — local tests don't execute Spark (the
     exact boundary the `array_remove` defect escaped through, narrower
     now that the live fault run cross-validated one code path by
     execution, but not closed); incident evidence capture is manual, no
     append-only mechanism exists (belongs to chapter 03); `expect_or_fail`
     and `conserved=false` have still never fired/been observed live.
- Working checkout was on `main`, up to date with `origin/main`, 98 tests
  passing, before this round's branch was created.
- This merge was CI's **first-ever deployment** to the workspace. Watched
  it: `Unit tests` and `Validate bundle` green, `Deploy bundle` ran
  `databricks bundle deploy --target dev` and succeeded; `run_job` correctly
  stayed skipped (manual opt-in only). Verified afterward by querying the
  workspace directly: `bedoux_analytics_job` (same `job_id`, no duplicate),
  all three `bedoux_*_pipeline`s (same `pipeline_id`s, no duplicates), job
  graph still Bronze → Silver → gate → Gold, Bronze's config still reads
  `bedoux.lead_invalid_rate: "0.02"`, and Gold's three digests unchanged —
  deploy doesn't run anything, and it didn't.
- **Chapter 02 is demonstrated**, not just implemented and locally tested.
  A live baseline run found a real defect (`silver.py` built `_reasons` with
  `array_remove(array(...), None)`, which is null-intolerant in Spark on its
  *element* argument — a NULL element nulls the whole array rather than
  stripping NULLs — so every `_flagged` view's `_reasons` was NULL on every
  row, silently emptying the persisted clean/quarantine tables while
  `gate_status` computed a self-consistent but wrong "pass" from that same
  NULL). Fixed with `array_compact` + `expect_or_fail` guards, and — the
  more load-bearing fix — `gate_status` now independently cross-checks row
  conservation (`accepted_rows + quarantined_rows == total`) against the
  *persisted* tables, not just the `_flagged` view the rate comes from. Full
  incident writeup, root cause, and fix are in the chapter doc's "Incident"
  section.
- The fix was then proven live with a full fault → restore → replay
  sequence in one session, in `dev`, all with ground-truth verification
  (direct table queries, not just job status):
  - **Fault** (`bedoux_lead_invalid_rate=0.30`): leads 336 accepted / 164
    quarantined / 32.8% / `gate_passed=false` / **`conserved=true`** — a
    genuinely high, correctly-conserved rate, not another silent-loss defect.
    `bedoux_gate_task` failed, `bedoux_gold_task` skipped, and Gold's three
    digests were confirmed unchanged with `updated_at` predating the run
    entirely — proof, not inference, that Gold was never touched.
  - **Restore** (`0.02`, explicitly redeployed and confirmed, not assumed):
    leads back to 490/10, Gold's digests matched the baseline again with
    `updated_at` advanced — a genuine re-derivation onto identical content.
  - **Replay** (`0.02`, no config change, run again immediately): identical
    `gate_status` and persisted-table counts to Restore, identical Gold
    digests, but `_computed_ts`/`updated_at` both advanced — fresh evidence
    each run, no duplication, a literal back-to-back rerun rather than a
    comparison against an older/different run.
- `dev` is currently deployed at the normal `bedoux_lead_invalid_rate=0.02`.
- Local Databricks CLI access (install method, profile `bedoux-databricks`,
  verification commands) is documented in `docs/development.md`. Credential
  capability (PAT verified working; no service principal exists, creation
  untested) is documented in `docs/sentinel/live-verification.md` — not
  duplicated here.
- Chapters 00/01/02 are all integrated into `main`; all three remote chapter
  branches retained (no local copies — cleaned up after each merge).

## Checks and results

- `uv run --locked python -m pytest -q`: **101 passed** (98 before this
  review-fix round; +3: `eligible_campaign_ids` unit test, adversarial
  lead/web-event tests pinning the campaign-reference fix). No Spark/DLT
  runtime is exercised — see `known-gaps.md`.
- `uv lock --check`, `git diff --check`: clean.
- Prior chapter-02 round: `bundle validate`/`bundle plan`/`bundle deploy`/
  `bundle run` all succeeded across five full job runs in `dev` (healthy
  baseline, healthy re-run post-fix, fault, restore, replay) — see
  `chapter-02-evidence.md` for the full per-stage record.
- CI on `main` (post-merge of PR #3): `Unit tests`, `Validate bundle`, and
  `Deploy bundle` all succeeded — the project's first-ever CI deployment,
  verified directly against the workspace (no duplicate resources, correct
  job graph/config, Gold unchanged).
- This round's verification run (Milestone 5) is the next task, not yet
  done — see below.

## Limitations

Known and documented, not changed by this chapter's demonstration:

- Gold withholding is whole-pipeline, not per-table; successful gate
  approval does not make multi-table Gold publication atomic.
- Freshness (`_computed_ts` vs. job start), not immutable batch/run
  identity — another writer's newer evidence could pass. The supported
  demo assumes one serialized job with no concurrent writers.
- Row conservation catches "the split doesn't add up to the input"; it does
  not catch every possible Spark-logic defect that still conserves row
  counts (e.g. a misclassification that quarantines the right count of rows
  for the wrong reason).
- `clients_clean`/`campaigns_clean` still dedup on a window ordered by the
  tied `_ingest_ts` (same class of bug `_row_id` fixed for the fact tables) —
  flagged, not fixed; out of this chapter's stated scope.
- A first-ever-run gate failure can't be demonstrated in this `dev` target
  without destroying its real baseline; left as a design argument.

**Two gaps live-unexercised even after the full demonstration:**
`expect_or_fail` has never fired (no run has produced a NULL `_reasons`),
and `conserved=false` has never been observed in the workspace — only
reproduced in policy tests against the incident's own numbers. The
conservation check's *passing* behavior is proven live; its own failure
path is not.

## Exact next task

**Milestone 5, immediately:** on `series/02-quality-gate-fixes`, run the
local suite (done, 101 passed), then `bundle validate`/`plan`/`deploy` at
the default `0.02` and run `bedoux_analytics_job` **once**. Prediction: since
no seeded campaign is droppable, the campaign-reference fix is a behavioral
no-op on current data — expect leads 490 clean / 10 quarantined,
`conserved=true`, gate passes, Gold digests matching
`chapter-02-evidence.md`'s reference values exactly. **Any deviation means
the reference-check change altered behavior unexpectedly — investigate
before merging, do not proceed to merge.**

Then: open a new PR from `series/02-quality-gate-fixes` into `main` (PR #3
is closed/merged, so this is a new PR, not a reopen), merge with a **merge
commit** (never squash/rebase), watch the CI deployment on `main`, verify
the workspace afterward (job graph, Bronze config, no duplicate resources),
and clean up the local branch only if every `branch-workflow.md` check
passes.

**After that**, chapter 02 is merged, integrated, review-closed, and
verified for a second time — nothing outstanding. Two independent next
steps, not mutually exclusive:

- **Draft the chapter 02 post** (`sentinel-story`, when asked). Publication
  status is still "Not drafted" in `roadmap.md` — the incident-then-fix arc,
  now including a real external-review round closed the same way, is
  unusually strong, honest material for this series' actual premise.
- **Start chapter 03** from integrated `main`, per `branch-workflow.md`'s
  chapter lifecycle, once its scope is authorized.

Use `sentinel-story` only when asked to draft posts. Jev remains optional;
AWS is deferred with no budget or deployment authorization.
