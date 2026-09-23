import json

import pytest

from src.bedoux import evidence, model_call
from src.bedoux.evidence import CANARY_MARKER, FICTIONAL_SENSITIVE_LEAD
from src.bedoux.model_call import BLOCKED, PENDING, REPORTED, ProviderTimeout

VALID_REPORT = json.dumps({
    "summary": "leads quarantine rate 32.8% exceeded the 10% threshold",
    "uncertainty": "cause of the malformed leads is not visible in this evidence",
    "proposed_recovery": "restore bedoux_lead_invalid_rate to 0.02 and rerun the job",
    "citations": ["source"],
})

# Healthy evidence: gate_status-shaped, nothing sensitive, no canary.
HEALTHY = {
    "source": "leads",
    "gate_passed": False,
    "quarantine_rate": 0.328,
    "rows": [{"lead_id": 1, "campaign_id": 7, "stage": "new"}],
}


class FakeProvider:
    """Records every payload it receives. `behavior` decides what happens
    on each call: a string is returned, an exception is raised."""

    def __init__(self, behavior=VALID_REPORT):
        self.behavior = behavior
        self.calls = []

    def complete(self, payload, *, timeout_s):
        self.calls.append({"payload": payload, "timeout_s": timeout_s})
        if isinstance(self.behavior, BaseException):
            raise self.behavior
        return self.behavior


def _no_secret_in(outcome):
    text = repr(outcome)
    for secret in ("000-00-0000", "4111-1111-1111-1111",
                   "sk_fake_0000000000000000", CANARY_MARKER):
        assert secret not in text


# ---------------------------------------------------------------------------
# A failed gate stops the call before it happens
# ---------------------------------------------------------------------------


def test_canary_blocks_with_zero_provider_calls():
    provider = FakeProvider()
    outcome = model_call.call_model(dict(FICTIONAL_SENSITIVE_LEAD), provider)
    assert outcome.status == BLOCKED
    assert "canary_present" in outcome.reason_codes
    assert provider.calls == []
    _no_secret_in(outcome)


def test_copied_secret_blocks_with_zero_provider_calls():
    provider = FakeProvider()
    fields = {"ssn": "123-45-6789", "notes": "caller read out 123-45-6789"}
    outcome = model_call.call_model(fields, provider)
    assert outcome.status == BLOCKED
    assert outcome.reason_codes == ("sensitive_value_leak",)
    assert provider.calls == []
    assert "123-45-6789" not in repr(outcome)


def test_nested_canary_blocks_with_zero_provider_calls():
    provider = FakeProvider()
    fields = {"source": "leads_quarantine",
              "rows": [{"lead_id": 1, "notes": f"ref {CANARY_MARKER}"}]}
    outcome = model_call.call_model(fields, provider)
    assert outcome.status == BLOCKED
    assert provider.calls == []


def test_evaluate_evidence_gate_verdict_alone_stops_the_call(monkeypatch):
    """The gate's verdict is authoritative, not just the checks it happens
    to run today: if evaluate_evidence_gate refuses clean evidence (say, a
    rule added later), the provider still isn't called. Without this, the
    final serialized check would mask a call site that ignored the gate --
    it repeats the gate's two current checks on the string."""
    monkeypatch.setattr(evidence, "evaluate_evidence_gate",
                        lambda fields: (False, ["some future rule"]))
    provider = FakeProvider()
    outcome = model_call.call_model(HEALTHY, provider)
    assert outcome.status == BLOCKED
    assert outcome.reason_codes == ("evidence_gate_failed",)
    assert provider.calls == []


def test_gate_problem_strings_never_reach_the_outcome():
    """Reason codes are fixed strings, not evaluate_evidence_gate's own
    problem text (which names field paths)."""
    fields = {"ssn": "123-45-6789", "notes": "123-45-6789"}
    _, problems = evidence.evaluate_evidence_gate(fields)
    outcome = model_call.call_model(fields, FakeProvider())
    for problem in problems:
        assert problem not in outcome.reason_codes


def test_final_serialized_check_catches_what_the_dict_gate_cannot():
    """An object whose str() carries the canary passes the dict-level gate
    (contains_canary only inspects strings), but serialize_packet renders
    it with default=str. The final check on the actual payload blocks it."""

    class Opaque:
        def __str__(self):
            return f"ref {CANARY_MARKER}"

    fields = {"source": "leads", "detail": Opaque()}
    allowed, _ = evidence.evaluate_evidence_gate(fields)
    assert allowed, "precondition: the dict-level gate misses this"

    provider = FakeProvider()
    outcome = model_call.call_model(fields, provider)
    assert outcome.status == BLOCKED
    assert outcome.reason_codes == ("canary_present",)
    assert provider.calls == []


# ---------------------------------------------------------------------------
# A passing gate sends exactly the checked, redacted payload, once
# ---------------------------------------------------------------------------


