"""Pure evidence-packet redaction and canary-detection logic for chapter 03
("Protect what matters") -- spark/dlt/network-free, unit testable in plain
pytest, same pattern as quality.py. This is deliberately the redaction/canary
half only: no outbound model call exists anywhere in this project yet (that
is chapter 04's job runtime), so nothing here has been exercised against a
real provider. See docs/sentinel/chapters/03-protect-evidence.md for what
that means for "proven" vs "merely asserted."

FICTIONAL_SENSITIVE_LEAD is an isolated fixture, not wired into
generator.py/silver.py/the real pipeline schema. Its purpose is narrow: give
redact_evidence_packet() and contains_canary() something realistic-shaped to
prove they actually strip/detect, rather than asserting it in the abstract.
"""

CANARY_MARKER = "SENTINEL-CANARY-7f3a9c2e"

# Field names treated as sensitive by name alone. Fictional formats -- none of
# these are real SSNs, card numbers, or API keys, and none are ever generated
# by generator.py or read by any Track 2 pipeline table.
SENSITIVE_FIELDS = {"ssn", "credit_card", "api_key", "phone_number", "password"}

REDACTED = "[REDACTED]"

# The canary lives inside "notes" -- a field name that reads as ordinary
# evidence, not as sensitive. This is deliberate: it demonstrates that
# redacting by known field name alone (SENSITIVE_FIELDS) is necessary but not
# sufficient. A packet-wide canary scan (contains_canary, below) is what
# actually catches this one; field-name redaction does not.
FICTIONAL_SENSITIVE_LEAD = {
    "lead_id": 9001,
    "campaign_id": 7,
    "stage": "qualified",
    "ssn": "000-00-0000",
    "credit_card": "4111-1111-1111-1111",
    "api_key": "sk_fake_0000000000000000",
    "notes": f"Follow-up call logged. Internal ref: {CANARY_MARKER}",
}


def redact_evidence_packet(fields):
    """Return a copy of `fields` with every value under a key in
    SENSITIVE_FIELDS replaced by REDACTED, recursing through nested dicts,
    lists, and tuples -- the same traversal contains_canary() already does.
    The realistic evidence-packet shape is a list of quarantined row dicts
    under a key (`{"source": ..., "rows": [row, row, ...]}`), so a sensitive
    field one level down must be redacted exactly as if it were top-level;
    a shallow, top-level-only version of this function previously left
    nested sensitive fields untouched while contains_canary was already
    recursive, so the two halves of the gate disagreed about depth and a
    nested field was neither redacted nor blocked.

    A key's own name that happens to carry the canary marker (see
    FICTIONAL_SENSITIVE_LEAD's "notes") is passed through unchanged --
    field-name redaction alone cannot know that. Proving the canary doesn't
    survive end to end is contains_canary()'s job, not this function's;
    evaluate_evidence_gate() below combines both.
    """
    if isinstance(fields, dict):
        return {
            key: (REDACTED if key in SENSITIVE_FIELDS else redact_evidence_packet(value))
            for key, value in fields.items()
        }
    if isinstance(fields, list):
        return [redact_evidence_packet(item) for item in fields]
    if isinstance(fields, tuple):
        return tuple(redact_evidence_packet(item) for item in fields)
    return fields


