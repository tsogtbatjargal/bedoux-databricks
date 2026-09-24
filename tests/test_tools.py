import json
from pathlib import Path

import pytest

from src.bedoux import boundaries, model_call, tools
from src.bedoux.evidence import CANARY_MARKER
from src.bedoux.incidents import IncidentLog
from src.bedoux.model_call import PENDING, REPORTED
from src.bedoux.tools import investigate_with_tools

# Local synthetic fixtures -- the only thing these tools ever read.
FIXTURES = {
    "gate_status": [
        {"source": "leads", "gate_passed": False, "quarantine_rate": 0.328},
        {"source": "web_events", "gate_passed": True, "quarantine_rate": 0.023},
    ],
    "quarantine": {
        "leads": [{"lead_id": n, "stage": None, "ssn": "123-45-6789"} for n in range(8)],
    },
    "gate_evidence_log": [
        {"source": "leads", "gate_passed": False, "problems": ["rate above threshold"]},
    ],
}

EVIDENCE = {"source": "leads", "gate_passed": False, "quarantine_rate": 0.328}


def _request(tool, **args):
    return json.dumps({"tool_request": {"tool": tool, "args": args}})


def _report(*citations):
    return json.dumps({"summary": "leads quarantine rate exceeded the threshold",
                       "uncertainty": "cause not visible",
                       "proposed_recovery": "rerun after fixing the generator",
                       "citations": list(citations) or ["evidence.source"]})


