"""Incident routing: rules, a cheap classifier, and selective escalation
(chapter 05, first step).

Three strategies the roadmap asks to compare on the same held-out set:

- RULES_ONLY: deterministic signals decide; no model is called.
- RULES_PLUS_REASONING: every incident goes to the (expensive) reasoning
  model.
- RULES_PLUS_CLASSIFIER: a cheap classifier (the role Jev would play) goes
  first; only an unknown, low-confidence, invalid, or unavailable answer
  escalates to the reasoning model.

Every model call -- classifier or reasoning -- goes through chapter 04's
path: model_call.prepare_payload once per incident, then send_payload with
that CheckedPayload. A cheaper route gets the same redacted, checked
payload and the same leak screen; if the gate refuses, no model of either
kind is called. There's no separate "lightweight" serialization.

Rules the models can't override:
- A severe deterministic signal (the publication gate failed, rows weren't
  conserved, or the evidence gate refused) is non-dismissable: whatever a
  model says, the incident isn't dismissed.
- Unknown / low-confidence / invalid / unavailable never becomes a
  dismissal; with nothing better, it goes to a human.
- Routing decides where an incident goes. It never approves recovery
  (recovery.py) and never clears a failed gate.

Costs: EST_COST_UNITS are *relative units* assumed for comparison -- an
estimate from fixed inputs, not a price and not measured spend. Latency is
not measured at all offline. Only fakes exist for both models.
"""

from dataclasses import dataclass

from . import model_call
from .model_call import CLASSIFIED

LABELS = ("data_quality", "sensitive_data", "suspicious_instruction", "healthy")
UNKNOWN = "unknown"

DISMISS = "dismiss"   # healthy: no action
RUNBOOK = "runbook"   # a known label: follow that label's runbook
HUMAN = "human"       # unknown, unavailable, or severe-but-unexplained: a person decides

RULES_ONLY = "rules_only"
RULES_PLUS_REASONING = "rules_plus_reasoning"
RULES_PLUS_CLASSIFIER = "rules_plus_classifier"
STRATEGIES = (RULES_ONLY, RULES_PLUS_REASONING, RULES_PLUS_CLASSIFIER)

# An arbitrary starting value, set before the held-out set existed and not
# tuned on anything -- tuning against fakes would be meaningless. Below
# this, a classifier answer escalates.
CONFIDENCE_THRESHOLD = 0.8

# ESTIMATE, not measured: assumed relative cost per call, in units, not
# currency. Only the ratio matters, and it is an assumption.
EST_COST_UNITS = {"classifier": 1, "reasoning": 20}


@dataclass(frozen=True)
class Route:
    label: str
    action: str
    reason_codes: tuple = ()
    calls: tuple = ()  # model stages called, in order: "classifier", "reasoning"
    severe: bool = False


def rule_signals(fields):
    """Deterministic severe signals from the evidence itself. `is False`,
    not falsiness: a missing field is not a signal either way."""
    codes = []
    if fields.get("gate_passed") is False:
        codes.append("gate_failed")
    if fields.get("conserved") is False:
        codes.append("not_conserved")
    return tuple(codes)


def _rules_label(fields, severe_codes):
    if severe_codes:
        return "data_quality"
    if fields.get("gate_passed") is True and fields.get("conserved") is True:
        return "healthy"
    return UNKNOWN


def _ask(payload, provider, timeout_s):
    """(label, confidence, code) from one gated call. Anything but a valid
    classification with a known label comes back as UNKNOWN."""
    outcome = model_call.send_payload(payload, provider, timeout_s=timeout_s,
                                      expect="classification")
    if outcome.status != CLASSIFIED:
        return UNKNOWN, 0.0, outcome.reason_codes[0]
    label = outcome.classification["label"]
    if label == UNKNOWN:
        return UNKNOWN, 0.0, "classified_unknown"
    if label not in LABELS:
        return UNKNOWN, 0.0, "invalid_label"
    return label, outcome.classification["confidence"], None


def _finish(label, severe_codes, codes, calls):
    codes = list(codes)
    if severe_codes:
        codes = list(severe_codes) + codes
        if label in ("healthy", UNKNOWN):
            if label == "healthy":
                codes.append("severe_signal_not_dismissable")
            return Route(label, HUMAN, tuple(codes), tuple(calls), True)
        return Route(label, RUNBOOK, tuple(codes), tuple(calls), True)
    if label == "healthy":
        return Route(label, DISMISS, tuple(codes), tuple(calls))
    if label == UNKNOWN:
        return Route(label, HUMAN, tuple(codes), tuple(calls))
    return Route(label, RUNBOOK, tuple(codes), tuple(calls))


def route(fields, strategy, *, classifier=None, reasoner=None, timeout_s=30.0):
    if strategy not in STRATEGIES:
        raise ValueError("unknown strategy")
    severe_codes = rule_signals(fields)

    payload, gate_codes = model_call.prepare_payload(fields)
    if payload is None:
        # The evidence gate refused: no model of any kind sees this.
        return Route("sensitive_data", HUMAN, ("evidence_gate_refused",) + gate_codes,
                     (), True)

    if strategy == RULES_ONLY:
        return _finish(_rules_label(fields, severe_codes), severe_codes, (), ())

    calls, codes = [], []
    if strategy == RULES_PLUS_CLASSIFIER:
        calls.append("classifier")
        label, confidence, code = _ask(payload, classifier, timeout_s)
        if code is None and confidence >= CONFIDENCE_THRESHOLD:
            return _finish(label, severe_codes, codes, calls)
        codes.append(code or "low_confidence")

    calls.append("reasoning")
    label, _confidence, code = _ask(payload, reasoner, timeout_s)
    if code is not None:
        codes.append(code)
    return _finish(label, severe_codes, codes, calls)


def evaluate(cases, strategy, *, classifier=None, reasoner=None):
    """Score one strategy on labelled cases: [{"case_id", "fields",
    "expected_label", "severe"}]. With fake models, these numbers describe
    the fakes' scripted answers and this harness -- nothing about Jev or a
    real reasoning model."""
    routes = [route(c["fields"], strategy, classifier=classifier, reasoner=reasoner)
              for c in cases]
    n = len(cases)
    classifier_calls = sum(r.calls.count("classifier") for r in routes)
    reasoning_calls = sum(r.calls.count("reasoning") for r in routes)
    return {
        "strategy": strategy,
        "cases": n,
        "severe_misses": sum(1 for c, r in zip(cases, routes)
                             if c["severe"] and r.action == DISMISS),
        "false_alerts": sum(1 for c, r in zip(cases, routes)
                            if c["expected_label"] == "healthy" and r.action != DISMISS),
        "correct_labels": sum(1 for c, r in zip(cases, routes)
                              if r.label == c["expected_label"]),
        "escalations": sum(1 for r in routes if r.calls == ("classifier", "reasoning")),
        "to_human": sum(1 for r in routes if r.action == HUMAN),
        "classifier_calls": classifier_calls,
        "reasoning_calls": reasoning_calls,
        "retries": 0,  # no route retries; one call per stage
        "est_cost_units": (classifier_calls * EST_COST_UNITS["classifier"]
                           + reasoning_calls * EST_COST_UNITS["reasoning"]),
        "latency": None,  # not measured offline
    }
