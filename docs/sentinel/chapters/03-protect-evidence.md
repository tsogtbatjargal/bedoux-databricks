# Part 03 — Protect what matters

Status: **Scoped and partially implemented, not merged.** This session wrote
the pure-Python redaction/canary spec (`src/bedoux/evidence.py`) and its
tests (`tests/test_evidence.py`), on branch `series/03-protect-evidence`, and
this doc. Nothing here has been wired into the job, `resources/`, or
`databricks.yml`; no outbound model call exists anywhere in this project yet.
Distinguish, throughout this doc: **planned** (design decisions below not yet
built), **implemented** (`evidence.py`'s functions, backed by passing unit
tests), and **demonstrated** (none of this — nothing has run against a real
model provider or a real job).

## What this chapter is protecting, and from what

Chapter 02 closed a gap in *whether* the pipeline publishes bad data.
Chapter 03 is about a different boundary: *what leaves the process* once an
agent (chapter 04's job runtime, not built yet) starts building evidence
packets from pipeline data to hand to a model. The roadmap's acceptance
criteria for this chapter: explicitly fictional sensitive fields in isolated
fixtures, an evidence packet that strips sensitive values before any model
call, a recognizable synthetic canary marker with a check for whether it
reaches an outbound payload, and a plain statement of what's inspected.

**The inspected boundary is one function's input**: whatever dict a future
caller assembles to send to a model. That's it. This is explicitly **not** an
S3 unauthorized-read detector (the roadmap says so directly), not a
network-layer DLP control, not IAM enforcement, and not a guarantee about
what a model provider's SDK does with a payload after it leaves this
process — logging, caching, or retries on the provider's side are outside
what any of this can see or prove.

## What exists: the redaction/canary spec

`src/bedoux/evidence.py`, same pattern as `quality.py` — pure Python, no
Spark, no `dlt`, no network, unit-testable directly.

- **`FICTIONAL_SENSITIVE_LEAD`**: an isolated fixture, not wired into
  `generator.py`, `silver.py`, or any real pipeline table. It exists only so
  the functions below have something realistic-shaped to prove they actually
  strip/detect, instead of asserting that in the abstract. Its sensitive
  fields (`ssn`, `credit_card`, `api_key`) are fictional formats — not real
  SSNs or card numbers — and never generated or read anywhere else in this
  project.
- **`CANARY_MARKER`**: a fixed, greppable string
  (`SENTINEL-CANARY-7f3a9c2e`), planted inside the fixture's `notes` field —
  deliberately *not* one of the known sensitive field names.
- **`redact_evidence_packet(fields)`**: replaces every key in
  `SENSITIVE_FIELDS` (`ssn`, `credit_card`, `api_key`, `phone_number`,
  `password`) with a fixed `[REDACTED]` marker. Non-sensitive fields
  (`lead_id`, `campaign_id`, `stage`, ...) pass through unchanged — the
  "useful non-sensitive evidence survives" half of the acceptance criteria.
- **`contains_canary(payload)`**: recursively scans a payload (through
  dicts/lists/tuples, substring match on strings) for `CANARY_MARKER`,
  independent of which field it's hiding in.
- **`evaluate_evidence_gate(fields)`**: the fail-closed check. Redacts known
  sensitive fields, then scans the *result* for the canary regardless of
  field name. Returns `(allowed, problems)`, mirroring `quality.evaluate_gate`'s
  shape — an empty `problems` list is the only way `allowed` is `True`.

### The point the fixture is built to make

`redact_evidence_packet` alone does **not** catch the canary in
`FICTIONAL_SENSITIVE_LEAD`, because the canary lives in `notes`, a field name
that reads as ordinary evidence, not as sensitive. A test
(`test_redact_by_field_name_alone_misses_the_canary`) pins this down
explicitly rather than leaving it implicit. Field-name redaction is
necessary but not sufficient. `evaluate_evidence_gate` is what actually
blocks this fixture — not by knowing `notes` is sensitive, but by scanning
the redacted result for the canary regardless of where it is. That's the
mechanism this chapter is actually testing: not "did we redact the fields we
already knew about," but "would something we didn't anticipate still get
through."

## What "blocked or redacted" is proven by, and what remains merely asserted

**Proven, this session:** `tests/test_evidence.py` (9 tests) exercises the
functions above directly against `FICTIONAL_SENSITIVE_LEAD` and clean
fixtures — `mise exec -- uv run --locked python -m pytest -q`, 110 passed
(101 before this chapter + 9 new). This proves the functions behave as
described, in isolation, in plain Python.

**Merely asserted, not proven:** everything about what happens once a
payload would actually leave this process. No caller of
`evaluate_evidence_gate` exists. No model API has ever been called with any
payload built by this code, real or redacted. Whether a real call site
correctly calls the gate *before* sending (rather than after, or not at all)
is a future implementation detail with its own failure mode — a gate that
exists but isn't called protects nothing, the same lesson chapter 02 learned
about a check with the wrong scope rather than no check at all. None of that
is exercised here.

## Does this close the durable-evidence gap from chapter 02?

[known-gaps.md](../known-gaps.md#durable-incident-evidence-is-manual) names
chapter 03 as the owner of an append-only incident/evidence log — quarantine
tables are recomputed each run, not archived, and the only durable record of
chapter 02's fault stage is a hand-assembled file
(`chapter-02-evidence.md`), not something the pipeline writes itself.

**This session closes only the redaction half, not that gap.** No
append-only log, no automatic capture mechanism, and no change to how
quarantine tables or `gate_status` persist were built or even designed here.
That gap is still open. It's a plausible next increment of this same chapter
(an evidence packet has to come from *somewhere* durable to be worth
redacting), but scoping and building it is explicitly deferred, not done —
`known-gaps.md`'s entry stays as-is until it is.

## Deliberately left unbuilt this session

- No wiring into `bedoux_analytics_job` or any job task.
- No changes to `resources/` or `databricks.yml`.
- No outbound model call, anywhere, with any payload — real or fictional.
- No append-only durable-evidence-log mechanism (see above).
- No integration with the real pipeline's actual sensitive-adjacent fields
  (there currently are none in `generator.py`'s schema beyond
  `email_domain`, which is not itself sensitive) — `FICTIONAL_SENSITIVE_LEAD`
  is deliberately isolated from that schema, not a variant of it.

If a future session needs one of these, it belongs in a design step written
down first, the same way this chapter's own AGENTS.md-governed scope was
written down before code.
