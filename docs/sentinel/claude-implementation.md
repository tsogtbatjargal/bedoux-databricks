# Claude implementation brief

**Dated, expiring working brief — not reference documentation.** Prepared
2026-09-22 from local `main` at `25e1784`, before chapters 00–03 were fully
integrated and before this repo's own file layout or `evidence.py` were in
their current state. Treat every path, commit SHA, and assessment below as a
snapshot of that moment, not a live description of the repo. Once chapter 04
actually starts, re-derive its first increment from the current codebase and
`roadmap.md`'s acceptance criteria rather than trusting this file's specifics
— then delete or archive this file; it will have served its purpose. Start
with [handoff.md](handoff.md) and inspect Git for what's actually current.

## Assessment

Track 2 has quality controls and a demonstrated publication gate. Chapter 03
has pure redaction/canary checks but no caller. The next useful increment is
a guarded incident runtime. Existing `sentinel-chapter` and `sentinel-story`
skills already cover implementation/review and writing. Another broad skill
would duplicate instructions without supplying the missing runtime.

The resource graph agrees with the contract: Bronze → Silver → gate → Gold.
The gate is enforced by that job; running Gold directly bypasses it. Do not
describe it as a platform-wide permission boundary.

## Invocation for the first implementation session

Paste this into Claude Code when ready to start the local implementation:

```text
/sentinel-chapter Implement the first local Chapter 04 increment described in
docs/sentinel/claude-implementation.md, section "First increment". Read AGENTS.md
and the current handoff, inspect Git, and follow the retained chapter-branch
workflow. Preserve existing work. Use synthetic fixtures and an injected fake
provider; do not wait for API credentials. Finish this increment, run relevant
checks, and update its evidence and handoff. Do not push, merge, deploy, run
workspace jobs, call paid APIs, or publish. Keep subsequent increments planned
and mark offline evidence explicitly.
```

If this workflow-preparation branch has not been integrated, keep its changes
safe and start the chapter from integrated `main` in a separate worktree. Read
the brief from this checkout; do not silently mix the two branches.

## First increment

Build one locally runnable incident flow, with no network dependency:

1. Define a small provider interface and inject a fake that records requests
   and simulates timeouts or malformed responses. No general agent framework
   or multiple provider implementations are needed for this increment.
2. Build bounded evidence from explicit allowed fields. Apply chapter-03
   controls before transport. Ensure the exact payload sent is the validated,
   redacted payload, including tool results or later-added context. A failed
   gate must result in zero provider invocations.
3. Persist an incident before attempting a provider call. Keep an append-only
   local event record with stable incident/event IDs, safe reason codes,
   evidence references, and pending/blocked/reported status. Fail safely if
   persistence fails. Retries must not create duplicate logical incidents.
4. Validate reports: evidence IDs resolve to supplied evidence; uncertainty
   and proposed recovery are explicit. Unknown references, timeouts, malformed
   responses, and exhausted bounded retries leave a visible pending incident.
   Do not persist raw provider errors or unchecked model text.
5. Allow only bounded read-only tools. Unknown tools and all recovery,
   publication, and export actions are denied by code in this increment.
   A recommendation does not grant permission to execute it.

Suggested homes: a small module under `src/bedoux/`, focused tests under
`tests/`, and `docs/sentinel/chapters/04-investigate-recover.md`. Choose filenames
after inspecting callers; these are suggestions, not existing modules. Read
`docs/contracts-bedoux.md` before pipeline work and affected resource YAML before
resource changes. Keep Track 1 stable.

Existing behavior to address: `evaluate_evidence_gate(fields)` returns a boolean
and problem strings, and internally rebuilds a redacted copy. It does not return
the validated packet. Its sensitive-copy failure string embeds the leaked value
(`src/bedoux/evidence.py`). Never copy those strings verbatim to logs, reports,
exceptions, or another model. Use safe codes, preserve independent checks against
original input, and verify the final serialized outbound content. Known-field
redaction alone is not general DLP.

Acceptance tests should exercise the real caller with the fake transport:

- Healthy evidence reaches the fake once and yields a cited report.
- Sensitive fixtures are redacted; canary and copied-secret cases block with
  zero calls. Secret values do not appear in persisted events or errors.
- A timeout or invalid response leaves a recoverable pending incident.
- Unapproved recovery, invented tools, and fabricated evidence IDs are rejected.
- Restart/retry retains prior events and does not overwrite incident history.

