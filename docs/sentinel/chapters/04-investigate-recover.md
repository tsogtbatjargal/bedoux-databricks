# Part 04 — Investigate and recover

Strategic theme: respond and adapt (see [README.md](../README.md)).

Status: **first increment integrated into `main`** (PR #18, merge
`b347a1c`, the eighth CI deployment: `Resources: 0 created, 0 changed, 0
deleted, 8 unchanged`, `Files: 70 uploaded, 0 deleted`). It builds the
guarded model-call path with an injected fake provider. There is no real
provider, agent, tool set, incident store, or recovery executor yet, and
nothing in `bedoux_analytics_job` calls this code.

## Why this increment first

Chapter 03's last open acceptance criterion was "a failed check prevents
the external call." `evaluate_evidence_gate` existed and was tested, but
the only caller was the evidence-log write — a Delta append, not a call to
a model. A criterion about a caller's control flow can't be met without a
caller. This increment is that caller.

The runtime model provider stays deliberately unbuilt (see
[known-gaps.md](../known-gaps.md#chapter-04s-runtime-model-provider-is-deliberately-not-built)):
a real vendor would add API spend without demonstrating anything a fake
can't — the interesting behavior is what the call site does *around* the
provider.

## The call site: `src/bedoux/model_call.py`

`call_model(fields, provider, *, timeout_s)` does, in order:

1. **Gate.** `evidence.evaluate_evidence_gate(fields)`. If it refuses,
   return `blocked` — the provider is never touched.
2. **Redact and serialize.** `redact_evidence_packet`, then
   `json.dumps(..., sort_keys=True, ensure_ascii=False, default=str)`.
   That string is the payload.
3. **Final check on the exact payload.** Re-run the canary scan and the
   copied-secret check (against the *original* input as the independent
   source) on the serialized string. This catches text that only appears
   at serialization: `default=str` renders non-JSON objects, and an
   object's `str()` can carry content the dict-level gate never saw
   (tested with an object whose `str()` holds the canary). If it fails,
   `blocked`.
4. **Call once.** `provider.complete(payload, timeout_s=...)` — the same
   string that was checked, never rebuilt. No retries: one attempt per
   call.
5. **Classify the result.** Timeout (`ProviderTimeout` or `TimeoutError`)
   → `pending` / `provider_timeout`. Any other exception → `pending` /
   `provider_error`, with the exception text discarded (it could echo the
   payload). A response that isn't a JSON object with non-empty string
   `summary`, `uncertainty`, and `proposed_recovery` → `pending` /
   `malformed_response`. Otherwise `reported`, keeping only those three
   fields.

Outcomes carry fixed reason codes (`canary_present`,
`sensitive_value_leak`, `evidence_gate_failed`, `provider_timeout`,
`provider_error`, `malformed_response`), never `evaluate_evidence_gate`'s
problem strings — those name field paths — and never raw provider output.

Enforcing the timeout itself is the provider's job; a real adapter would
pass `timeout_s` to its HTTP client. This module only decides what a
timeout means for the outcome.

## What the tests prove, and what they don't

`tests/test_model_call.py`, 22 tests (171 repo-wide), all against a fake
provider that records every call:

- A failed gate stops the call before it happens: canary, nested canary,
  and copied-secret evidence all produce `blocked` with **zero** provider
  calls, and no secret appears in the outcome.
- `evaluate_evidence_gate`'s verdict is authoritative on its own: with the
  gate forced to refuse otherwise-clean evidence, the provider isn't
  called. This test matters — the final payload check repeats the gate's
  two current checks, so without it, a call site that skipped the gate
  entirely would still pass every other test. Checked by removing the gate
  line: only this test failed. Removing the final check likewise fails only
  its own test.
- Healthy evidence reaches the provider exactly once, and what it receives
  is exactly the redacted serialization; the caller's input isn't mutated.
- Timeouts, provider exceptions, and nine malformed-response shapes each
  leave `pending` with a fixed code; extra response fields are dropped.

**Not proven:** anything about a real provider, the network, or
Databricks. No evidence has left the process. The provider interface is
exercised only by the fake, so a real SDK's timeout, retry, or logging
behavior is untested — and, as chapter 03 already states, what a provider
does with a payload after it arrives is outside anything this code can
see. The user decided this closes chapter 03's "a failed check prevents
the external call" criterion as **implemented and unit-tested, not
demonstrated live**, on the strength of
`test_evaluate_evidence_gate_verdict_alone_stops_the_call`.

## Chapter 04 acceptance, mapped

| Roadmap criterion | Status |
| --- | --- |
| Reports identify evidence and uncertainty | Partly: `uncertainty` is required. Evidence citations aren't validated yet. |
| Sensitive raw rows do not enter prompts | Implemented for this call site: gate + final payload check, tested with a fake. |
| Recovery requires the defined approval | Not started. `proposed_recovery` is text only; nothing executes it. |
| Replay does not duplicate accepted records | Not started. |
| Model failure leaves a visible pending incident | Partly: failures return `pending`, but nothing persists an incident yet. |
| Before/after business metric | Not started. |
| Offline fixtures separate from live model runs | Holds trivially: there are no live runs. |

Next increments, not authorized yet: persist an incident before the call
(so `pending` survives a restart), validate report evidence citations,
and a bounded read-only tool set with recovery denied by code.
