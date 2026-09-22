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


def redact_evidence_packet(fields: dict) -> dict:
    """Return a copy of `fields` with every key in SENSITIVE_FIELDS replaced
    by REDACTED. Every other key, including one that happens to carry the
    canary marker in free text (see FICTIONAL_SENSITIVE_LEAD's "notes"), is
    passed through unchanged -- field-name redaction alone cannot know that.
    Proving the canary doesn't survive end to end is contains_canary()'s job,
    not this function's; evaluate_evidence_gate() below combines both.
    """
    return {
        key: (REDACTED if key in SENSITIVE_FIELDS else value)
        for key, value in fields.items()
    }


def contains_canary(payload) -> bool:
    """True if CANARY_MARKER appears anywhere in payload, recursively through
    dicts/lists/tuples and as a substring of any string value. Used to prove
    -- not assume -- whether a built payload is canary-free, independent of
    which field name it was hiding in."""
    if isinstance(payload, str):
        return CANARY_MARKER in payload
    if isinstance(payload, dict):
        return any(contains_canary(v) for v in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(contains_canary(v) for v in payload)
    return False


def evaluate_evidence_gate(fields: dict) -> tuple[bool, list[str]]:
    """Fail-closed pre-flight check an outbound model call must pass before
    it may send `fields` anywhere. Mirrors quality.evaluate_gate's shape: an
    empty problems list is the only way `allowed` is True. No caller of this
    function exists yet in this project -- see the module docstring.

    Redacts known sensitive fields first, then scans the *result* for the
    canary regardless of which field it's in. A packet that still contains
    the canary after redaction is blocked outright, since a field-name miss
    here is exactly the failure mode this gate exists to catch.
    """
    packet = redact_evidence_packet(fields)
    problems = []
    for field in SENSITIVE_FIELDS:
        if field in fields and packet.get(field) != REDACTED:
            problems.append(f"{field}: sensitive field survived redaction")
    if contains_canary(packet):
        problems.append(
            "canary marker present in packet after redaction -- field-name "
            "redaction alone missed it; blocking rather than sending"
        )
    return (not problems), problems