Use `uv sync --locked` and `uv run --locked python -m pytest -q`. Record inputs,
command, environment, results, and remaining boundaries. A local event log does
not close the missing pipeline-written durable-evidence archive. Fake transport
tests prove the local call path, not a live provider, Databricks replay, or IAM.

## Remaining completion sequence

| Increment | Deliverable and exit condition |
| --- | --- |
| 04, provider | Select one provider/model; add a bounded adapter with timeouts, usage recording and retry limits. An authorized synthetic live run validates the actual outbound boundary. |
| 04, tools/recovery | Add bounded quality, contract, runbook and job-status tools; persist evidence before refresh erases it; enforce defined approval in the recovery executor. Demonstrate approved replay, reconciliation and before/after metrics when live work is authorized. |
| 05, Jev | Freeze held-out incidents before tuning. Compare rules only, rules plus reasoning, and rules plus Jev/selective escalation on the same set. |
| 06, adversarial checks | Exercise malicious logs, unauthorized tools/exports, ambiguous cases and outages against the executor. Deterministic severe signals remain non-dismissable. |
| 07, demonstration | Record one reproducible incident end to end; provide the 4–6 minute video, evaluation report, retained branch links and limitations. |

Check each chapter against `roadmap.md`; these increments do not replace its
acceptance criteria. Keep one increment per coding session. Resolve existing
dedup/replay limitations before making replay guarantees.

## Keep Claude context small

- Use one writer. Give a fresh reviewer base/head SHAs, relevant acceptance
  criteria and actual diff, including uncommitted/untracked files. Request
  findings before fixes.
- Start with the short handoff and current roadmap section. Follow detailed
  evidence/history links only when needed. Search with `rg -n`, then read ranges.
- Use the account's available Sonnet tier for routine implementation; reserve a
  stronger model for difficult boundary design or unresolved review findings.
  Select explicitly until routing demonstrates a benefit.
- Use `/context` to inspect overhead and `/mcp` to disable unused connections.
  Save the handoff before `/clear` between unrelated tasks. During one task,
  compact around changed files, decisions, test results and the exact next step.
- Run focused tests while changing behavior and the required full suite at the
  end. Retain failure evidence; avoid repeating passing checks without a reason.
- Measure comparable tasks, including review/fix retries and context/cache
  costs. Smaller model prices alone do not establish fewer tokens or faster
  completion. Subscription savings are not API-dollar savings.

These practices follow [Anthropic's cost guidance](https://code.claude.com/docs/en/costs).
No token/cost saving percentage has been measured for this repository.

## Where Jev fits

The supplied video's useful idea is typed decisions feeding code-controlled
workflows. The video page/transcript could not be retrieved in this session;
this assessment uses the user's summary and the primary sources below.
TypeSafe documents choices, yes/no probabilities, and scores. Typed output does
not guarantee a correct judgment; its official skill makes that distinction.
Keep Claude for implementation and incident narrative reasoning.

There are two separate experiments: selecting a coding model during development,
and routing incidents in Sentinel. Prioritize the latter in chapter 05, where
the project requires a measured comparison. Manual skill/model selection is
sufficient for development now. An automatic proxy or startup installer adds
setup work before a benefit has been established.

For Sentinel, start with known runbook categories plus `unknown`. Only pass
bounded, sanitized evidence. Unknown, low-confidence, invalid, or unavailable
classification escalates or remains pending; it never grants recovery permission
or clears a deterministic failed gate.

Measure severe misses, false alerts, routing accuracy, escalation rate, latency
and total cost, including classifier calls, retries and reasoning calls. Freeze
model versions and input sets. A router saves money only if avoided downstream
cost exceeds its overhead and additional review/rework cost.

OpenRouter currently lists Jev 1.13; direct TypeSafe access is another option.
Account access, API shape and billing need checking for the selected path.
No account is needed for offline work. Before live work, provide the provider
choice, model availability and spend cap; configure credentials locally, never
in chat or tracked files. A Claude subscription alone does not grant runtime
API access. Do not assume a coding-router plugin supports OpenRouter merely
because OpenRouter lists Jev.

Sources checked 2026-09-22:

- [TypeSafe introduction](https://docs.typesafe.ai/introduction)
- [Official TypeSafe skill](https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md)
- [OpenRouter Jev 1.13 listing](https://openrouter.ai/typesafe/jev-1.13/)

The TypeSafe skill is a candidate for a later integration task, not installed
or enabled here. Inspect and pin its revision and dependencies before use.