def test_healthy_evidence_reaches_the_provider_once_and_reports():
    provider = FakeProvider()
    outcome = model_call.call_model(HEALTHY, provider, timeout_s=5.0)
    assert outcome.status == REPORTED
    assert outcome.reason_codes == ()
    assert set(outcome.report) == set(model_call.REPORT_FIELDS) | {"citations"}
    assert len(provider.calls) == 1
    assert provider.calls[0]["timeout_s"] == 5.0


def test_sent_payload_is_exactly_the_redacted_serialization():
    fields = {"source": "leads", "ssn": "123-45-6789", "stage": "qualified"}
    provider = FakeProvider()
    outcome = model_call.call_model(fields, provider)
    assert outcome.status == REPORTED
    sent = provider.calls[0]["payload"]
    assert sent == model_call.serialize_packet(evidence.redact_evidence_packet(fields))
    assert "123-45-6789" not in sent
    assert json.loads(sent)["ssn"] == evidence.REDACTED
    assert json.loads(sent)["stage"] == "qualified"


def test_call_does_not_mutate_the_callers_fields():
    fields = {"source": "leads", "ssn": "123-45-6789", "rows": [{"ssn": "987-65-4321"}]}
    before = json.dumps(fields, sort_keys=True)
    model_call.call_model(fields, FakeProvider())
    assert json.dumps(fields, sort_keys=True) == before


# ---------------------------------------------------------------------------
# Timeouts and provider errors leave a visible pending outcome
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("exc", [ProviderTimeout(), TimeoutError()])
def test_timeout_is_pending(exc):
    provider = FakeProvider(behavior=exc)
    outcome = model_call.call_model(HEALTHY, provider)
    assert outcome.status == PENDING
    assert outcome.reason_codes == ("provider_timeout",)
    assert outcome.report is None
    assert len(provider.calls) == 1, "one attempt, no silent retry loop"


def test_provider_error_is_pending_and_its_text_is_discarded():
    """A provider error message could echo the payload back; the outcome
    keeps only a fixed code."""
    provider = FakeProvider(behavior=RuntimeError("upstream said: " + CANARY_MARKER))
    outcome = model_call.call_model(HEALTHY, provider)
    assert outcome.status == PENDING
    assert outcome.reason_codes == ("provider_error",)
    assert CANARY_MARKER not in repr(outcome)


# ---------------------------------------------------------------------------
# Malformed responses leave a visible pending outcome
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", [
    None,
    b'{"summary": "x"}',
    "",
    "not json at all",
    "[1, 2, 3]",
    json.dumps("just a string"),
    json.dumps({"summary": "s", "uncertainty": "u"}),  # missing field
    json.dumps({"summary": "s", "uncertainty": "u", "proposed_recovery": 3}),
    json.dumps({"summary": "s", "uncertainty": "   ", "proposed_recovery": "r"}),
])
def test_malformed_response_is_pending(raw):
    outcome = model_call.call_model(HEALTHY, FakeProvider(behavior=raw))
    assert outcome.status == PENDING
    assert outcome.reason_codes == ("malformed_response",)
    assert outcome.report is None


def test_unexpected_response_fields_are_dropped():
    raw = json.dumps({
        "summary": "s", "uncertainty": "u", "proposed_recovery": "r",
        "citations": ["source"],
        "execute": "DELETE FROM workspace.bedoux_gold.gold_campaign_performance",
    })
    outcome = model_call.call_model(HEALTHY, FakeProvider(behavior=raw))
    assert outcome.status == REPORTED
    assert "execute" not in outcome.report


# ---------------------------------------------------------------------------
# send_payload can't be reached without the gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("unchecked", [
    json.dumps({"ssn": "123-45-6789", "notes": f"ref {CANARY_MARKER}"}),
    # Byte-for-byte the text prepare_payload would produce, but unwrapped:
    # the check is on how the payload was made, not on what it looks like.
    model_call.serialize_packet(evidence.redact_evidence_packet(HEALTHY)),
    "",
    {"source": "leads"},
    None,
])
def test_send_payload_refuses_anything_but_a_checked_payload(unchecked):
    provider = FakeProvider()
    with pytest.raises(TypeError):
        model_call.send_payload(unchecked, provider)
    assert provider.calls == []


def test_checked_payload_is_only_made_by_prepare_payload():
    with pytest.raises(TypeError):
        model_call.CheckedPayload("anything")
    with pytest.raises(TypeError):
        model_call.CheckedPayload("anything", _token=object())
    checked, codes = model_call.prepare_payload(HEALTHY)
    assert isinstance(checked, model_call.CheckedPayload) and codes == ()
    with pytest.raises(AttributeError):
        checked._text = "swapped"


# ---------------------------------------------------------------------------
# A report only counts if it cites evidence that was actually sent
# ---------------------------------------------------------------------------


def _report(citations, summary="leads quarantine rate exceeded the threshold"):
    body = {"summary": summary, "uncertainty": "cause not visible",
            "proposed_recovery": "rerun after fixing the generator"}
    if citations is not _OMIT:
        body["citations"] = citations
    return json.dumps(body)


