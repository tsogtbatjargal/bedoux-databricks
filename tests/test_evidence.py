from src.bedoux import evidence


# ---------------------------------------------------------------------------
# redact_evidence_packet: known sensitive fields, useful evidence survives
# ---------------------------------------------------------------------------


def test_redact_strips_known_sensitive_fields():
    packet = evidence.redact_evidence_packet(evidence.FICTIONAL_SENSITIVE_LEAD)
    assert packet["ssn"] == evidence.REDACTED
    assert packet["credit_card"] == evidence.REDACTED
    assert packet["api_key"] == evidence.REDACTED


def test_redact_leaves_non_sensitive_evidence_untouched():
    packet = evidence.redact_evidence_packet(evidence.FICTIONAL_SENSITIVE_LEAD)
    assert packet["lead_id"] == 9001
    assert packet["campaign_id"] == 7
    assert packet["stage"] == "qualified"


def test_redact_by_field_name_alone_misses_the_canary():
    # The canary lives in "notes", not a SENSITIVE_FIELDS key -- field-name
    # redaction alone must not accidentally catch it, or the test below
    # (which proves the packet-wide scan is what actually catches it) would
    # be vacuous.
    packet = evidence.redact_evidence_packet(evidence.FICTIONAL_SENSITIVE_LEAD)
    assert evidence.CANARY_MARKER in packet["notes"]


def test_redact_recurses_into_nested_row_dicts():
    # The realistic evidence-packet shape is a list of quarantined row
    # dicts under a key, e.g. {"source": ..., "rows": [row, row, ...]}.
    # Before the depth fix, redaction was shallow (top-level keys only)
    # while contains_canary was already recursive -- the two halves of the
    # gate disagreed about depth, so a sensitive field nested one level
    # down was neither redacted nor blocked.
    packet = {"source": "leads_quarantine", "rows": [dict(evidence.FICTIONAL_SENSITIVE_LEAD)]}
    redacted = evidence.redact_evidence_packet(packet)
    assert redacted["rows"][0]["ssn"] == evidence.REDACTED
    assert redacted["rows"][0]["credit_card"] == evidence.REDACTED
    assert redacted["rows"][0]["api_key"] == evidence.REDACTED


def test_redact_preserves_non_sensitive_evidence_at_depth():
    # The positive case for the same fix: recursion must not turn into
    # over-redaction -- non-sensitive fields nested inside a row survive.
    packet = {"source": "leads_quarantine", "rows": [dict(evidence.FICTIONAL_SENSITIVE_LEAD)]}
    redacted = evidence.redact_evidence_packet(packet)
    assert redacted["source"] == "leads_quarantine"
    assert redacted["rows"][0]["lead_id"] == 9001
    assert redacted["rows"][0]["campaign_id"] == 7
    assert redacted["rows"][0]["stage"] == "qualified"


# ---------------------------------------------------------------------------
# contains_canary: recursive, substring, independent of field name or key
# ---------------------------------------------------------------------------


def test_contains_canary_true_when_present_in_any_field():
    assert evidence.contains_canary(evidence.FICTIONAL_SENSITIVE_LEAD) is True


def test_contains_canary_false_on_clean_payload():
    clean = {"lead_id": 1, "campaign_id": 2, "stage": "new"}
    assert evidence.contains_canary(clean) is False


def test_contains_canary_recurses_through_nested_structures():
    nested = {"a": [{"b": {"c": f"prefix {evidence.CANARY_MARKER} suffix"}}]}
    assert evidence.contains_canary(nested) is True


def test_contains_canary_detects_marker_hidden_in_a_key_name():
    # contains_canary previously scanned dict values but not keys -- a
    # canary smuggled into a key name (not a value) was reported clean.
    payload = {"ref_" + evidence.CANARY_MARKER: "x"}
    assert evidence.contains_canary(payload) is True


# ---------------------------------------------------------------------------
# evaluate_evidence_gate: fail-closed, blocks what field-name redaction misses
# ---------------------------------------------------------------------------


def test_gate_blocks_the_canary_fixture():
    allowed, problems = evidence.evaluate_evidence_gate(evidence.FICTIONAL_SENSITIVE_LEAD)
    assert allowed is False
    assert any("canary" in p for p in problems)


def test_gate_allows_a_clean_packet():
    clean = {"lead_id": 1, "campaign_id": 2, "stage": "new"}
    allowed, problems = evidence.evaluate_evidence_gate(clean)
    assert allowed is True
    assert problems == []


def test_gate_allows_a_packet_once_its_sensitive_field_is_redacted():
    # A known sensitive field that redaction successfully strips, with no
    # canary anywhere, is the pass case -- proves the gate isn't
    # unconditionally blocking, only blocking on an actual undetected-
    # sensitive or canary condition.
    fields = {"lead_id": 1, "ssn": "000-00-0000"}
    allowed, problems = evidence.evaluate_evidence_gate(fields)
    assert allowed is True
    assert problems == []


def test_gate_blocks_canary_hidden_in_a_key_name():
    allowed, problems = evidence.evaluate_evidence_gate({"ref_" + evidence.CANARY_MARKER: "x"})
    assert allowed is False
    assert any("canary" in p for p in problems)


def test_gate_allows_nested_packet_once_sensitive_fields_are_actually_redacted():
    # Reproduces the pre-fix false-open case exactly: a nested packet (the
    # realistic "rows" shape) with the canary removed from "notes". Before
    # the depth fix, this returned (True, []) while ssn/credit_card/api_key
    # sat untouched two levels down -- "allowed" was true but wrong, because
    # nothing had actually looked at that depth. After the fix, allowed=True
    # here is correct, because the nested fields are genuinely gone from the
    # result, not just unexamined -- confirmed independently below.
    packet = {"source": "leads_quarantine", "rows": [dict(evidence.FICTIONAL_SENSITIVE_LEAD)]}
    packet["rows"][0]["notes"] = "clean note, no canary"
    allowed, problems = evidence.evaluate_evidence_gate(packet)
    assert allowed is True
    assert problems == []
    redacted = evidence.redact_evidence_packet(packet)
    assert redacted["rows"][0]["ssn"] == evidence.REDACTED


def test_gate_catches_a_sensitive_value_copied_into_a_non_sensitive_field():
    # The original "sensitive field survived redaction" loop checked
    # redact_evidence_packet's own output for something that function
    # unconditionally guarantees -- it could never fire. This is the case
    # it was meant to catch: the raw ssn value duplicated, verbatim, into
    # an unrelated field name that field-name redaction has no way to know
    # about. The fixed check verifies against the original input's
    # sensitive values (an independent source), not the redaction
    # function's own claim about itself.
    fields = {"ssn": "000-00-0000", "notes": "SSN on file: 000-00-0000"}
    allowed, problems = evidence.evaluate_evidence_gate(fields)
    assert allowed is False
    assert any("000-00-0000" in p for p in problems)
