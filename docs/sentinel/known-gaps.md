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

**Still open.** Chapter 03's first session built the redaction/canary half
of its scope (`src/bedoux/evidence.py`) but explicitly did not build this
mechanism — see
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md#does-this-close-the-durable-evidence-gap-from-chapter-02)
for what was and wasn't done and why.

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
