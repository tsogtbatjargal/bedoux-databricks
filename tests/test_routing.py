import hashlib
import json
from pathlib import Path

import pytest

from src.bedoux import model_call, routing
from src.bedoux.evidence import CANARY_MARKER
from src.bedoux.routing import (DISMISS, HUMAN, RULES_ONLY, RULES_PLUS_CLASSIFIER,
                                RULES_PLUS_REASONING, RUNBOOK, STRATEGIES, UNKNOWN, route)

CASES = json.loads((Path(__file__).parent / "fixtures" / "routing_cases.json")
                   .read_text(encoding="utf-8"))
HELD_OUT = CASES["held_out"]
HELD_OUT_SHA256 = "c4e55cb90e1399e928d83aed90a8332b06306d15f61a3887aeb0c212eb659da6"


class ScriptedModel:
    """A fake classifier or reasoning model. Answers by the case_id in the
    payload it receives; a dict is returned as JSON, an exception raised,
    a string returned as-is. Records every payload."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def complete(self, payload, *, timeout_s):
        self.calls.append(payload)
        answer = self.answers[json.loads(payload)["case_id"]]
        if isinstance(answer, BaseException):
            raise answer
        return json.dumps(answer) if isinstance(answer, dict) else answer


def _c(label, confidence):
    return {"label": label, "confidence": confidence}


# Scripted answers for the held-out set. The classifier is deliberately
# wrong or unsure on some cases, so every path is exercised; h07 is a
# scripted failure (fooled by the embedded instruction).
CLASSIFIER = {
    "h01": _c("healthy", 0.95), "h02": _c("healthy", 0.9),
    "h03": _c("healthy", 0.99),            # wrong, and the gate failed
    "h04": _c("data_quality", 0.9),
    "h06": _c("sensitive_data", 0.6),      # right, but under the threshold
    "h07": _c("healthy", 0.92),            # fooled
    "h08": _c("unknown", 0.5),
    "h09": _c("data_quality", 0.85),
    "h10": RuntimeError("classifier unavailable"),
}
REASONER = {
    "h01": _c("healthy", 0.9), "h02": _c("healthy", 0.9), "h03": _c("data_quality", 0.9),
    "h04": _c("data_quality", 0.9), "h06": _c("sensitive_data", 0.9),
    "h07": _c("suspicious_instruction", 0.9), "h08": _c("data_quality", 0.9),
    "h09": _c("data_quality", 0.9), "h10": _c("healthy", 0.9),
}


def _case(case_id):
    return next(c for c in HELD_OUT if c["case_id"] == case_id)


def _route(case_id, strategy, classifier=None, reasoner=None):
    classifier = classifier or ScriptedModel(CLASSIFIER)
    reasoner = reasoner or ScriptedModel(REASONER)
    return route(_case(case_id)["fields"], strategy, classifier=classifier,
                 reasoner=reasoner), classifier, reasoner


# ---------------------------------------------------------------------------
# Every route goes through the gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_the_gate_refusing_means_no_model_of_any_kind_is_called(strategy):
    result, classifier, reasoner = _route("h05", strategy)  # canary in evidence
    assert (result.action, result.reason_codes[0]) == (HUMAN, "evidence_gate_refused")
    assert classifier.calls == [] and reasoner.calls == []


@pytest.mark.parametrize("case_id", ["h06", "h08", "h10"])  # classifier, then reasoning
def test_every_model_receives_exactly_the_checked_payload(case_id):
    result, classifier, reasoner = _route(case_id, RULES_PLUS_CLASSIFIER)
    expected = model_call.prepare_payload(_case(case_id)["fields"])[0].text
    assert result.calls == ("classifier", "reasoning")
    assert classifier.calls == [expected]
    assert reasoner.calls == [expected]


def test_the_cheap_route_sends_redacted_evidence():
    _, classifier, _ = _route("h06", RULES_PLUS_CLASSIFIER)
    assert "123-45-6789" not in classifier.calls[0]
    assert json.loads(classifier.calls[0])["rows"][0]["ssn"] == "[REDACTED]"


def test_a_classifier_answer_echoing_a_secret_is_not_trusted():
    leaky = ScriptedModel({"h06": _c("sensitive_data 123-45-6789", 0.99)})
    result, _, reasoner = _route("h06", RULES_PLUS_CLASSIFIER, classifier=leaky)
    assert result.calls == ("classifier", "reasoning")
    assert "report_leak" in result.reason_codes
    assert "123-45-6789" not in repr(result)


def test_rules_only_never_calls_a_model():
    for case in HELD_OUT:
        classifier, reasoner = ScriptedModel(CLASSIFIER), ScriptedModel(REASONER)
        route(case["fields"], RULES_ONLY, classifier=classifier, reasoner=reasoner)
        assert classifier.calls == [] and reasoner.calls == []


# ---------------------------------------------------------------------------
# Severe deterministic signals can't be dismissed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("strategy", [RULES_PLUS_CLASSIFIER, RULES_PLUS_REASONING])
def test_a_severe_signal_is_not_dismissed_whatever_the_model_says(strategy):
    sure_healthy = ScriptedModel({"h03": _c("healthy", 1.0), "h04": _c("healthy", 1.0)})
    for case_id in ("h03", "h04"):  # gate failed; rows not conserved
        result, _, _ = _route(case_id, strategy, classifier=sure_healthy,
                              reasoner=sure_healthy)
        assert result.action == HUMAN
        assert "severe_signal_not_dismissable" in result.reason_codes
        assert result.severe


# ---------------------------------------------------------------------------
# The project's own evidence-log shape (review regression; deliberately NOT
# in the held-out set -- that set is frozen, and adding a case because a
# review found it would be tuning on the test set)
# ---------------------------------------------------------------------------

# Shaped like chapter-03-evidence.md's Run 3 gate_evidence_log row.
RUN_3 = {
    "run_start_ms": 1790132411535,
    "passed": False,
    "problems": ["leads: gate_passed is false (quarantine rate 32.8%)"],
    "sources": [
        {"source": "leads", "total": 500, "quarantined_rows": 164, "accepted_rows": 336,
         "quarantine_rate": 0.328, "gate_passed": False, "conserved": True},
        {"source": "ops_events", "total": 365, "quarantined_rows": 8, "accepted_rows": 357,
         "quarantine_rate": 0.021917808219178082, "gate_passed": True, "conserved": True},
        {"source": "web_events", "total": 2000, "quarantined_rows": 46, "accepted_rows": 1954,
         "quarantine_rate": 0.023, "gate_passed": True, "conserved": True},
    ],
}


class AlwaysHealthy:
    def __init__(self):
        self.calls = []

    def complete(self, payload, *, timeout_s):
        self.calls.append(payload)
        return json.dumps(_c("healthy", 0.95))


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_an_evidence_log_record_of_a_failed_run_is_never_dismissed(strategy):
    model = AlwaysHealthy()
    result = route(RUN_3, strategy, classifier=model, reasoner=model)
    assert result.action != DISMISS
    assert result.severe
    if strategy != RULES_ONLY:
        assert result.action in (HUMAN, RUNBOOK)
        assert "severe_signal_not_dismissable" in result.reason_codes


@pytest.mark.parametrize("record, codes", [
    (RUN_3, ("run_failed", "source_gate_failed")),
    ({"passed": False, "sources": []}, ("run_failed",)),
    ({"passed": True, "sources": [{"source": "leads", "gate_passed": True, "conserved": False}]},
     ("source_not_conserved",)),
    ({"passed": True, "sources": [{"source": "leads"}]}, ()),  # missing isn't a signal
])
def test_evidence_log_signals(record, codes):
    assert routing.rule_signals(record) == codes


def test_a_passing_evidence_log_record_can_be_dismissed():
    passing = {**RUN_3, "passed": True, "problems": [],
               "sources": [{**s, "gate_passed": True} for s in RUN_3["sources"]]}
    assert route(passing, RULES_ONLY).action == DISMISS
    model = AlwaysHealthy()
    assert route(passing, RULES_PLUS_CLASSIFIER, classifier=model).action == DISMISS


def test_a_model_cannot_dismiss_evidence_the_rules_do_not_recognise():
    unfamiliar = {"source": "leads", "status": "FAILED", "failed_sources": ["leads"]}
    assert routing.rule_signals(unfamiliar) == () and not routing.recognized(unfamiliar)
    model = AlwaysHealthy()
    for strategy in (RULES_PLUS_CLASSIFIER, RULES_PLUS_REASONING):
        result = route(unfamiliar, strategy, classifier=model, reasoner=model)
        assert result.action == HUMAN
        assert "unrecognized_evidence" in result.reason_codes


# ---------------------------------------------------------------------------
# Unknown, low-confidence, invalid, or unavailable escalates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("answer, code", [
    (_c("unknown", 0.99), "classified_unknown"),
    (_c("healthy", 0.79), "low_confidence"),
    (_c("dismiss_everything", 0.99), "invalid_label"),
    ('{"label": "healthy"}', "malformed_response"),
    (RuntimeError("down"), "provider_error"),
    (model_call.ProviderTimeout(), "provider_timeout"),
])
def test_an_unusable_classifier_answer_escalates_to_reasoning(answer, code):
    classifier = ScriptedModel({"h01": answer})
    result, _, reasoner = _route("h01", RULES_PLUS_CLASSIFIER, classifier=classifier)
    assert result.calls == ("classifier", "reasoning")
    assert code in result.reason_codes
    assert len(reasoner.calls) == 1
    assert (result.label, result.action) == ("healthy", DISMISS)  # the reasoner's answer


def test_a_confident_known_answer_does_not_escalate():
    result, _, reasoner = _route("h09", RULES_PLUS_CLASSIFIER)
    assert (result.calls, result.action) == (("classifier",), RUNBOOK)
    assert reasoner.calls == []


def test_when_nothing_usable_comes_back_a_person_decides():
    down = ScriptedModel({"h01": RuntimeError("down")})
    result, _, _ = _route("h01", RULES_PLUS_CLASSIFIER, classifier=down, reasoner=down)
    assert (result.label, result.action) == (UNKNOWN, HUMAN)


# ---------------------------------------------------------------------------
# The held-out set is frozen, and the harness counts what the roadmap asks
# ---------------------------------------------------------------------------


def test_the_held_out_set_is_frozen_and_separate_from_tuning():
    digest = hashlib.sha256(json.dumps(HELD_OUT, sort_keys=True).encode()).hexdigest()
    assert digest == HELD_OUT_SHA256, "held-out cases changed; that invalidates comparisons"
    assert not {c["case_id"] for c in HELD_OUT} & {c["case_id"] for c in CASES["tuning"]}


def test_the_comparison_on_scripted_fakes():
    """These numbers describe the scripted fakes above and the harness --
    nothing about Jev or a real reasoning model. They pin the harness's
    arithmetic, including a negative result: the classifier route dismisses
    h07, the embedded instruction, which is a severe miss."""
    # instruction_rule=False: chapter 05's rules, so its recorded numbers
    # stay reproducible. Chapter 06's rule is scored in test_boundaries.py.
    results = {s: routing.evaluate(HELD_OUT, s, classifier=ScriptedModel(CLASSIFIER),
                                   reasoner=ScriptedModel(REASONER), instruction_rule=False)
               for s in STRATEGIES}
    pick = ("severe_misses", "false_alerts", "correct_labels", "escalations", "to_human",
            "classifier_calls", "reasoning_calls", "est_cost_units")
    got = {s: tuple(results[s][k] for k in pick) for s in STRATEGIES}
    assert got == {
        RULES_ONLY: (1, 0, 6, 0, 1, 0, 0, 0),
        RULES_PLUS_REASONING: (0, 0, 10, 0, 1, 0, 9, 180),
        RULES_PLUS_CLASSIFIER: (1, 0, 8, 3, 2, 9, 3, 69),
    }
    assert all(r["latency"] is None and r["retries"] == 0 for r in results.values())


# ---------------------------------------------------------------------------
# send_payload's classification mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", [
    "not json", "[]", '{"label": "", "confidence": 0.5}', '{"label": "x", "confidence": 1.5}',
    '{"label": "x", "confidence": true}', '{"label": 3, "confidence": 0.5}',
])
def test_a_malformed_classification_is_pending(raw):
    payload, _ = model_call.prepare_payload({"case_id": "x", "source": "leads"})
    outcome = model_call.send_payload(payload, ScriptedModel({"x": raw}),
                                      expect="classification")
    assert (outcome.status, outcome.reason_codes) == (model_call.PENDING,
                                                      ("malformed_response",))


def test_classification_mode_still_refuses_an_unchecked_payload():
    with pytest.raises(TypeError):
        model_call.send_payload(json.dumps({"case_id": "x", "notes": CANARY_MARKER}),
                                ScriptedModel({}), expect="classification")
