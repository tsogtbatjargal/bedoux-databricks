# ADR 0005: One definition of "valid", shared by lakehouse and legacy

Status: accepted (Track 3), 2026-10-16

## Context
If the lakehouse and the legacy report define "valid row" differently,
reconciliation fails for reasons that aren't bugs, and people stop trusting the gate.

## Decision
`src/aglc/expectations.py` holds each rule once, as SQL (enforced by DLT
`expect_all_or_drop`) plus a Python predicate with the same meaning (used by the
legacy report and tests). Boundary tests pin the meaning.

## Consequences
- Rule changes happen in one file and show up in review.
- The SQL and the Python can still diverge in edge cases (null handling). Boundary
  tests cover the known ones. A live run is the final check.