def _iter_atoms(payload):
    """Yield every scalar (leaf) value in payload, plus every dict key, at
    any depth through dicts/lists/tuples. Both contains_canary() and
    evaluate_evidence_gate()'s sensitive-value check need to inspect the
    same surface: a canary or a copied sensitive value can hide in a key
    name exactly as easily as in a value, and at any nesting depth."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key
            yield from _iter_atoms(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            yield from _iter_atoms(item)
    else:
        yield payload


def contains_canary(payload) -> bool:
    """True if CANARY_MARKER appears anywhere in payload -- as a dict key or
    a dict/list/tuple value, at any depth, as a substring of any string atom.
    Used to prove -- not assume -- whether a built payload is canary-free,
    independent of which field name or nesting depth it was hiding in."""
    return any(
        isinstance(atom, str) and CANARY_MARKER in atom for atom in _iter_atoms(payload)
    )


def _collect_sensitive_values(fields):
    """Recursively collect the value found under every key in
    SENSITIVE_FIELDS, at any depth through dicts/lists/tuples. Reads from
    the original, pre-redaction input -- this is the independent source
    evaluate_evidence_gate()'s sensitive-value check verifies against,
    deliberately not redact_evidence_packet()'s own output.

    Skips `None` and `""`: evidence packets are built from quarantined rows,
    and rows land in quarantine largely *because* a field is null -- a
    sensitive field that is itself empty carries no content to leak, and
    checking it only produces false positives against every other null or
    empty field elsewhere in the same packet (round 2's over-blocking
    regression: `{"ssn": None, "stage": None}` blocked because `None ==
    None`, not because anything leaked).
    """
    values = []
    if isinstance(fields, dict):
        for key, value in fields.items():
            if key in SENSITIVE_FIELDS and value not in (None, ""):
                values.append(value)
            values.extend(_collect_sensitive_values(value))
    elif isinstance(fields, (list, tuple)):
        for item in fields:
            values.extend(_collect_sensitive_values(item))
    return values


# Below this length, a string sensitive value is indistinguishable from
# ordinary text -- checking it produces noise, not signal. Every fictional
# sensitive format in this project (FICTIONAL_SENSITIVE_LEAD's ssn/
# credit_card/api_key) is 11+ characters; 8 sits comfortably under all of
# them while ruling out short tokens, initials, and single-character values
# that are common, unrelated content in a real packet.
_MIN_LEAK_MATCH_LENGTH = 8


def _value_leaked(packet, value) -> bool:
    """True if `value` (a sensitive value read from the original input, via
    _collect_sensitive_values) is still present as a substring of some
    string atom anywhere in the redacted `packet`. Independent of which key
    it's under, so a sensitive value copied verbatim into an unrelated,
    non-sensitive field is still caught.

    Two deliberate narrowings, both against over-blocking regressions found
    in round 2 review (see the chapter doc):

    - Only checks string values of at least _MIN_LEAK_MATCH_LENGTH. A short
      string (`"password": "a"`) matched almost every other field as a
      substring of ordinary text -- not a leak, just short strings being
      common. There is no length below which a match is still meaningful,
      so short values are not checked at all, not checked more loosely.
    - Only checks string values, full stop. A non-string sensitive value
      (e.g. a numeric `api_key`) matching another field by bare equality
      (`api_key == lead_id`) is common by coincidence in small fixtures --
      unrelated numeric fields collide constantly -- and equality alone
      can't distinguish that from a real copy. Every SENSITIVE_FIELDS value
      in this project's actual fixture is string-shaped (ssn, credit_card,
      api_key, phone_number, password are all secrets rendered as text), so
      this check's value is in string content matching; a non-string
      sensitive value is still redacted by field name in
      redact_evidence_packet, just not cross-checked here.
    """
    if not isinstance(value, str) or len(value) < _MIN_LEAK_MATCH_LENGTH:
        return False
    return any(isinstance(atom, str) and value in atom for atom in _iter_atoms(packet))


def evaluate_evidence_gate(fields) -> tuple[bool, list[str]]:
    """Fail-closed pre-flight check an outbound model call must pass before
    it may send `fields` anywhere. Mirrors quality.evaluate_gate's shape: an
    empty problems list is the only way `allowed` is True. No caller of this
    function exists yet in this project -- see the module docstring.

    Two independent checks against the redacted result, not one check
    validating itself:

    1. Sensitive-value check: every meaningful string value that appeared
       under a SENSITIVE_FIELDS key in the *original* `fields` (collected by
       _collect_sensitive_values, before redaction) must not appear anywhere
       in the redacted packet. This is deliberately not "does
       redact_evidence_packet's own output still have REDACTED under those
       keys" -- that would only ever confirm redact_evidence_packet agrees
       with itself, which it always will by construction. Instead it re-reads
       the pre-redaction input as an independent source and scans the
       *result* for leftover copies, the same shape as chapter 02's row-
       conservation check (verify accepted+quarantined against the persisted
       tables, not against the rate computation that might itself be wrong).
       This is what catches a sensitive value duplicated, verbatim, into an
       unrelated non-sensitive field that field-name redaction has no way to
       know about. "Meaningful" excludes None/empty values
       (_collect_sensitive_values) and non-string or short-string values
       (_value_leaked's _MIN_LEAK_MATCH_LENGTH) -- see those functions'
       docstrings for why checking them produced false positives, not real
       findings, in round 2 review.
    2. Canary check: scans the redacted result for CANARY_MARKER regardless
       of which key (or nesting depth) it's in -- catches what field-name
       redaction structurally cannot.

    A packet that fails either check is blocked outright.
    """
    packet = redact_evidence_packet(fields)
    problems = []
    for value in _collect_sensitive_values(fields):
        if _value_leaked(packet, value):
            problems.append(
                f"a sensitive value survived redaction, found elsewhere in "
                f"the packet: {value!r}"
            )
    if contains_canary(packet):
        problems.append(
            "canary marker present in packet after redaction -- field-name "
            "redaction alone missed it; blocking rather than sending"
        )
    return (not problems), problems
