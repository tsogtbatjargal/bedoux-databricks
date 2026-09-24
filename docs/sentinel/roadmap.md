# Chapter roadmap

The user approved a small, incremental series ending in a complete project demo.
Each chapter gets its own branch. Start the next one from `main` after its
predecessor is integrated; do not create all future branches from today's baseline.
Editorial drafts and publication tracking live in the separate
`bedoux-sentinel-content` workspace; see [repository scope](repository-scope.md).

| Part | Branch | Working title | Build status |
| --- | --- | --- | --- |
| 00 | `series/00-introduction` | Shared development setup | Integrated into `main` |
| 01 | `series/01-know-your-platform` | Know your platform | Integrated into `main` |
| 02 | `series/02-quality-gate` | Defend before damage spreads | Demonstrated, integrated, and review-closed: fault → restore → replay confirmed live in `dev` (PR #3); a follow-on review's campaign-reference gap and terminology findings fixed and verified with a second live run (PR #4, branch `series/02-quality-gate-fixes`); durable evidence in `chapter-02-evidence.md`, deferred gaps in `known-gaps.md` |
| 03 | `series/03-protect-evidence` | Protect what matters | Integrated into `main` (PR #6, two pre-merge review rounds; PR #8, branch `series/03-evidence-leak-fix`, a post-merge round fixing `evaluate_evidence_gate`'s own problem strings leaking the secret they were reporting), **acceptance-complete at code level, not demonstrated live**: redaction/canary spec implemented and unit-tested (`evidence.py`) meets "blocked or redacted" and "non-sensitive evidence survives" and documents the inspected boundary. "A failed check prevents the external call" is met as implemented and unit-tested (user's decision): chapter 04's `model_call.call_model` (PR #18, merge `b347a1c`) returns before calling its provider when the gate fails, proven by `test_evaluate_evidence_gate_verdict_alone_stops_the_call`, which fails if the gate line is removed. A live proof needs a real provider, deliberately deferred; no evidence has left the process. Durable-evidence-log half built, deployed, and confirmed live (`evidence_log.py`, append-only `gate_evidence_log`, wired into `bedoux_gate_task`; PR #11, merge `7856b78`, sixth CI deployment; PR #14, merge `028b27e`, seventh CI deployment, a docstring-only fix to `evaluate_evidence_gate` that moved 0 resources). Four `dev` runs (`649621694823474`, `102698121895581` passing; `180753859499836` failing under a separately authorized fault deploy; `793561848702599` restore) confirmed a row per run matching `gate_status`, `delta.appendOnly` genuinely set, append-not-replace, and a failing run's row with its first-ever non-empty `problems`. A negative test then confirmed the property actually rejects `UPDATE`/`DELETE` against real rows (`[DELTA_CANNOT_MODIFY_APPEND_ONLY]`) — see `chapter-03-evidence.md`. A limitation the design doc already predicted was then confirmed live: a retried failing run writes a duplicate evidence row (append-only guards mutation, not duplication) — tracked in `known-gaps.md`, not fixed. See `chapters/03-protect-evidence.md`'s "Roadmap acceptance mapping" |
| 04 | `series/04-investigate-recover` | Investigate and recover | **Acceptance-complete at code level, not demonstrated live** (the user's decision after PR #23). Five increments integrated, each a fake-provider, offline build: guarded model-call path (PR #18, `b347a1c`); local incident log and `CheckedPayload` (PR #20, `27e20c1`); report citations and the report leak screen (PR #21, `8f9d1f5`); read-only tools with an allowlist, gated tool results, and a 3-call limit (PR #22, `3fa08a9`); recovery approval and duplicate-free replay keyed on `lead_id` (PR #23, `c9b9815`, twelfth CI deployment — `Resources: 0 created, 0 changed, 0 deleted, 8 unchanged`). Five criteria met at code level; offline/live separation holds trivially; the before/after business metric and the live run are deliberately deferred together (both need a real provider, covered in the post/video instead). No real model has been called and nothing has run against the real tables. See "Roadmap acceptance mapping" in `chapters/04-investigate-recover.md` |
| 05 | `series/05-jev-routing` | Spend intelligence carefully | **Acceptance-complete at code level, not demonstrated live** (the user's decision after PR #24, merge `9274317`, thirteenth CI deployment — `Resources: 0 created, 0 changed, 0 deleted, 8 unchanged`). Routing with fake classifier/reasoning models through chapter 04's gated path; frozen held-out set; non-dismissable severe signals in both the flat and the `gate_evidence_log` shape; a scoring harness for all three strategies. The chapter's central result is a measurement, so the harness exists but the result doesn't: the live three-way comparison is deliberately deferred with the other provider work. No real model called; costs are labelled estimates, latency unmeasured. See `chapters/05-spend-intelligence.md` |
| 06 | `series/06-agent-boundaries` | Establish rules of command | **Acceptance-complete at code level, not demonstrated live** (the user's decision after PR #27). Two steps integrated: PR #26 (merge `db3d0e9`, fourteenth CI deployment) — instructions inside evidence can't dismiss an incident, add a tool, approve or trigger a recovery, or clear a failed gate, plus a regex flag that's easy to evade; PR #27 (merge `cb709bb`, fifteenth CI deployment — `Resources: 0 created, 0 changed, 0 deleted, 8 unchanged`) — an audit record of routing decisions and a prohibited-action rule. Honest failure analysis written from fakes. No real model called; nothing touched the real tables. See `chapters/06-rules-of-command.md` |
| 07 | `series/07-full-demo` | The complete demonstration | Integrated at code level, not demonstrated live (PR #29, merge `29aa8c8`; no deployment). The user chose no new live runs. A local end-to-end demonstration of chapter 02's fault case, one command, fakes only (`scripts/full_demo.py`, `tests/test_full_demo.py`), tied to the live evidence already recorded (chapter 02's fault/restore/replay runs, chapter 03's failing evidence row and rejected `UPDATE`/`DELETE`). No real model called. Video recording, final architecture, and an evaluation result are not done. See `chapters/07-full-demo.md` |

## 00 — Shared development setup

Prepare shared agent instructions, technical skills, handoff, and branch workflow.
Verify local configuration and document what was not tested. This establishes the series; it does not implement Sentinel.

## 01 — Know your platform

Map source data, trust boundaries, dataset dependencies, owners, and business
impact. Define three synthetic scenarios and a normal control. Establish the
current baseline before proposing new guarantees.

Acceptance: an architecture/threat map distinguishes existing and planned parts;
the scenario inputs and expected behavior are explicit; capability checks are
recorded as verified, unavailable, or untested. Correct the Track 2 contract's
append-only/full-recompute and streaming/batch contradictions in this chapter.
Record a live baseline when access is authorized and available; otherwise leave
live behavior explicitly unverified and continue the local work.

## 02 — Defend before damage spreads

Add deterministic row-order identity for dedup (not batch/run identity, which
this chapter does not implement), persistent quarantine with reasons, quality
metrics, and a publication gate. Cover malformed values, duplicate leads, and
missing campaign references. Decide whether to reject individual records or
withhold the affected Gold refresh, and document the threshold and business
reason.

Acceptance: account for accepted, quarantined, and duplicate records without
double-counting; a failed gate preserves the previously published data; normal
input passes. Test repeated processing. Do not claim whole-platform transactional
publication unless that guarantee is actually implemented.

## 03 — Protect what matters

Add explicitly fictional sensitive fields to isolated fixtures. Build an evidence
packet that removes sensitive values before a model call. Introduce a recognizable
synthetic canary marker and check whether it reaches an outbound payload.

Acceptance: sensitive fixtures and the marker are blocked or redacted; useful
non-sensitive evidence survives; a failed check prevents the external call.
Document the inspected boundary. This is not an S3 unauthorized-read detector.

## 04 — Investigate and recover

Build a local agent with one runtime model provider and bounded tools for quality
results, contracts, runbooks, and job status. Produce an incident report citing
evidence and proposing a recovery step. Use code to enforce permitted actions
from the first implementation; chapter 06 expands the adversarial evaluation.

Acceptance: reports identify evidence and uncertainty; sensitive raw rows do not
enter prompts; recovery requires the defined approval; replay does not duplicate
accepted records; model failure leaves a visible pending incident. Record the
before/after business metric. Keep offline fixtures separate from live model runs.

## 05 — Spend intelligence carefully

Add optional Jev classification/routing with explicit labels and an unknown path.
Compare rules only, rules plus the reasoning model, and rules plus Jev with
selective escalation on the same held-out incident set. Reserve held-out examples
before tuning thresholds. Keep high-severity deterministic signals non-dismissable.

Acceptance: report severe misses, false alerts, routing quality, escalation rate,
latency, and cost with inputs/model versions. Count classifier overhead and retries.
Report negative results too. A lack of Jev access permits adapter/fixture work,
but does not justify claiming a live comparison.

## 06 — Establish rules of command

Exercise malicious instructions in logs, prohibited exports, unauthorized tool
calls, ambiguous incidents, and provider outages. Document who may approve a
recovery and what the agent can never authorize for itself.

Acceptance: executor-level checks reject prohibited actions regardless of model
output; unknown/timeouts cannot authorize publication or data export; the audit
record explains the decision without storing secrets. Publish an honest failure
analysis with the limits of this test set.

## 07 — The complete demonstration

Run the same incident from a healthy dashboard through detection, redaction,
classification, investigation, approved replay, and reconciliation. Link the
retained chapter branches and exact post snapshots from the series index.

Acceptance: a 4–6 minute video, reproducible scenario instructions, final
architecture, evaluation report, and documented limitations. Label cached model
responses or edited waiting periods. Verify every performance claim against a run.

## Shared scenario and deferred work

Use a fictional campaign batch with malformed/duplicate leads, a missing campaign
reference, an unexpected sensitive field, and an instruction embedded in an ops
message. Inject these separately for diagnosis, then compose them for the finale.
Always include ordinary mistakes and healthy batches so every anomaly is not
automatically treated as an attack.

AWS can follow as a separate chapter: Terraform, scoped S3 access, a decoy outside
normal ingestion, and explicitly enabled CloudTrail object events. Step Functions
and direct S3 ingestion need a verified reason and supported Databricks access.
Identity-based masking needs tests with real restricted identities; simulated
policies must be labeled simulated. No AWS spending is assumed by this plan.
