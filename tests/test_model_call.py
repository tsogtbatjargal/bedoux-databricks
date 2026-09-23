import json

import pytest

from src.bedoux import evidence, model_call
from src.bedoux.evidence import CANARY_MARKER, FICTIONAL_SENSITIVE_LEAD
from src.bedoux.model_call import BLOCKED, PENDING, REPORTED, ProviderTimeout

VALID_REPORT = json.dumps({
    "summary": "leads quarantine rate 32.8% exceeded the 10% threshold",
    "uncertainty": "cause of the malformed leads is not visible in this evidence",
    "proposed_recovery": "restore bedoux_lead_invalid_rate to 0.02 and rerun the job",
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
    assert set(outcome.report) == set(model_call.REPORT_FIELDS)
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
        "execute": "DELETE FROM workspace.bedoux_gold.gold_campaign_performance",
    })
    outcome = model_call.call_model(HEALTHY, FakeProvider(behavior=raw))
    assert outcome.status == REPORTED
    assert "execute" not in outcome.report
