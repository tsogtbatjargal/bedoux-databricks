# Session handoff

This file records current state and the next task, not permission to merge,
deploy, run jobs, change secrets, bind resources, or publish. Inspect Git
before continuing. Detailed session-by-session history lives in Git log and
`docs/sentinel/chapters/02-quality-gate.md`, not here.

## Current state

- **Chapter 02 is merged and integrated into `main`.** PR #3 merged via a
  merge commit (`f8ae89d`, `series/02-quality-gate` at `8c10bbf` is an
  ancestor of `main`). The remote chapter branch is retained; the local
  branch was deleted (`git branch -d`, all branch-workflow.md checks
  passed: clean tree, remote branch exists, local tip == remote tip,
  ancestor of both local and `origin/main`). Working checkout is now on
  `main`, up to date with `origin/main`, 98 tests passing.
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

- `uv run --locked python -m pytest -q`: **98 passed** (was 92 before this
  chapter's incident/fix; +6 tests: 5 conservation-policy tests, 1 AST-based
  regression test pinning that `silver.py` no longer calls `array_remove`).
  No Spark/DLT runtime is exercised — these are policy/pure-Python/AST-source
  checks. That gap is exactly what let the original defect ship; see the
  chapter doc for what the new tests do and don't close.
- `uv lock --check`, `git diff --check`: clean.
- Live, this chapter: `bundle validate`/`bundle plan`/`bundle deploy`/
  `bundle run` all succeeded across five full job runs in `dev` (healthy
  baseline, healthy re-run post-fix, fault, restore, replay). Deployed
  source diffed byte-for-byte against the checkout after each deploy.
- CI on `main` (post-merge): `Unit tests`, `Validate bundle`, and — for the
  first time ever on this project — `Deploy bundle` all succeeded. Verified
  the deploy's actual effect directly against the workspace: same resource
  IDs (no duplicates), correct job graph, correct Bronze config, Gold
  content unchanged (deploy doesn't run anything).

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

Chapter 02 is merged, integrated, CI-deployed and verified, and locally
tidied up — nothing left outstanding from this chapter's implementation or
demonstration. Two independent next steps, not mutually exclusive:

- **Draft the chapter 02 post** (`sentinel-story`, when asked). Publication
  status is still "Not drafted" in `roadmap.md`, tracked separately from
  implementation — the incident-then-fix arc (a gate that initially passed a
  100% row-loss run, found and closed with a live demonstration) is
  unusually strong, honest material for this series' actual premise.
  Publishing itself (tag, register row, posting) needs its own authorization
  when that's the task.
- **Start chapter 03** from integrated `main` (`git switch -c
  series/03-... main` once the next chapter's scope is authorized), per
  `branch-workflow.md`'s chapter lifecycle.

Neither is more urgent than the other from the repo's perspective — both
are clean starting points now. Recommend deciding based on which serves the
series' momentum better: a post while the fault→restore→replay evidence is
freshest, or continuing the implementation arc into chapter 03's scope
(`docs/sentinel/roadmap.md` — "Protect what matters").

Use `sentinel-story` only when asked to draft posts. Jev remains optional;
AWS is deferred with no budget or deployment authorization.
