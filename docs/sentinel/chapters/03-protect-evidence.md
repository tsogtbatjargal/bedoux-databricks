# Part 03 — Protect what matters

Status: **Merged and integrated into `main`, but not complete** (PR #6,
merge commit `569c03d` — the project's fourth CI deployment, verified
directly against the workspace: correct `job_id`, no duplicate resources,
unchanged job graph and Bronze config, all three Gold digests unchanged).
This session wrote the pure-Python redaction/canary spec
(`src/bedoux/evidence.py`) and its tests (`tests/test_evidence.py`), plus
three review rounds: round 1 found and fixed three confirmed defects;
round 2 found and fixed an over-blocking regression round 1's own fix
introduced; round 3 (post-merge) found and fixed the module's own
rejection messages leaking the secret they were reporting on. See "Review
findings, round 1/2/3" below, and "Roadmap acceptance mapping" for exactly
which acceptance criteria this leaves met, documented, or structurally
blocked. As of this session (PR #6/#8), nothing here is wired into the
job, `resources/`, or `databricks.yml`; no outbound model call exists
anywhere in this project — merging shipped an inert module, not a new
capability. **A later session wires `evidence.py` into `bedoux_gate_task`**
for the append-only evidence log — see "Append-only evidence log," below —
which is still not an outbound model call. Distinguish,
throughout this doc: **planned** (design decisions not yet built),
**implemented** (`evidence.py`'s functions, backed by passing unit tests),
and **demonstrated** (none of this — nothing has run against a real model
provider or a real job).

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

## Review findings, round 1 (pre-merge, before PR #6 merged)

A pre-merge review of the first version of `evidence.py` found three
confirmed defects — confirmed by running the reproduction below against the
actual code, not inferred from reading it. Each is pinned by a test that
failed before the fix and passes after.

**Severity, stated plainly so this isn't overstated:** all three were caught
in code nothing calls yet, before it ever merged. That is a materially
different severity from chapter 02's incident, which was a live pipeline run
silently losing 100% of its rows in the workspace. Nothing here ever ran
against real evidence, a real job, or a real model call. The value of this
round is that two of the three are the *same class of mistake* chapter 02
already named, recurring inside the very chapter written to apply that
lesson — which is worth recording precisely because it shows the lesson
didn't fully transfer on the first attempt, not because anything broke in
production.

1. **Redaction was shallow; canary detection was already recursive.**
   `redact_evidence_packet` only inspected a packet's top-level keys.
   `contains_canary` already walked dicts/lists/tuples at any depth. The
   realistic evidence-packet shape is a list of quarantined row dicts under
   a key (`{"source": ..., "rows": [row, ...]}`) — exactly the shape a
   caller would build from `<source>_quarantine`. Reproduced:
   ```python
   p = {"source": "leads_quarantine", "rows": [dict(FICTIONAL_SENSITIVE_LEAD)]}
   p["rows"][0]["notes"] = "clean note, no canary"
   evaluate_evidence_gate(p)   # before: (True, []) with ssn/credit_card/api_key
                                #         still present, two levels down, untouched
   ```
   Fixed by making `redact_evidence_packet` recurse through dicts, lists,
   and tuples the same way `contains_canary` already did. After the fix,
   the same call still returns `(True, [])` — but now correctly, because
   `redact_evidence_packet` actually redacted the nested fields rather than
   never looking at them. **This is chapter 02's first review finding,
   recurring**: a correct control (redaction by known field name) pointed
   at the wrong input scope (top-level only, when the real evidence lives
   nested) — the same shape as the campaign-reference check validating
   against unfiltered Bronze while Gold read the filtered Silver dimension.
2. **`contains_canary` scanned values, not keys.** A canary smuggled into a
   key name rather than a value was reported clean. Reproduced:
   ```python
   evaluate_evidence_gate({"ref_" + CANARY_MARKER: "x"})   # before: (True, [])
   ```
   Fixed: the traversal (`_iter_atoms`) now yields dict keys as well as
   leaf values, at any depth, so both `contains_canary` and the
   sensitive-value check below inspect the same surface. This one is a
   straightforward completeness gap, not a recurrence of a prior finding.
3. **The "sensitive field survived redaction" check validated
   `redact_evidence_packet`'s output against itself.** It looked up each
   `SENSITIVE_FIELDS` key in the packet `redact_evidence_packet` had just
   produced and asserted it equaled `REDACTED` — something that function
   guarantees unconditionally by construction. It could never fire,
   regardless of input. Fixed by making it a real independent check:
   `_collect_sensitive_values` reads the *original*, pre-redaction `fields`
   for every value that appeared under a sensitive key (an independent
   source), and `_value_leaked` scans the redacted *result* for any of
   those values turning up anywhere else — catching a sensitive value
   copied verbatim into an unrelated, non-sensitive field, which field-name
   redaction has no way to know about. **This is chapter 02's original
   incident, recurring in miniature**: a check deriving its verdict from
   the same source as the thing it's checking, rather than from independent
   evidence — the same shape `gate_status`'s row-conservation check was
   added to fix (verify against the persisted tables, not the rate
   computation that might itself be broken).

Nine new tests were added (116 total, from 110) covering all three, plus the
positive case that non-sensitive evidence still survives redaction at
nesting depth. None of the original 110 were weakened to make this pass.

**A further gap noticed, not fixed:** this module can only recognize
sensitive content under a known field name, the literal canary, or a copy
of a recognized field's value — freeform sensitive text with none of those
properties is invisible to it. Moved to
[known-gaps.md](../known-gaps.md#freeform-sensitive-text-with-no-recognized-marker-is-invisible-to-evidencepy)
so the register is the single home for this rather than duplicating it
here.

## Review findings, round 2 (pre-merge, over-blocking regression)

Round 1's fix for finding 3 (the independent sensitive-value check) was
itself defective: it matched too broadly, not too narrowly. Three
reproductions, run against the actual code before changing anything:

```python
evaluate_evidence_gate({"ssn": None, "stage": None})           # -> blocked
evaluate_evidence_gate({"password": "a", "stage": "qualified"}) # -> blocked
evaluate_evidence_gate({"api_key": 9001, "lead_id": 9001})      # -> blocked
```

All three reported a sensitive value "survived redaction" when nothing had
leaked. The first is the one that matters in practice: evidence packets are
built from quarantined rows, and rows are quarantined largely *because* a
field is null — a lead with `ssn=None` and any other null field anywhere in
the same packet blocked the whole thing, every time, for no reason. A gate
that blocks nearly every realistic packet is not a stricter gate; it is a
disabled one, because the first person it inconveniences routes around it.

Root causes and fixes, both in `_collect_sensitive_values`/`_value_leaked`:

- `None == None` and `"" == ""` are trivially true and carry no information
  — a null sensitive field matched any other null field in the same packet.
  Fixed: `_collect_sensitive_values` now skips `None` and `""` outright, since
  there is nothing there to leak.
- A short string (`"a"`) matches almost any text as a substring — `"a" in
  "password"` and `"a" in "qualified"` are both true and both meaningless.
  Fixed: `_value_leaked` only checks string values of at least
  `_MIN_LEAK_MATCH_LENGTH` (chosen as **8**: every fictional sensitive format
  in this project — `ssn`/`credit_card`/`api_key` — is 11+ characters, so 8
  sits comfortably under all of them while ruling out short tokens and
  single-character values). Below that length, a value is indistinguishable
  from ordinary text and is deliberately not checked this way at all, not
  checked more loosely.
- A non-string sensitive value (`api_key: 9001`) matching another field by
  bare equality (`lead_id: 9001`) is common by coincidence — small fixtures
  reuse small integer ranges constantly — and equality alone cannot tell a
  coincidence from a copy. **Decision, stated plainly:** `_value_leaked` now
  only checks string values. Every `SENSITIVE_FIELDS` value in this
  project's actual fixture (`ssn`, `credit_card`, `api_key`,
  `phone_number`, `password`) is string-shaped, so this scoping costs
  nothing against the real fixture; a non-string sensitive value is still
  redacted by field name in `redact_evidence_packet`, just not
  cross-checked here. If a future sensitive field is genuinely numeric,
  this check will not catch a numeric copy of it — a known, accepted limit
  of this design, not an oversight.

**The tradeoff, named explicitly:** over-blocking is the *safer* failure
mode for a gate in isolation — a false block costs an inconvenienced caller,
a false pass costs a leak. But a gate that refuses nearly every realistic
packet does not stay safer in practice: it gets disabled, bypassed, or
ignored the first time it is inconvenient, which is a worse outcome than a
narrower check that only fires on real signal. Round 1's fix optimized
purely for "never miss a leak" and, in doing so, became unusable against
ordinary quarantined-row data. Round 2 narrows the check's *precision*
(what counts as evidence of a leak) without narrowing its *scope* (still
recursive, still independent of the redaction function's own claim about
itself) — the real-leak case (`ssn` copied verbatim into `notes`) and the
canary case both still block, unchanged, after this fix.

Five new tests (121 total, from 116) pin the three false-positive cases plus
regression tests proving the real leak and the canary fixture both still
block. None of the prior 116 were weakened, and the depth fix (round 1,
finding 1) and key-scanning fix (round 1, finding 2) were not touched.

## Review findings, round 3 (post-merge, the gate's own rejection leaked the secret)

Reproduced against merged, deployed code (not pre-merge, unlike rounds 1–2):

```python
evaluate_evidence_gate({"ssn": "000-00-0000", "notes": "SSN on file: 000-00-0000"})
# -> (False, ["a sensitive value survived redaction, found elsewhere in the
#              packet: '000-00-0000'"])
```

The gate correctly blocks this packet — but its own problem string embeds
the raw SSN, verbatim, in the second element of the return value. A caller
that logs `problems`, puts them in an error message, or files them into an
incident report (exactly the surfaces this module exists to protect) hands
the secret to whoever reads that surface. The gate blocks the packet and
then leaks the secret through its own rejection. This was first flagged by
`claude-implementation.md`'s assessment while scoping a future caller, not
found by a fresh line-by-line review — worth noting, since it means the
existing test suite passed with this present the whole time; nothing
asserted on problem-string *content* being safe, only on whether the gate
blocked or allowed.

Every `problems.append` call site in the module was checked, not just this
one. Only one leaked: the sensitive-value message above. The canary
message (`"canary marker present in packet after redaction..."`) was
already safe — it names the condition, never the marker itself.

**Fix:** `_collect_sensitive_values` now returns `(path, value)` pairs
instead of bare values, where `path` is a tuple of keys/indices locating
where the sensitive value was found (e.g. `("rows", 0, "ssn")`). A new
`_format_path` renders that as `"rows[0].ssn"` — structure, not secret. The
sensitive-value problem string now reads `"sensitive value at 'ssn'
survived redaction -- found elsewhere in the packet"`: it identifies which
check failed and which field it fired on, never the value that failed it.
The check itself — what counts as a leak — is unchanged; only what gets
reported changed.

Four new tests assert the *absence* of the literal secret and the literal
canary string in every returned problem string (for the leak case, the
canary fixture, and a nested packet combining both), so a future
reintroduction of interpolation fails a test rather than passing silently
the way this one did. **125 total tests** (121 + 4), none weakened.

**The pattern, stated plainly — this is the chapter's real finding:** this
is the *third* time in one chapter that a control's own reporting or
verification leaked through the same channel it was supposed to protect,
or verified against its own output instead of an independent source:

1. Round 1, finding 1: redaction and canary-detection disagreed about
   *depth* — a control correct in isolation, scoped to the wrong input.
2. Round 1, finding 3: the original sensitive-value check verified
   `redact_evidence_packet`'s output against itself — a check that could
   never fail because it never looked anywhere else.
3. Round 3 (this finding): the check that *does* look elsewhere then
   reported what it found through an unprotected channel — the fix for
   finding 3 fixed the verification but not the reporting.

Three findings, one chapter, all controls-checking-themselves or
controls-leaking-through-their-own-output in slightly different shapes.
Chapter 02 had exactly one incident of this kind (`gate_status` computing
its pass/fail from the same NULL that caused the loss) and one review
finding of the "wrong scope" kind. That a chapter *about* protecting
sensitive evidence produced this pattern three times before a single line
called it in anger is worth more than any one of the three fixes — it
suggests the failure mode itself, not any specific function, is what needs
a standing check (e.g., a lint or test convention that flags interpolated
values in any string a security-relevant function returns) — a suggestion
for a future pass, not built here.

This finding is now fully closed at the code level: `_format_path` reports
structure only, four tests pin the absence of both the secret and the
canary in every problem string, and the underlying check is unchanged.
Nothing about it belongs in `known-gaps.md` as a new entry — what remains
open is the pre-existing fact this doc's "Roadmap acceptance mapping"
section already records: at the time this round was written, no caller of
`evaluate_evidence_gate` existed, so this fix was proven against the
function in isolation, not against a real log/error/report surface. **A
caller exists as of "Append-only evidence log," below** — a durable Delta
write, not the external model call this criterion still requires; the
distinction is stated precisely there, not upgraded here.

## What "blocked or redacted" is proven by, and what remains merely asserted

**Proven, this session:** `tests/test_evidence.py` (24 tests, across three
review rounds, part of the repo's 125-test total) exercises the functions above directly against
`FICTIONAL_SENSITIVE_LEAD` and clean/edge-case fixtures — `mise exec -- uv
run --locked python -m pytest -q`. This proves the functions behave as
described, in isolation, in plain Python — including, after round 2, that
they behave correctly on both genuine leaks and the null/short/coincidental
fields a real quarantined-row packet actually contains.

**Merely asserted, not proven:** everything about what happens once a
payload would actually leave this process *to a model*. As of "Append-only
evidence log," below, `evaluate_evidence_gate` does have a caller
(`evidence_log.gate_and_redact`) — but it guards a Delta table append, not
a model call, so this paragraph's claim stands for the external-call
boundary specifically: no model API has ever been called with any payload
built by this code, real or redacted. Whether a real *model*-call site
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

**This session closed only the redaction half, not that gap.** No
append-only log, no automatic capture mechanism, and no change to how
quarantine tables or `gate_status` persist were built or even designed here.
That gap was still open at the end of this session. It's a plausible next
increment of this same chapter (an evidence packet has to come from
*somewhere* durable to be worth redacting), but scoping and building it was
explicitly deferred, not done, at this point in the chapter's history.

**Built in a later session — see "Append-only evidence log," below.** The
mechanism this section describes as missing now exists: `evidence_log.py`
plus a thin writer in `gate_check.py` append one row per job run to
`workspace.bedoux_silver.gate_evidence_log`, pass or fail. It is not yet
deployed or demonstrated live, so `known-gaps.md`'s entry is updated to say
exactly that rather than closed outright — see that section for the full
design and what remains unverified.

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

## Roadmap acceptance mapping

`roadmap.md`'s stated acceptance for chapter 03: "sensitive fixtures and the
marker are blocked or redacted; useful non-sensitive evidence survives; a
failed check prevents the external call. Document the inspected boundary.
This is not an S3 unauthorized-read detector." Per criterion, stated
honestly rather than marking the chapter complete:

- **"Sensitive fixtures and the marker are blocked or redacted" — met,
  proven by unit tests.** `redact_evidence_packet` strips every
  `SENSITIVE_FIELDS` key at any depth
  (`test_redact_strips_known_sensitive_fields`,
  `test_redact_recurses_into_nested_row_dicts`); `evaluate_evidence_gate`
  blocks `FICTIONAL_SENSITIVE_LEAD`'s canary and a sensitive value copied
  into an unrelated field
  (`test_gate_still_blocks_the_canary_fixture_after_the_over_blocking_fix`,
  `test_gate_still_blocks_a_real_leak_after_the_over_blocking_fix`). Proven
  in isolation, in plain Python — not proven against a real payload leaving
  the process, because none ever has.
- **"Useful non-sensitive evidence survives" — met, proven by unit tests.**
  `test_redact_leaves_non_sensitive_evidence_untouched` and
  `test_redact_preserves_non_sensitive_evidence_at_depth`, plus round 2's
  false-positive fixes specifically restoring this for null/short/
  coincidental-value fields that a real quarantined-row packet actually
  contains.
- **"A failed check prevents the external call" — not met, structurally
  blocked, not merely undemonstrated.** This requires an external call
  *site* that calls `evaluate_evidence_gate` and branches on its result —
  no such *external-call* site exists anywhere in this project, even
  though a durable-write caller now does (see "Append-only evidence log,"
  below). `evaluate_evidence_gate` correctly computes `allowed=False` on a
  bad packet, which is a necessary precondition, but "prevents the call"
  is a claim about a caller's control flow at *that* boundary, and there
  is still no caller with that specific control flow. This is chapter 04's
  job runtime to build, not something addable within chapter 03's own
  pure-Python scope. Durable register entry:
  [known-gaps.md](../known-gaps.md#no-caller-of-evaluate_evidence_gate-prevents-an-external-call).
- **"Document the inspected boundary" — met.** See "What this chapter is
  protecting, and from what," above: one function's input, explicitly not
  network/IAM/S3-layer enforcement.
- **"This is not an S3 unauthorized-read detector" — honored.** Nothing
  built here touches S3, IAM, or network-layer access at all.

**Was deferred by choice at this point in the chapter's history, since
built — see "Append-only evidence log," below.** The append-only
durable-evidence-log mechanism `known-gaps.md` names chapter 03 as owning
is not part of `roadmap.md`'s stated acceptance criteria for this chapter
at all — it's a cross-reference this project chose to make, associating
chapter 02's evidence-capture gap with chapter 03 because both are about
protecting/preserving evidence. Unlike the external-call criterion,
nothing prevented building it within chapter 03's own scope, and a later
session did; that does not change any bullet above, since none of them
were about this mechanism.

**Chapter 03 is not complete.** Two of four roadmap criteria are met and
proven by tests; one criterion is documented; one criterion cannot be met
until chapter 04 exists. Calling this chapter "done" would overstate what
a pure-Python spec with no *external-call* caller can prove — a durable-write
caller existing since does not change that; see "Append-only evidence log,"
below.

## Append-only evidence log (design, this session)

`known-gaps.md`'s "Durable incident evidence is manual" names the gap this
closes: `gate_status` is current-state only and `<source>_quarantine` is
recomputed every run, so a rejected batch's evidence is gone by the next
run — chapter 02's fault-stage record only survives because it was
hand-assembled from a session transcript afterward. This section is the
design; the implementation follows it below.

**Where the write happens.** `src/bedoux/gate_check.py`, immediately after
it calls `quality.evaluate_gate`. Three reasons, not just the obvious one:
it runs exactly once per job run (not per Silver table, not per Gold
table); it already receives `{{job.start_time.timestamp_ms}}` as
`run_start_ms`, making it the only component in this project with real run
identity — Silver's DLT tables full-recompute with no equivalent boundary,
and Gold's dataset functions have no run context at all; and it sits
outside DLT entirely, which is what makes append-only possible in the
first place. Track 2's DLT tables (`gate_status` included) are declarative
full recomputes by design — see `docs/contracts-bedoux.md`'s Silver
section — so an append-only table cannot live there without fighting that
model. `gate_check.py` is already ordinary imperative job code (the same
reason it, not a Gold dataset function, holds the publication check — see
its own module docstring), so an explicit `.write.mode("append")` is a
natural fit, not a workaround.

**Schema.** One row per job run, at `workspace.bedoux_silver.gate_evidence_log`:

| Column | Type | Meaning |
| --- | --- | --- |
| `run_start_ms` | `BIGINT` | The run's declared start (`{{job.start_time.timestamp_ms}}`) — run identity, same freshness boundary `evaluate_gate` already uses. Not a guaranteed-unique batch ID under concurrent execution; same caveat `contracts-bedoux.md` states for `min_computed_ts` elsewhere. |
| `run_start_ts` | `TIMESTAMP` | `run_start_ms` converted to UTC, for human readability only — derived, not independent information. |
| `written_ts` | `TIMESTAMP` | Wall-clock time this row was actually appended (`current_timestamp()` at write time). Distinct from `run_start_ts` on purpose: comparing the two shows how long Bronze+Silver took before the gate ran, and a row whose `written_ts` looks wrong under a healthy `run_start_ts` is itself a signal. |
| `passed` | `BOOLEAN` | The overall verdict from `quality.evaluate_gate` — whether Gold was allowed to proceed. Never recomputed here; copied from the gate's own decision. |
| `problems` | `ARRAY<STRING>` | `quality.evaluate_gate`'s own problem strings verbatim (source-name/count/threshold language only — see `evaluate_gate`'s docstring; it never touches row content). Empty exactly when `passed` is true. |
| `sources` | `ARRAY<STRUCT<source, gate_passed, conserved, total, quarantined, accepted_rows, quarantined_rows, quarantine_rate, computed_ts>>` | The exact `gate_status` rows the gate read this run, kept with the verdict so a reader isn't cross-referencing a table that will itself be recomputed by the next run. |

One row captures the whole run's decision and its inputs together, so
reconstructing "why did run X do what it did" never requires joining
against `gate_status` as it existed at that moment — which, being
current-state, won't exist anymore.

**Enforcement: real, not conventional, but unverified live.** The writer
creates the table with `TBLPROPERTIES ('delta.appendOnly' = 'true')` if it
doesn't already exist, before the first append. That is a genuine Delta
Lake storage-engine property — it rejects `UPDATE`/`DELETE`/`MERGE INTO`
against the table outright, not just a convention this code happens to
follow. That said: **this session has read-only workspace access and did
not deploy or run the job**, so the property has never actually been set
against a live table or tested against a real `UPDATE`/`DELETE` attempt.
"Implemented" here means the `CREATE TABLE ... TBLPROPERTIES` statement is
written and will run the first time this task executes; it does not yet
mean "observed to reject a mutation in this workspace." That gap is closed
by the live demonstration in `live-verification.md`, not by this session.
Until that table property is confirmed live, treat "append-only" as
implemented-but-unverified, not proven.

**Every run, not only failures.** The row is written whether `passed` is
true or false. A log that only captures failures cannot show that the
healthy case was actually healthy — which was chapter 02's whole lesson:
a run can look clean (`gate_passed=true`, low quarantine rate) while the
persisted tables tell a different story, and the only way to catch that
after the fact is to have recorded the healthy-looking run's own evidence,
not just the runs that already raised an alarm.

**What this does and does not close against `evaluate_evidence_gate`.**
The record is run through `evidence.redact_evidence_packet` /
`evidence.evaluate_evidence_gate` before it is written (see "Milestone 2"
in the implementation below) — this is that function's first real caller
anywhere in the project. It is deliberately **not** the roadmap's "a failed
check prevents the external call" criterion: a Delta table append is not
an external call, and chapter 04 still owns building an actual model-call
site. What this session's caller demonstrates is the same control shape —
gate before write, never trust the write path to redact itself — applied
to a durable boundary instead of a network one. `roadmap.md`'s acceptance
mapping above is unchanged by this; it is recorded as its own bullet in
the implementation section below, not folded into that mapping.

## Append-only evidence log (implementation)

Built per the design above. Two layers, same split as `quality.py`/
`evidence.py`: a pure Python half (`src/bedoux/evidence_log.py`, no Spark,
no dlt, no network, fully unit-testable) and a thin Spark writer wired into
`gate_check.py`.

**`evidence_log.build_evidence_record(rows, passed, problems, run_start_ms,
written_ts)`** — pure. Takes exactly what `gate_check.py` already has in
hand right after calling `quality.evaluate_gate`: the collected
`gate_status` rows, the verdict, the problem strings, and the run's
declared start. Fails closed on malformed input: a non-positive or
non-integer `run_start_ms`, or a `written_ts` that is not an aware
`datetime`, raises `ValueError` rather than silently building a row with a
fabricated timestamp — an evidence row with a wrong or missing run
identity is worse than no row, because it would misattribute a decision to
the wrong run. Malformed per-source rows (not a dict, or missing fields)
are not fatal, though: they are still recorded as an entry in `sources`
with whatever fields are present and the rest `None`, since dropping a
malformed row silently would itself lose evidence — the same asymmetry as
`evaluate_evidence_gate` failing closed by blocking rather than guessing.
`passed`/`problems` are always `quality.evaluate_gate`'s own values, copied
verbatim — this function makes no gate decisions of its own.

**`evidence_log.gate_and_redact(record)`** — pure. Runs `record` through
`evaluate_evidence_gate`, then always returns `redact_evidence_packet`'s
output. If the evidence gate itself finds a problem (in practice it should
not: `gate_status`-derived fields carry no `SENSITIVE_FIELDS` names or
canary-shaped text), the returned packet still gets written — with its
`passed` forced to `False` and the evidence gate's own problems appended to
`problems` — rather than the row being silently dropped. Blocking never
means losing the row; it means the row records that the evidence gate
itself objected.

**The Spark writer**, in `gate_check.py`, right after
`quality.evaluate_gate` runs and before the existing pass/fail print+raise
block: builds the record, gates it, `CREATE TABLE IF NOT EXISTS
workspace.bedoux_silver.gate_evidence_log ... TBLPROPERTIES
('delta.appendOnly' = 'true')`, then `spark.createDataFrame([packet],
schema=...).write.mode("append").saveAsTable(...)`. The entire block is
wrapped in one `try`/`except Exception`, printing a warning and continuing
on any failure — this was the deliberate priority decision Milestone 3
asked for: **verdict propagation over the write.** If appending the
evidence row throws, the gate's own `passed`/`raise RuntimeError(...)`
logic immediately below is untouched and still runs exactly as before.
The alternative (letting a logging failure fail the whole task) was
rejected because it would mean an evidence-log bug could withhold a
healthy Gold refresh — turning a logging concern into a publication
outage, which is a worse failure mode than one missing log row that
monitoring can catch separately. The cost of this choice: a broken writer
can run silently for a while with no automatic alarm beyond the printed
warning in the task log. That is accepted, not unnoticed.

Added to `docs/contracts-bedoux.md`: `gate_evidence_log`'s table, grain
(one row per job run), and append-only property, alongside the existing
Silver table descriptions.

**Known limitation, not solved this session:** a task retry within the
same job run (Databricks task retries, not a fresh job run) would call
`gate_check.py` again with the same `run_start_ms` and append a second row
for that run. `run_start_ms` is a freshness boundary, not a dedup key —
the same caveat `evaluate_gate`'s docstring already states about
`min_computed_ts`. This log does not deduplicate by run; it is append-only
in the sense of "never mutates a written row," not "at most one row per
run enforced." Recorded here rather than silently assumed away.

**Live demonstration is separate and not run this session.** See
`live-verification.md` for the exact commands a future authorized session
would run to deploy this, trigger the job, and confirm both the row
content and the `delta.appendOnly` rejection live.

## Post draft — deliberately not written yet

Chapters 00, 01, and 02 have a "## LinkedIn draft" section; this one does
not, and that's a decision, not an oversight. Chapter 03 is explicitly not
acceptance-complete (see above) — a published post implies a finished
chapter the way this one currently doesn't. The chapter's most interesting
material so far — two review rounds finding the chapter's own controls
repeating chapter 02's two core mistakes (a correct control pointed at the
wrong scope; a check verifying its own output instead of an independent
source) — also reads better once a real caller exists to show the fix
actually protecting something, rather than only protecting a fixture
nothing calls. Draft this once chapter 04 gives the chapter a call site, or
once the durable-evidence-log half is built and the chapter's own scope is
genuinely finished — whichever the user decides to close first.
