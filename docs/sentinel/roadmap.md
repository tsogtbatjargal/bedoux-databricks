# Chapter roadmap

The user approved a small, incremental series ending in a complete project demo.
Each chapter gets its own branch. Start the next one from `main` after its
predecessor is integrated; do not create all future branches from today's baseline.

| Part | Branch | Working title | Build status | Publication |
| --- | --- | --- | --- | --- |
| 00 | `series/00-introduction` | The challenge | Integrated into `main` | Draft only |
| 01 | `series/01-know-your-platform` | Know your platform | Integrated into `main` | Not drafted |
| 02 | `series/02-quality-gate` | Defend before damage spreads | Demonstrated and integrated: fault → restore → replay all confirmed live in `dev` (see chapter doc); PR #3 merged into `main`, first CI deployment verified | Not drafted |
| 03 | `series/03-protect-evidence` | Protect what matters | Planned | Not drafted |
| 04 | `series/04-investigate-recover` | Investigate and recover | Planned | Not drafted |
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