_OMIT = object()


def test_citations_that_resolve_in_the_sent_payload_are_reported():
    citations = ["source", "quarantine_rate", "rows[0].stage", "rows[0]"]
    outcome = model_call.call_model(HEALTHY, FakeProvider(behavior=_report(citations)))
    assert outcome.status == REPORTED
    assert outcome.report["citations"] == citations


@pytest.mark.parametrize("citations", [_OMIT, [], None])
def test_a_report_without_citations_is_pending(citations):
    provider = FakeProvider(behavior=_report(citations))
    outcome = model_call.call_model(HEALTHY, provider)
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("no_citations",))
    assert outcome.report is None


@pytest.mark.parametrize("citations", ["source", [3], ["source", ""], [["source"]]])
def test_badly_typed_citations_are_malformed(citations):
    outcome = model_call.call_model(HEALTHY, FakeProvider(behavior=_report(citations)))
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("malformed_response",))


@pytest.mark.parametrize("bad", [
    "lead_owner",          # no such key
    "rows[0].ssn",         # key never in this evidence
    "rows[5].stage",       # index out of range
    "rows.stage",          # key access on a list
    "source[0]",           # index into a string
    "rows[0].stage.x",     # past a leaf
    "rows[0]..stage",      # empty segment
])
def test_a_citation_that_does_not_resolve_in_the_payload_is_refused(bad):
    """The provider was called and answered; the report still doesn't
    count, because one citation points at something it was never sent."""
    provider = FakeProvider(behavior=_report(["source", bad]))
    outcome = model_call.call_model(HEALTHY, provider)
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("unresolved_citation",))
    assert outcome.report is None
    assert len(provider.calls) == 1


def test_citations_resolve_against_what_was_sent_not_the_original_fields():
    """`ssn` exists in both, but in the payload it's the redaction marker --
    the provider never saw the value, so citing it is refused."""
    fields = {"source": "leads", "ssn": "123-45-6789", "stage": "qualified"}
    outcome = model_call.call_model(fields, FakeProvider(behavior=_report(["stage", "ssn"])))
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("redacted_citation",))


def test_citing_a_container_that_holds_a_redacted_field_is_allowed():
    fields = {"rows": [{"ssn": "123-45-6789", "stage": "qualified"}]}
    outcome = model_call.call_model(fields, FakeProvider(behavior=_report(["rows[0]"])))
    assert outcome.status == REPORTED


@pytest.mark.parametrize("container", ["secrets", "rows[0]", "rows"])
def test_citing_a_container_whose_values_are_all_redacted_is_refused(container):
    """Nothing in it was visible to the provider, so it supports nothing."""
    fields = {"source": "leads",
              "secrets": {"ssn": "123-45-6789", "password": "hunter2-fictional"},
              "rows": [{"ssn": "987-65-4321", "api_key": "sk_fake_1111111111111111"}]}
    provider = FakeProvider(behavior=_report(["source", container]))
    outcome = model_call.call_model(fields, provider)
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("redacted_citation",))


def test_resolve_citation_handles_a_list_at_the_root():
    assert model_call.resolve_citation([{"a": 1}], "[0].a") == 1
    assert model_call.resolve_citation({"a": 1}, "[0]") is model_call._MISSING


# ---------------------------------------------------------------------------
# A report that echoes the canary or a secret is never handed back
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("echo", [f"ref {CANARY_MARKER}", "caller id 123-45-6789"])
def test_a_report_that_echoes_the_canary_or_a_secret_is_refused(echo):
    """The provider only saw the redacted payload. A secret from the
    original fields turning up in its report means something is wrong --
    and it must not come back to the caller."""
    fields = {"source": "leads", "ssn": "123-45-6789", "stage": "qualified"}
    provider = FakeProvider(behavior=_report(["stage"], summary=echo))
    outcome = model_call.call_model(fields, provider)
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("report_leak",))
    assert outcome.report is None
    assert "123-45-6789" not in repr(outcome) and CANARY_MARKER not in repr(outcome)


def test_send_payload_itself_screens_the_report():
    """Not just call_model: a caller using prepare_payload + send_payload
    directly can't receive a report carrying the canary or a secret."""
    fields = {"source": "leads", "api_key": "sk_fake_0000000000000000"}
    echo = f"ref {CANARY_MARKER}, key sk_fake_0000000000000000"
    payload, codes = model_call.prepare_payload(fields)
    assert codes == ()
    provider = FakeProvider(behavior=_report(["source"], summary=echo))
    outcome = model_call.send_payload(payload, provider)
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("report_leak",))
    assert outcome.report is None


def test_checked_payload_repr_and_text_hold_no_sensitive_value():
    fields = {"source": "leads", "ssn": "123-45-6789", "api_key": "sk_fake_0000000000000000"}
    payload, _ = model_call.prepare_payload(fields)
    for secret in ("123-45-6789", "sk_fake_0000000000000000"):
        assert secret not in repr(payload)
        assert secret not in str(payload)
        assert secret not in payload.text
