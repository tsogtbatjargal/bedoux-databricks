# Known gaps

A durable, cross-chapter register of gaps found and deliberately deferred,
not fixed. Distinct from a chapter's own "Verification and limits" table:
this file is where a gap goes once it's understood to be structural —
something a future chapter should close, not a one-off bug. Add to it;
don't let a deferred gap live only in a session transcript or a closed
review thread.

## Local tests do not execute Spark

Local tests cover `quality.py`'s pure Python reference logic, notebook/API
stubs (`gate_check.py`, `bronze.py`'s generator wiring), and source-text/AST
assertions against `silver.py` (reason-code constants match, `array_remove`
isn't called, `expect_or_fail` guards are present). **None of that executes
`silver.py`'s actual Spark expressions.** This is the exact boundary the
`array_remove(..., None)` defect escaped through: the local suite was fully
green while every `_flagged` view's `_reasons` was silently NULL on every
row in the live workspace (see
[chapters/02-quality-gate.md](chapters/02-quality-gate.md), "Incident").

Duplicate handling and missing-reference behavior in `silver.py`'s actual
Spark joins/window functions/`when()` chains remain unexecuted locally.
Closing this needs a JVM + `pyspark` available in the dev environment (not
currently a project dependency — see `docs/development.md`) and extracting
`silver.py`'s transformations into functions testable against a local Spark
session, the way `quality.py` already separates pure logic from I/O.

**Narrower than it was, not closed:** the live fault run in chapter 02's
demonstration did cross-validate `quality.py`'s reference rules against
`silver.py`'s actual Spark output by execution — the predicted 336
accepted / 164 quarantined (32.80%) matched the observed rate exactly. That
is real evidence the two are in sync *for that one code path, on that one
run*. It is not a standing local check; a future edit to either file could
silently diverge again with nothing catching it before a live run.

## Durable incident evidence is manual

Quarantine tables (`<source>_quarantine`) are recomputed each run, not an
append-only archive — a run's rejected rows are gone once the next run
recomputes them. `gate_status` is a single current-state table, not a
history. The only durable record of what happened during chapter 02's fault
stage is [chapter-02-evidence.md](chapter-02-evidence.md), assembled by hand
from session transcripts after the fact. There is no mechanism that
captures this automatically at the time it happens.

Building that mechanism — an append-only incident/evidence log, written by
the pipeline itself rather than reconstructed afterward — belongs to
chapter 03 ("Protect what matters"), not this chapter. Chapter 02's gate
decides whether to publish; it was never scoped to also preserve evidence
of what it rejected beyond one run's `_quarantine` tables.

**Built, run live, and negative-tested; a predicted limitation confirmed
in the process.** Chapter 03's first session built the redaction/canary
half of its scope (`src/bedoux/evidence.py`) but explicitly did not build
this mechanism. A later session built it: `src/bedoux/evidence_log.py`
plus a thin writer in `gate_check.py` append at least one row per job run
(a task retry appends more — see below) to
`workspace.bedoux_silver.gate_evidence_log`, pass or fail, created with a
real `delta.appendOnly = true` table property. Deployed at `7856b78`
(`Files: 66 uploaded`). Confirmed live across four job runs (two passing
at the default `bedoux_lead_invalid_rate=0.02`, one failing at a
separately authorized `0.30`, one restore run back at `0.02`): a row is
written on every run, pass or fail, with content matching `gate_status`
from the same run; `SHOW TBLPROPERTIES` shows `delta.appendOnly`
genuinely set on the created table (not just requested in the creation
code); and rows accumulate rather than replace. **The negative test is
now done:** an `UPDATE` and a `DELETE` against two real, existing rows
both failed with `[DELTA_CANNOT_MODIFY_APPEND_ONLY]`, and a full re-read
confirmed every row unchanged. This proves the property rejects those two
specific operations against real data — not that the table is immutable
against every possible operation; `MERGE`, `INSERT OVERWRITE`, `REPLACE
TABLE`, `DROP`, and a property change were out of scope and not attempted.
A `gate_evidence_log` row from a failing run is confirmed too: `leads`
breached at a 32.8% quarantine rate under the fault deploy, `problems`
held its first-ever non-empty value, and the gate correctly withheld Gold.

**A predicted limitation, now empirically confirmed:** the design doc
already named this ("Known limitation, not solved this session" in
`chapters/03-protect-evidence.md`) — a task retry within one job run
would call `gate_check.py` again with the same `run_start_ms` and append
a second row. The failing run's `bedoux_gate_task` retried once at the
job level (both attempts failed), and the evidence-write-then-raise code
ran on *both* attempts, appending **two** rows with identical
`run_start_ms` and content, differing only in `written_ts`. Append-only
guards against mutation, not duplication — the property held exactly as
designed, and a retried failing run still produces a duplicate evidence
row today. Not investigated or fixed here; a candidate for a future
chapter or a dedicated fix, the same way other entries in this file are
held. See
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#append-only-evidence-log-design-this-session)
for the full design, [chapter-03-evidence.md](chapter-03-evidence.md) for
the raw run evidence including the duplicate-row detail, and
[live-verification.md](live-verification.md#6-chapter-03-evidence-log-demonstration-confirmed-live)
for the exact commands used, including the negative test.

## Two conservation-check paths have never fired live

- `@dlt.expect_or_fail("reasons_not_null", "_reasons IS NOT NULL")` has
  never fired in any live run — no run has produced a NULL `_reasons`,
  including the fault run (which produced a real high quarantine rate, not
  a NULL-propagation failure). Its guard is unit-tested and code-reviewed,
  not live-exercised.
- `conserved=false` has never been observed in the workspace. It has only
  been reproduced in policy tests (`tests/test_gate_policy.py`) directly
  against the original incident's numbers. The live fault run proved
  `conserved=true` on a genuinely high rate; it did not, and by design
  could not, prove what happens when conservation itself fails, since
  nothing in the current fixture or fault path breaks conservation.

Both are real, working code paths backed by tests — this is not a claim
they're broken. It's a claim that "tested" and "observed live" are
different levels of evidence, and only the first is currently true for
these two.

## CI credential expiry will look like a bundle defect

The `github-actions-ci` PAT backing `DATABRICKS_TOKEN` in this repo's GitHub
Actions secrets **expires 2026-12-20**. No token value is recorded here or
anywhere in this project — this is a durability note about the expiry date
only.

**When it expires, `Validate bundle`/`Deploy bundle` will fail on
authentication** (`default auth: cannot configure default credentials` or
similar), on a PR or a `main` push that otherwise contains no bundle
problem at all. This is not a hypothetical: the very first time this
project's CI attempted `Validate bundle`, before any CI credential existed,
it failed exactly this way, and diagnosing "is this a real bundle defect or
a missing-credential problem" consumed a full session before `gh secret
list` confirmed the repo had zero secrets configured. A future expiry will
produce the identical symptom on a repo that otherwise has working
credentials — check the token's expiry and the secret's presence *before*
assuming the bundle itself broke.

**For the user, not acted on here:** three PATs currently exist in the
workspace — `github-actions-ci` (in use by CI), `bedoux-databricks-project`
(expires 2027-07-30, appears unused since CI got its own dedicated token),
and `CLI Access Token` (expires 2027-09-21, never specifically accounted
for in this project's records). Whether to revoke either of the unused ones
is the user's decision; this file only records that they exist and when
they expire.

## `evaluate_evidence_gate` prevents the call only against a fake provider

History: for most of chapter 03 this entry was titled "No caller of
`evaluate_evidence_gate` prevents an external call." Its first caller,
`evidence_log.gate_and_redact`, guards a Delta append, which is not the
external call the roadmap's chapter 03 criterion names.

**Closed at code level.** Chapter 04's first increment (PR #18, merge
`b347a1c`) added the model-call site: `src/bedoux/model_call.call_model`
runs the gate and returns before touching its provider when the gate
fails. `test_evaluate_evidence_gate_verdict_alone_stops_the_call` forces
the gate to refuse clean evidence and asserts zero provider calls;
removing the gate line from `call_model` makes exactly that test fail.
The user decided this meets chapter 03's criterion as implemented and
unit-tested, not demonstrated live (see
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#roadmap-acceptance-mapping)).

**Why the entry stays:** the only provider is a test fake. No evidence
has left the process, so this is proven for the local call path's control
flow, not for a real network egress. A live proof needs a real provider,
deliberately deferred (next entry). Nothing in the job calls `model_call`
either.

## The sensitive-value leak check misses short and non-string secrets

`evaluate_evidence_gate`'s sensitive-value check (`_value_leaked` in
`src/bedoux/evidence.py`) only substring-matches string values of at least
8 characters, and skips non-string values entirely (both narrowings were
added to fix a round-2 over-blocking regression — see
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#review-findings-round-2-pre-merge-over-blocking-regression)).
Concretely, this lets a real leak through:

```python
evaluate_evidence_gate({"password": "hunter2", "notes": "pw is hunter2"})
# -> (True, [])
```

A 7-character secret copied verbatim into another field is invisible to
this check. It is not a bug in the sense of behaving other than designed —
the 8-character threshold is deliberate — but the threshold's stated basis
is narrower than the field set it applies to: it was calibrated against
`FICTIONAL_SENSITIVE_LEAD`, which only ever populates `ssn`, `credit_card`,
and `api_key` (all 11+ characters). `SENSITIVE_FIELDS` also names
`password` and `phone_number`, which the fixture never populates and which
are routinely shorter than 8 characters in realistic use (a 6-8 character
password, a 7-10 digit phone number without country code). The threshold is
defensible against what was tested; it was not validated against the full
field set it's meant to cover.

## Freeform sensitive text with no recognized marker is invisible to `evidence.py`

The module can only recognize sensitive content that is either under a
`SENSITIVE_FIELDS` key, carries the literal `CANARY_MARKER`, or is a
meaningful-length copy of a value that appeared under a recognized key
elsewhere in the same packet. Sensitive text typed directly into an
unlabeled field — never duplicated from a labeled one, containing no
canary — is invisible to it. This is inherent to a rule-based/pattern
approach, not a defect any specific fix closes: there is no way to
recognize "this looks like a secret" from content alone without a much
broader detection method (format-specific pattern matching, a classifier,
or similar), none of which this module attempts. `evidence.py` is a
targeted check against a known field/marker set, not general DLP — see
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md) for
where this caveat is also stated in the chapter's own scope.

## `clients_clean`/`campaigns_clean` dedup ties on a constant timestamp

`clients_clean` and `campaigns_clean` (`silver.py`) dedup by a window
ordered on `_ingest_ts`. Since `_ingest_ts` is `current_timestamp()`, it's
constant across every row of a single table computation and ties whenever
the same `client_id`/`campaign_id` appears more than once in one run —
`row_number()` over a tied window is not guaranteed deterministic. This is
the same class of bug `_row_id` was added to fix for `leads`/`web_events`/
`ops_events` in chapter 02, but touching `clients_clean`/`campaigns_clean`
was out of that chapter's stated scope (only "malformed values, duplicate
leads, and missing campaign references" were named), and neither table has
test coverage today to catch a regression if this silently misbehaves.
Flagged, not fixed; a candidate for a future chapter or a dedicated fix.

## Chapter 04's runtime model provider is deliberately not built

This is a portfolio demonstration, not a production incident-response
system, and a live model provider would incur real API spend for no
additional demonstrated capability beyond what a fake provider already
proves. The boundary the provider would sit behind is designed and
unit-tested — `evidence.py`'s redaction/canary gate, and this session's
append-only evidence log (`evidence_log.py`) that gives it its first real
caller — but the provider itself is intentionally absent. That is a scope
decision, made once, in writing, not an oversight discovered later: the
same distinction `claude-implementation.md`'s "First increment" already
draws between building the guarded call path (inject a fake provider, no
network dependency, no waiting on credentials) and the separate, later
increment of wiring in an actual model/provider with real spend.

Covering this gap in the post or video version, rather than building it,
is the plan — spend the demonstration budget on showing the boundary
holds under a fake provider's timeouts and malformed responses, not on
proving a real vendor's API works.
