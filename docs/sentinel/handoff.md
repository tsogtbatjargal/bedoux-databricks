# Session handoff

This file records current state and the next task, not permission to merge,
deploy, run jobs, change secrets, bind resources, or publish. Inspect Git
before continuing. Detailed session-by-session history lives in Git log and
`docs/sentinel/chapters/02-quality-gate.md`, not here.

## Current state

- **Chapter 02 is merged and integrated into `main`** (PR #3, merge commit
  `f8ae89d`). **A follow-on external review then found five more issues**
  against the merged code; four are fixed and **merged** (PR #4, merge
  commit `b62bffa`, branch `series/02-quality-gate-fixes` — created from
  `main`, per `branch-workflow.md`'s "make later fixes on a new branch from
  main, treat a published branch as a snapshot"; `series/02-quality-gate`
  itself was not reopened, since PR #3 was already closed/merged). The
  fifth was already fixed by `8c10bbf` before this round — verified
  directly against the file contents, not assumed. **This is now fully
  closed out**: verified with one live run (no deviation from the
  prediction), merged, CI-deployed a second time, and cleaned up.
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
- Working checkout is on `main`, up to date with `origin/main`, 101 tests
  passing. Both `series/02-quality-gate` and `series/02-quality-gate-fixes`
  local branches were deleted after merging (`git branch -d`, all
  `branch-workflow.md` checks passed both times); both remote branches are
  retained.
- **Both merges triggered a CI deployment** to the workspace (PR #3's merge
  was the project's first-ever; PR #4's merge was the second). Both
  verified afterward by querying the workspace directly: same `job_id`/
  `pipeline_id`s both times (no duplicates), job graph still Bronze →
  Silver → gate → Gold, Bronze's config still reads
  `bedoux.lead_invalid_rate: "0.02"`, Gold's three digests unchanged by the
  deploy step itself (a deploy doesn't run anything). The live verification
  run for PR #4's changes (one `bedoux_analytics_job` run before merging,
  not the CI deploy) showed **zero deviation** from the predicted 490
  clean / 10 quarantined, `conserved=true`, matching Gold digests — the
  campaign-reference fix is confirmed behaviorally inert on the current
  seeded data, exactly as expected, while closing a real structural gap.
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
- Chapter-02 demonstration round: `bundle validate`/`bundle plan`/
  `bundle deploy`/`bundle run` all succeeded across five full job runs in
  `dev` (healthy baseline, healthy re-run post-fix, fault, restore, replay)
  — see `chapter-02-evidence.md` for the full per-stage record.
- Review-fix round: deployed source diffed byte-for-byte against the
  checkout; one live run confirmed zero deviation from the prediction
  (`gate_status`, persisted Silver counts, and all three Gold digests
  matched exactly).
- CI: PR #3's merge (project's first-ever deployment) and PR #4's merge
  (second) both succeeded — `Unit tests`, `Validate bundle`, `Deploy
  bundle` all green — and both were verified directly against the
  workspace afterward (no duplicate resources, correct job graph/config,
  Gold unchanged by the deploy step itself).

## Limitations

Structural/deferred gaps (whole-Gold not per-table withholding, freshness
not immutable batch identity, row conservation not catching every possible
misclassification, the `clients_clean`/`campaigns_clean` dedup-tie bug, the
untestable first-run-failure case, `expect_or_fail`/`conserved=false` never
observed live, local tests not executing Spark, manual incident-evidence
capture, and CI's PAT expiring 2026-12-20) are consolidated in
[known-gaps.md](known-gaps.md) — the single home for these now, not
duplicated here.

## Current housekeeping + post draft round (`series/02-post-draft`)

Branch from `main`, three commits, **pushed with a PR open, not merged**:

1. Housekeeping: recorded the `github-actions-ci` PAT's 2026-12-20 expiry
   and what its failure will look like (a CI auth error that reads like a
   bundle defect — the exact confusion an earlier session spent a full
   session on) in `known-gaps.md`; noted the three PATs in the workspace
   for the user's own revocation decision, not acted on; moved the
   `clients_clean`/`campaigns_clean` dedup-tie finding out of the chapter
   doc and into `known-gaps.md` as the single register.
2. Drafted the chapter 02 LinkedIn post as a new "LinkedIn draft" section in
   `chapters/02-quality-gate.md` (mirroring chapter 00's pattern), with a
   "Before posting" checklist. Every claim traces to `chapter-02-evidence.md`
   or the chapter doc's own sections; no invented costs, incidents, quotes,
   or personal stories. **Not published** — no `post/02-quality-gate` tag
   exists, and publishing needs its own separate authorization.
3. `roadmap.md`'s publication column for chapter 02 updated to "Draft only,"
   kept separate from the (unchanged) implementation/integration status.

101 tests still pass; `git diff --check` clean throughout.

## Exact next task

Nothing left outstanding from chapter 02's implementation, demonstration,
external review, or this housekeeping/draft round. Two independent next
steps, not mutually exclusive:

- **Publish the chapter 02 post**, when the user requests it: tag
  `post/02-quality-gate` at the demonstrated commit, add the publication-
  register row in `branch-workflow.md`, post the draft, then record the
  public URL. All of that is a separate authorization from drafting.
- **Start chapter 03** from integrated `main`, per `branch-workflow.md`'s
  chapter lifecycle, once its scope is authorized.

Use `sentinel-story` only when asked to draft/revise posts. Jev remains
optional; AWS is deferred with no budget or deployment authorization.