class ScriptedProvider:
    """Returns its responses in order and records every payload."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, payload, *, timeout_s):
        self.calls.append(payload)
        return self.responses[len(self.calls) - 1]


class Recorder:
    """A tool implementation that records its calls."""

    def __init__(self, fn=lambda fixtures, **args: "done"):
        self.fn = fn
        self.calls = []

    def __call__(self, fixtures, **args):
        self.calls.append(args)
        return self.fn(fixtures, **args)


@pytest.fixture
def log(tmp_path):
    return IncidentLog(tmp_path / "incidents.jsonl")


# ---------------------------------------------------------------------------
# An allowed tool runs, and its result reaches the model as checked evidence
# ---------------------------------------------------------------------------


def test_an_allowed_tool_runs_and_its_result_is_sent(log):
    gate_status = Recorder(tools.read_gate_status)
    provider = ScriptedProvider(_request("read_gate_status", source="leads"),
                                _report("tool_results[0].result[0].quarantine_rate"))
    incident_id, outcome = investigate_with_tools(
        EVIDENCE, provider, log, FIXTURES,
        implementations={**tools.IMPLEMENTATIONS, "read_gate_status": gate_status})

    assert outcome.status == REPORTED
    assert gate_status.calls == [{"source": "leads"}]
    sent = json.loads(provider.calls[1])
    assert sent["tool_results"][0]["result"] == [FIXTURES["gate_status"][0]]

    [call] = IncidentLog(log.path).load()[incident_id].tool_calls
    assert (call["status"], call["request"]["tool"]) == (tools.RAN, "read_gate_status")
    assert call["evidence_payload"] == provider.calls[1]


def test_a_tool_result_with_a_sensitive_field_is_redacted_not_raw(log):
    provider = ScriptedProvider(_request("read_quarantine_sample", source="leads"),
                                _report("tool_results[0].result[0].lead_id"))
    incident_id, outcome = investigate_with_tools(EVIDENCE, provider, log, FIXTURES)
    assert outcome.status == REPORTED
    rows = json.loads(provider.calls[1])["tool_results"][0]["result"]
    assert len(rows) == tools.MAX_SAMPLE_ROWS  # 8 rows in the fixture
    assert {row["ssn"] for row in rows} == {"[REDACTED]"}
    assert "123-45-6789" not in Path(log.path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Anything off the allowlist is refused and never executed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", [
    "restore_source", "replay_batch", "deploy_bundle", "write_gold",
    "delete_quarantine", "READ_GATE_STATUS", "read_gate_status ", "__import__",
])
def test_a_tool_off_the_allowlist_is_refused_and_never_executed(log, name):
    """The implementation exists and is callable; the allowlist alone
    keeps it from running."""
    recovery = Recorder()
    provider = ScriptedProvider(_request(name, source="leads"), _report())
    incident_id, outcome = investigate_with_tools(
        EVIDENCE, provider, log, FIXTURES,
        implementations={**tools.IMPLEMENTATIONS, name: recovery})

    assert recovery.calls == []
    assert name not in tools.ALLOWED_TOOLS
    [call] = IncidentLog(log.path).load()[incident_id].tool_calls
    assert call["request"] == {"tool": name, "args": {"source": "leads"}}  # kept as evidence
    # Since chapter 06, a prohibited name is refused first, with its own code.
    code = "prohibited_action" if boundaries.is_prohibited(name) else "tool_not_allowed"
    assert (call["status"], call["reason_codes"]) == (tools.REFUSED, [code])
    # The model is told it was refused, and the investigation carries on.
    refused = json.loads(provider.calls[1])["tool_results"][0]
    assert (refused["status"], refused["result"]) == (tools.REFUSED, None)
    assert outcome.status == REPORTED


@pytest.mark.parametrize("args", [{}, {"source": 1}, {"source": "leads", "path": "/"},
                                  {"source": "leads", "limit": True}])
def test_bad_arguments_are_refused_and_never_executed(args):
    sample = Recorder()
    status, codes, result = tools.execute_tool_request(
        {"tool": "read_quarantine_sample", "args": args}, FIXTURES,
        {**tools.IMPLEMENTATIONS, "read_quarantine_sample": sample})
    assert (status, codes, result, sample.calls) == (
        tools.REFUSED, ("invalid_tool_args",), None, [])


@pytest.mark.parametrize("limit", [-1, 0, tools.MAX_SAMPLE_ROWS + 1, 50])
def test_a_sample_limit_outside_the_cap_is_refused_and_never_executed(limit):
    """limit=-1 used to slice rows[:-1] -- every row but the last."""
    rows = [{"lead_id": n} for n in range(40)]
    sample = Recorder(tools.read_quarantine_sample)
    status, codes, result = tools.execute_tool_request(
        {"tool": "read_quarantine_sample", "args": {"source": "leads", "limit": limit}},
        {"quarantine": {"leads": rows}},
        {**tools.IMPLEMENTATIONS, "read_quarantine_sample": sample})
    assert (status, codes, result, sample.calls) == (
        tools.REFUSED, ("invalid_tool_args",), None, [])


def test_a_sample_limit_inside_the_cap_is_honoured():
    status, _, result = tools.execute_tool_request(
        {"tool": "read_quarantine_sample", "args": {"source": "leads", "limit": 2}}, FIXTURES)
    assert (status, len(result)) == (tools.RAN, 2)


def test_without_tools_offered_a_tool_request_is_a_malformed_report():
    """call_model and investigate don't offer tools; for them a tool
    request is just not a report."""
    outcome = model_call.call_model(EVIDENCE, ScriptedProvider(_request("read_gate_status",
                                                                        source="leads")))
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("malformed_response",))


def test_a_tool_request_echoing_a_secret_is_not_recorded(log):
    fields = {**EVIDENCE, "api_key": "sk_fake_0000000000000000"}
    provider = ScriptedProvider(_request("read_gate_status", source="sk_fake_0000000000000000"))
    _, outcome = investigate_with_tools(fields, provider, log, FIXTURES)
    assert (outcome.status, outcome.reason_codes) == (PENDING, ("tool_request_leak",))
    assert "sk_fake_0000000000000000" not in Path(log.path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# A tool result is gated like any other evidence before it's sent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row, code", [
    ({"lead_id": 1, "notes": f"ref {CANARY_MARKER}"}, "canary_present"),
    ({"lead_id": 1, "ssn": "123-45-6789", "notes": "read out 123-45-6789"},
     "sensitive_value_leak"),
])
def test_a_tool_result_carrying_the_canary_or_a_secret_is_blocked_not_sent(log, row, code):
    fixtures = {"quarantine": {"leads": [row]}}
    provider = ScriptedProvider(_request("read_quarantine_sample", source="leads"), _report())
    incident_id, outcome = investigate_with_tools(EVIDENCE, provider, log, fixtures)

    assert (outcome.status, outcome.reason_codes) == (PENDING, ("tool_result_blocked", code))
    assert len(provider.calls) == 1  # the result never went out
    [call] = IncidentLog(log.path).load()[incident_id].tool_calls
    assert (call["status"], call["evidence_payload"]) == (tools.BLOCKED_RESULT, None)
    raw = Path(log.path).read_text(encoding="utf-8")
    assert CANARY_MARKER not in raw and "123-45-6789" not in raw


# ---------------------------------------------------------------------------
# The loop is bounded
# ---------------------------------------------------------------------------


def test_the_call_limit_stops_the_loop(log):
    gate_status = Recorder(tools.read_gate_status)
    # Asks for ten tools, then would report. The limit is three.
    provider = ScriptedProvider(*[_request("read_gate_status", source="leads")] * 10,
                                _report())
    incident_id, outcome = investigate_with_tools(
        EVIDENCE, provider, log, FIXTURES,
        implementations={**tools.IMPLEMENTATIONS, "read_gate_status": gate_status})

    assert (outcome.status, outcome.reason_codes) == (PENDING, ("tool_limit_reached",))
    assert len(gate_status.calls) == tools.MAX_TOOL_CALLS
    assert len(provider.calls) == tools.MAX_TOOL_CALLS + 1
    stored = IncidentLog(log.path).load()[incident_id]
    assert [c["status"] for c in stored.tool_calls] == [tools.RAN] * 3 + [tools.NOT_RUN]
    assert stored.status == PENDING


def test_refused_requests_count_toward_the_limit(log):
    provider = ScriptedProvider(*[_request("restore_source")] * 10, _report())
    _, outcome = investigate_with_tools(EVIDENCE, provider, log, FIXTURES)
    assert outcome.reason_codes == ("tool_limit_reached",)
    assert len(provider.calls) == tools.MAX_TOOL_CALLS + 1
