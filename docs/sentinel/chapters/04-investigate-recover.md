# Part 04 — Investigate and recover

Strategic theme: respond and adapt (see [README.md](../README.md)).

Status: **first increment integrated into `main`** (PR #18, merge
`b347a1c`, the eighth CI deployment: `Resources: 0 created, 0 changed, 0
deleted, 8 unchanged`, `Files: 70 uploaded, 0 deleted`). It builds the
guarded model-call path with an injected fake provider. **Second increment
(local incident log) integrated too** (PR #20, merge `27e20c1`, the ninth
CI deployment: `Resources: 0 created, 0 changed, 0 deleted, 8 unchanged`,
`Files: 72 uploaded, 0 deleted`) — see "Incident log," below. **Third
increment (report citations) integrated** (PR #21, merge `8f9d1f5`, the
tenth CI deployment: `Resources: 0 created, 0 changed, 0 deleted, 8
unchanged`, `Files: 72 uploaded, 0 deleted`) — see "Report citations,"
below. **Fourth increment (read-only tools) integrated** (PR #22, merge
`3fa08a9`, the eleventh CI deployment: `Resources: 0 created, 0 changed,
0 deleted, 8 unchanged`, `Files: 74 uploaded, 0 deleted`) — see
"Read-only tools," below. Per-criterion status is in "Roadmap acceptance
mapping," at the end. There is no real provider or recovery executor, and
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
   `malformed_response`. Since the third increment, the report must also
   carry citations that check out, and must not echo the canary or a
   secret (see "Report citations"). Otherwise `reported`, keeping only
   those four fields.

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

## Incident log: `src/bedoux/incidents.py` (second increment)

`investigate(fields, provider, log)` saves an incident *before* the model
is called, then records the outcome against it:

1. `model_call.prepare_payload(fields)` — the same gate and final payload
   check `call_model` uses (`call_model` is now `prepare_payload` +
   `send_payload`, unchanged in behavior). It returns a `CheckedPayload`,
   which only `prepare_payload` can create, and `send_payload` raises
   `TypeError` on anything else before touching the provider. Without
   that, splitting `call_model` would have made the gate skippable with
   `send_payload(json.dumps(fields), provider)` — and chapter 03's
   criterion was closed on the gate being unavoidable.
2. `log.open_incident(payload)` appends an `opened` event and fsyncs it.
   The stored evidence is the exact checked payload, or nothing when the
   gate blocked — never the raw fields. Plain redaction isn't enough to
   store: it doesn't remove the canary.
3. Only if the payload exists: `send_payload` calls the provider once.
4. `log.record_outcome(...)` appends an `outcome` event with the status
   (`blocked` / `pending` / `reported`) and fixed reason codes. Since the
   third increment it also stores the report, for `reported` outcomes
   only — after its citations and the leak screen have passed. Before
   that, report text wasn't stored at all.

