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
