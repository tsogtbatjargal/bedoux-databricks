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


# ---------------------------------------------------------------------------
# contains_canary: recursive, substring, independent of field name
# ---------------------------------------------------------------------------


def test_contains_canary_true_when_present_in_any_field():
    assert evidence.contains_canary(evidence.FICTIONAL_SENSITIVE_LEAD) is True


def test_contains_canary_false_on_clean_payload():
    clean = {"lead_id": 1, "campaign_id": 2, "stage": "new"}
    assert evidence.contains_canary(clean) is False


def test_contains_canary_recurses_through_nested_structures():
    nested = {"a": [{"b": {"c": f"prefix {evidence.CANARY_MARKER} suffix"}}]}
    assert evidence.contains_canary(nested) is True


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