**Storage: a local append-only JSON Lines file.** The chapter's
investigation service is local (`sentinel/README.md`, "Scope"; the
roadmap's "local agent"), so a Delta table would put a Spark and workspace
dependency where the design says there isn't one. JSONL needs only the
standard library, and append-only — a second event instead of an update —
is the same pattern `gate_evidence_log` already uses. SQLite would also
work but adds mutable rows for no benefit here. An incident with no
`outcome` event is pending; a torn last line from a crash mid-write is
skipped on read.

**What the tests prove** (`tests/test_incidents.py`, 19 tests, plus 6 in
`tests/test_model_call.py` for `CheckedPayload`; 196 repo-wide; fake
provider only):

- The incident is on disk and pending when the provider is called, as
  seen by a fresh reader of the file.
- A real subprocess that dies (`os._exit`) inside the provider call leaves
  a pending incident with its evidence, visible on restart.
- If saving the incident fails, the provider is never called. If saving
  the outcome fails, the incident stays pending.
- `investigate` decides exactly like `call_model` for six inputs (healthy,
  redacted-ssn, the canary fixture, nested canary, copied secret, and an
  object whose `str()` carries the canary); blocked inputs never reach
  the provider and are stored with no evidence.
- The log file never contains a raw sensitive value or the canary, even
  when the provider's error message or report text contains the canary.
- `send_payload` refuses a raw string — even one byte-for-byte equal to a
  prepared payload — plus an empty string, a dict, and `None`, with zero
  provider calls; a `CheckedPayload` can't be built outside
  `prepare_payload` or modified.
- Checked by mutation: storing plain-redacted evidence or raw fields
  fails the leak tests; saving after the call fails the three ordering
  tests; removing `send_payload`'s type check, or replacing it with duck
  typing that accepts a string, fails all five refusal cases.
- Not a security boundary against code in the same process: the
  creation token is module-private by convention, which Python can't
  enforce. It stops mistakes, not deliberate circumvention.

**Not proven:**
- Real-world durability. `fsync` is called, but no test can show the OS
  and disk honor it through a power loss; the subprocess test proves
  survival of a process death, not a machine crash.
- One writer at a time is assumed. Concurrent appends from several
  processes aren't locked or tested.
- Retries: a retried investigation opens a new incident. Nothing links or
  deduplicates them yet.
- Anything live: no real provider, and nothing in the job writes here.

## Report citations (third increment)

A report is only `reported` if it points at evidence the provider was
actually sent.

**Format.** A required `citations` field: a non-empty list of path
strings in the format `evidence.py` already uses for its problem
strings — `source`, `quarantine_rate`, `rows[0].stage`, or a container
like `rows[0]`. Each one is resolved against the JSON of the payload the
provider received (`CheckedPayload.text`), not the original fields.

**Outcomes** (all `pending`, never `reported`):
- `no_citations`: the field is missing, `null`, or an empty list.
- `malformed_response`: it isn't a list of non-empty strings.
- `unresolved_citation`: any citation names a key, index, or step that
  doesn't exist in the payload — for example `rows[5].stage`, or
  `rows.stage` on a list. One bad citation refuses the whole report.
- `redacted_citation`: any citation lands on the `[REDACTED]` marker, or
  on a container (`secrets`, `rows[0]`) whose values are all redacted.
- `report_leak`: the report text contains the canary or a sensitive value
  from the original fields (the same two checks as the final payload
  check).

**Redacted citations refuse the report, not just the citation.** The
provider never saw a redacted value, so a claim that rests on it has no
basis in the evidence. Dropping the citation quietly would leave that
claim standing with its basis hidden. The cost: a report can't cite a
redacted field even to say "this was withheld" — it has to say that in
`uncertainty` instead. Citing a container is allowed only if it holds at
least one value other than the marker: `rows[0]` with a redacted `ssn`
beside a visible `stage` is fine, but a `secrets` object holding only a
redacted `ssn` and `password` gave the provider nothing, so it's refused.
An empty container is refused by the same rule.

**Leaks are refused before they reach anyone.** `send_payload` screens
the report itself, before returning it. `prepare_payload` already has the
original fields, so it stores their sensitive values in a private slot of
the `CheckedPayload` — in memory only, never in its `text`, its `repr`, or
anything written to disk. Every caller of `send_payload`, including
`call_model` and `investigate`, therefore gets the same screening; neither
an in-process caller nor the log can receive a report carrying the canary
or a secret. Only a `reported` outcome's report is stored.

**What the tests prove** (28 new; 224 repo-wide; fake provider only):
- Citations that resolve — leaf values and a container — are reported
  and kept.
- Missing, empty, or `null` citations → `no_citations`; badly typed ones
  → `malformed_response`.
- Seven kinds of citation that don't resolve in the payload are refused
  as `unresolved_citation`, even though the provider was called and
  answered.
- Citations are checked against what was sent: `ssn` exists in both the
  fields and the payload, but citing it is refused because the payload
  holds the redaction marker.
- Citing a container whose values are all redacted (`secrets`, `rows[0]`,
  `rows`) is refused; citing one with a visible value is still reported.
- `prepare_payload` + `send_payload`, without `call_model`, returns
  `pending` / `report_leak` for a report echoing the canary and an API
  key. `repr` and `text` of a `CheckedPayload` hold no sensitive value.
- A report echoing the canary or a copied secret is refused, never
  returned, and never stored; a report with a bad citation isn't stored
  either; a report that passes is stored with its citations.
- Checked by mutation: removing the citation check fails 9 tests (all
  seven unresolved cases, the redacted case, and the incident-log case);
  allowing redacted citations fails the redacted test. Removing the
  screen from `send_payload` fails 5 tests (the direct `send_payload`
  test, both `call_model` echo cases, and both log-leak tests); refusing
  only redacted leaves again fails the three all-redacted container
  cases; putting the sensitive values in `repr` fails the `repr` test.

**What citation checking does not prove:** that the cited evidence
supports the claim. It checks that each citation *exists* in what was
sent and isn't redacted — nothing more. A report can cite `source` and
then say anything. It doesn't check that the summary is true, that the
uncertainty is honest, that the most relevant evidence was cited, or
that a proposed recovery is safe. Judging support needs a reader — a
person, or a later evaluation step — not a path lookup. Other limits: key
names containing `.`, `[`, or `]` can't be cited; a real value that
happens to be the string `[REDACTED]` is treated as redacted.

## Read-only tools (fourth increment)

`tools.investigate_with_tools(fields, provider, log, fixtures)` lets the
provider ask for a tool instead of reporting. It's `investigate` with a
bounded loop; `call_model` and `investigate` still offer no tools, and a
tool request sent to them is just a `malformed_response`.

**The tools** read local synthetic fixtures that the caller passes in
(a dict), never the workspace:

- `read_gate_status(source)`: that source's `gate_status` rows.
- `read_quarantine_sample(source, limit=5)`: up to 5 quarantined rows
  (`limit` must be 1–5; anything else is refused as
  `invalid_tool_args` and the tool doesn't run).
- `read_evidence_log(source)`: that source's `gate_evidence_log` rows.

A model asks with `{"tool_request": {"tool": "...", "args": {...}}}`.

**The allowlist decides, in code.** `ALLOWED_TOOLS` is a fixed
`frozenset` of those three names. `execute_tool_request` checks it before
anything else, and a name that isn't in it exactly is refused with
`tool_not_allowed` and never executed. That covers restore, replay,
deploy, write, and delete requests, and also near-misses like
`READ_GATE_STATUS` or a trailing space. The model-supplied name is only
compared against the set, never looked up with `getattr` or `globals`,
and nothing in a response can add to it. Arguments are checked against
each tool's fixed signature (`invalid_tool_args`). A refused request is
still recorded in the incident log as evidence, and the model is told it
was refused. There is no recovery tool at all; "recovery refused in code"
means any request for one hits the allowlist.

**Tool results are gated like the first payload.** A result is new
evidence going to the model, so the next payload — the original evidence
plus every tool result so far — goes through `prepare_payload` again:
redaction, the gate, and the final serialized check. A sensitive field in
a quarantined row (`ssn`) is redacted and sent. A result carrying the
canary or a copied secret is blocked, not sent: the investigation stops
as `pending` with `tool_result_blocked` plus the gate's code. A tool
request echoing a secret is refused by `send_payload` as
`tool_request_leak` before it's recorded.

**The loop is bounded.** At most `MAX_TOOL_CALLS = 3` tool calls per
investigation, refused ones included. A fourth request is recorded as
`not_run` and the incident ends `pending` with `tool_limit_reached`.

**What's recorded.** Each tool call is a `tool_call` event in the
incident log. It holds the screened request, a status (`ran`, `refused`,
`failed`, `blocked`, `not_run`), fixed reason codes, and — only if the
result passed the gate — the checked payload that carried it. The log
never holds a raw result or the raw fields.

**What the tests prove** (`tests/test_tools.py`, 25 tests; 249 repo-wide;
fake provider and fake tools only):
- An allowed tool runs once with the requested arguments. Its result
  reaches the model inside the checked payload, the log stores that exact
  payload, and a report citing the result is `reported`.
- Eight names off the allowlist — five recovery-style tools plus three
  near-misses — are refused and never executed, even though a recording
  implementation with that name is present. The request is logged.
- Bad arguments are refused without executing the tool, including a
  sample `limit` of -1, 0, 6, or 50. A `limit` of -1 once got through:
  the cap was `rows[:min(limit, 5)]`, so -1 sliced `rows[:-1]` and
  returned every row but the last (39 of 40).
- A tool result carrying the canary, or a secret copied into another
  field, is blocked. The provider is called once, never with the result,
  and neither value reaches the log. A sensitive field in a result is
  redacted, not stored raw.
- Ten tool requests stop after three executions and four provider calls.
  Refused requests count toward the limit.
- Checked by mutation: dropping `read_gate_status` from the allowlist
  fails the allowed-tool test (and the limit test, which uses it).
  Removing the allowlist check fails all eight refusal cases. Sending tool
  results redacted but not gated fails both blocked-result cases.
  Removing the limit fails both limit tests. Going back to `min()`
  without the range check fails all four out-of-range `limit` cases.

**What this doesn't prove:**
- **No real model has ever chosen a tool.** Every tool request in these
  tests is scripted, so nothing here shows a model would ask for the
  right tool, respect a refusal, or produce a sensible investigation.
- The tools read in-memory fixtures shaped like `gate_status`,
  quarantine, and `gate_evidence_log` rows. They have never read the
  workspace, so nothing here shows the real tables' contents, sizes, or
  permissions.
- Read-only holds because the three functions only filter a dict. It is
  not enforced by a database permission; a real tool reading Delta would
  need a read-only identity for that.
- The allowlist is a same-process check. Like `CheckedPayload`, it stops
  mistakes and model requests, not hostile code in the process.
- A tool call is recorded after it runs, so a process death during a
  tool leaves the incident pending with no record of that call.
- Prompt injection through tool results (instructions hidden in a row)
  isn't tested; chapter 06 covers adversarial evaluation.

## Roadmap acceptance mapping

`roadmap.md`'s stated acceptance for chapter 04: "reports identify evidence
and uncertainty; sensitive raw rows do not enter prompts; recovery requires
the defined approval; replay does not duplicate accepted records; model
failure leaves a visible pending incident. Record the before/after business
metric. Keep offline fixtures separate from live model runs." Per
criterion, using four states: **met at code level** (with the test that
proves it), **met live**, **not built**, or **deliberately deferred**. No
criterion is met live, because no real model has ever been called. This
section lays the chapter out; it doesn't decide what closes it.

| Roadmap criterion | State | Proof or gap |
| --- | --- | --- |
| Reports identify evidence and uncertainty | Met at code level | `test_citations_that_resolve_in_the_sent_payload_are_reported`, `test_a_citation_that_does_not_resolve_in_the_payload_is_refused`, `test_citations_resolve_against_what_was_sent_not_the_original_fields`; a missing or blank `uncertainty` is refused in `test_malformed_response_is_pending`. Proves citations exist in what was sent, not that they support the claim. |
| Sensitive raw rows do not enter prompts | Met at code level | `test_canary_blocks_with_zero_provider_calls`, `test_copied_secret_blocks_with_zero_provider_calls`, `test_final_serialized_check_catches_what_the_dict_gate_cannot`, `test_sent_payload_is_exactly_the_redacted_serialization`; for tool results, `test_a_tool_result_carrying_the_canary_or_a_secret_is_blocked_not_sent` and `test_a_tool_result_with_a_sensitive_field_is_redacted_not_raw`. Bounded by `evidence.py`'s own limits: a sensitive value under an unrecognized key name, in freeform text, or too short or non-string, isn't caught (see [known-gaps.md](../known-gaps.md#freeform-sensitive-text-with-no-recognized-marker-is-invisible-to-evidencepy)). |
| Recovery requires the defined approval | Not built | No approval path exists, and "the defined approval" isn't defined yet. What *is* met at code level is the stronger precondition: nothing can execute a recovery at all. `proposed_recovery` is text only, and every non-allowlisted tool request is refused without running (`test_a_tool_off_the_allowlist_is_refused_and_never_executed`). |
| Replay does not duplicate accepted records | Not built | Nothing deduplicates. A retried investigation opens a new incident, and chapter 03's evidence log already writes a duplicate row on a task retry ([known-gaps.md](../known-gaps.md#durable-incident-evidence-is-manual)). |
| Model failure leaves a visible pending incident | Met at code level | `test_process_death_during_the_call_leaves_a_pending_incident` (a real subprocess dies mid-call), `test_outcome_is_recorded_against_the_incident` (timeout, provider error, malformed response), `test_restart_keeps_earlier_incidents`; bounded tool loops end `pending` too (`test_the_call_limit_stops_the_loop`). Process death only, not a machine crash. |
| Record the before/after business metric | Not built | No metric is chosen or measured. |
| Keep offline fixtures separate from live model runs | Holds trivially | Everything is offline: a fake provider and in-memory synthetic fixtures. There is no live run to keep separate yet, so this says nothing about how the separation would be done. |

The roadmap's scope sentence adds two things that aren't acceptance
criteria but bear on them. "One runtime model provider" is
**deliberately deferred** ([known-gaps.md](../known-gaps.md#chapter-04s-runtime-model-provider-is-deliberately-not-built)).
"Bounded tools for quality results, contracts, runbooks, and job status"
is **partly built**: three tools cover quality results (`gate_status`,
quarantine samples, the evidence log). None covers contracts, runbooks,
or job status.

**Where the handoff's open items fall:**

| Open item | State | Criteria it affects |
| --- | --- | --- |
| Live run | Deliberately deferred: it needs a real provider, and the user chose not to build one. | It would move the three code-level criteria (evidence and uncertainty, sensitive rows, pending incident) toward met live, and make the offline/live separation meaningful. No criterion requires it by wording. |
| Real-table reads | Not built. Tools read in-memory fixtures; real reads would need a read-only identity and a workspace call. | None directly. It's scope ("bounded tools"), and it would strengthen the sensitive-rows criterion by testing real row shapes. |
| Recovery approval path | Not built. | Recovery requires the defined approval. |
| Replay without duplicates | Not built. | Replay does not duplicate accepted records. |
| Before/after business metric | Not built. | Record the before/after business metric. |

**The decision left to the user:** three criteria are met at code level,
one holds trivially, and three aren't built: recovery approval, replay,
and the business metric. Whether chapter 04 closes at code level the way
chapter 03 did, needs some of the unbuilt items first, or waits for a
live run is not decided here.
