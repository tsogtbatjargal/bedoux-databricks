# Chapter roadmap

The user approved a small, incremental series ending in a complete project demo.
Each chapter gets its own branch. Start the next one from `main` after its
predecessor is integrated; do not create all future branches from today's baseline.

| Part | Branch | Working title | Build status | Publication |
| --- | --- | --- | --- | --- |
| 00 | `series/00-introduction` | The challenge | Integrated into `main` | Draft only |
| 01 | `series/01-know-your-platform` | Know your platform | Integrated into `main` | Draft only (`chapters/01-know-your-platform.md`, "LinkedIn draft" section); no tag |
| 02 | `series/02-quality-gate` | Defend before damage spreads | Demonstrated, integrated, and review-closed: fault → restore → replay confirmed live in `dev` (PR #3); a follow-on review's campaign-reference gap and terminology findings fixed and verified with a second live run (PR #4, branch `series/02-quality-gate-fixes`); durable evidence in `chapter-02-evidence.md`, deferred gaps in `known-gaps.md` | Draft only (`chapters/02-quality-gate.md`, "LinkedIn draft" section); no tag |
| 03 | `series/03-protect-evidence` | Protect what matters | Integrated into `main` (PR #6, two pre-merge review rounds; PR #8, branch `series/03-evidence-leak-fix`, a post-merge round fixing `evaluate_evidence_gate`'s own problem strings leaking the secret they were reporting), **acceptance-complete at code level, not demonstrated live**: redaction/canary spec implemented and unit-tested (`evidence.py`) meets "blocked or redacted" and "non-sensitive evidence survives" and documents the inspected boundary. "A failed check prevents the external call" is met as implemented and unit-tested (user's decision): chapter 04's `model_call.call_model` (PR #18, merge `b347a1c`) returns before calling its provider when the gate fails, proven by `test_evaluate_evidence_gate_verdict_alone_stops_the_call`, which fails if the gate line is removed. A live proof needs a real provider, deliberately deferred; no evidence has left the process. Durable-evidence-log half built, deployed, and confirmed live (`evidence_log.py`, append-only `gate_evidence_log`, wired into `bedoux_gate_task`; PR #11, merge `7856b78`, sixth CI deployment; PR #14, merge `028b27e`, seventh CI deployment, a docstring-only fix to `evaluate_evidence_gate` that moved 0 resources). Four `dev` runs (`649621694823474`, `102698121895581` passing; `180753859499836` failing under a separately authorized fault deploy; `793561848702599` restore) confirmed a row per run matching `gate_status`, `delta.appendOnly` genuinely set, append-not-replace, and a failing run's row with its first-ever non-empty `problems`. A negative test then confirmed the property actually rejects `UPDATE`/`DELETE` against real rows (`[DELTA_CANNOT_MODIFY_APPEND_ONLY]`) — see `chapter-03-evidence.md`. A limitation the design doc already predicted was then confirmed live: a retried failing run writes a duplicate evidence row (append-only guards mutation, not duplication) — tracked in `known-gaps.md`, not fixed. See `chapters/03-protect-evidence.md`'s "Roadmap acceptance mapping" | Draft only (`chapters/03-protect-evidence.md`, "LinkedIn draft" section); no tag |
| 04 | `series/04-investigate-recover` | Investigate and recover | In progress: first increment integrated (guarded model-call path, `model_call.py`, fake provider only, 22 tests; PR #18, merge `b347a1c`, eighth CI deployment — `Resources: 0 created, 0 changed, 0 deleted, 8 unchanged`). Later increments not started — see `chapters/04-investigate-recover.md` | Not drafted |
| 05 | `series/05-jev-routing` | Spend intelligence carefully | Planned | Not drafted |
| 06 | `series/06-agent-boundaries` | Establish rules of command | Planned | Not drafted |
| 07 | `series/07-full-demo` | The complete demonstration | Planned | Not drafted |

## 00 — The challenge

Prepare shared agent instructions, skills, handoff, and branch/publication workflow.
Write the launch draft in future tense. Verify local configuration and document
what was not tested. This establishes the series; it does not implement Sentinel.

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
