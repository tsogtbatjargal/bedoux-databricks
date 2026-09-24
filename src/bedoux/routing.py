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
  model says, the incident isn't dismissed. rule_signals reads two shapes:
  flat gate_status-style fields, and gate_evidence_log records (top-level
  `passed`, per-source values under `sources[]`).
- Evidence the rules don't recognise at all -- neither shape -- can't be
  dismissed by a model either: a "healthy" answer goes to a person
  (`unrecognized_evidence`). Dismissal is the one outcome nobody looks at
  again, so it needs the rules to have understood the evidence.
- Instruction-like text anywhere in the evidence (boundaries.py, chapter
  06) is a severe signal too: `instruction_in_evidence`, labelled
  suspicious_instruction by the rules. It's a regex flag and easy to evade;
  see boundaries.py for what it does and doesn't catch.
- Unknown / low-confidence / invalid / unavailable never becomes a
  dismissal; with nothing better, it goes to a human.
- Routing decides where an incident goes. It never approves recovery
  (recovery.py) and never clears a failed gate.

Audit (chapter 06): given an IncidentLog, route() appends one
`route_decision` event per decision -- strategy, label, action, reason
codes, model stages called, whether a severe signal applied, and the
SHA-256 of the checked payload (None when the gate refused). Only fixed
codes and a hash: never raw fields, model text, or matched instruction
text. explain() turns an event back into sentences from EXPLANATIONS.

Costs: EST_COST_UNITS are *relative units* assumed for comparison -- an
estimate from fixed inputs, not a price and not measured spend. Latency is
not measured at all offline. Only fakes exist for both models.
"""

import hashlib
import uuid
from dataclasses import dataclass

from . import boundaries, model_call
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

ROUTE_DECISION = "route_decision"

ACTION_EXPLANATIONS = {
    DISMISS: "dismissed: no further action",
    RUNBOOK: "sent to the runbook for its label",
    HUMAN: "sent to a person",
}
# Every reason code route() can record, with a fixed sentence. A code
# missing here makes explain() say so, and a test fails.
EXPLANATIONS = {
    "gate_failed": "the publication gate failed",
    "not_conserved": "rows were not conserved",
    "run_failed": "the evidence-log record says the run failed",
    "source_gate_failed": "a source in the evidence-log record failed its gate",
    "source_not_conserved": "a source in the evidence-log record did not conserve rows",
    "instruction_in_evidence": "instruction-like text was found in the evidence (text not stored)",
    "evidence_gate_refused": "the evidence gate refused the payload, so no model was called",
    "canary_present": "the canary marker was in the evidence",
    "sensitive_value_leak": "a sensitive value would have left the process",
    "evidence_gate_failed": "the evidence gate failed for another reason",
    "classified_unknown": "the model answered unknown",
    "invalid_label": "the model answered a label that isn't on the list",
    "low_confidence": "the classifier's confidence was under the threshold",
    "malformed_response": "the model's answer didn't parse",
    "provider_error": "the model provider failed",
    "provider_timeout": "the model provider timed out",
    "report_leak": "the model's answer echoed a secret or the canary",
    "severe_signal_not_dismissable": "a model said healthy, but a severe signal can't be dismissed",
    "unrecognized_evidence": "a model said healthy, but the rules didn't recognise the evidence",
}


@dataclass(frozen=True)
class Route:
    label: str
    action: str
    reason_codes: tuple = ()
    calls: tuple = ()  # model stages called, in order: "classifier", "reasoning"
    severe: bool = False


def _source_entries(fields):
    sources = fields.get("sources")
    if not isinstance(sources, list):
        return []
    return [entry for entry in sources if isinstance(entry, dict)]


def rule_signals(fields):
    """Deterministic severe signals from the evidence itself, in either
    shape: flat gate_status-style fields, or a gate_evidence_log record
    (top-level `passed`, per-source values under `sources[]`). `is False`,
    not falsiness: a missing field is not a signal either way."""
    codes = []
    if fields.get("gate_passed") is False:
        codes.append("gate_failed")
    if fields.get("conserved") is False:
        codes.append("not_conserved")
    if fields.get("passed") is False:
        codes.append("run_failed")
    entries = _source_entries(fields)
    if any(entry.get("gate_passed") is False for entry in entries):
        codes.append("source_gate_failed")
    if any(entry.get("conserved") is False for entry in entries):
        codes.append("source_not_conserved")
    return tuple(codes)


def recognized(fields):
    """True if the rules understand this evidence's shape: a boolean
    gate_passed/conserved/passed at the top, or a sources[] entry carrying
    a boolean gate_passed/conserved."""
    if any(isinstance(fields.get(k), bool) for k in ("gate_passed", "conserved", "passed")):
        return True
    return any(isinstance(entry.get(k), bool)
               for entry in _source_entries(fields) for k in ("gate_passed", "conserved"))


def _rules_label(fields, severe_codes):
    if severe_codes == (boundaries.INSTRUCTION_IN_EVIDENCE,):
        return "suspicious_instruction"
    if severe_codes:
        return "data_quality"
    if fields.get("gate_passed") is True and fields.get("conserved") is True:
        return "healthy"
    entries = _source_entries(fields)
    if fields.get("passed") is True and entries and all(
            e.get("gate_passed") is True and e.get("conserved") is True for e in entries):
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


def _finish(label, severe_codes, codes, calls, known_shape=True):
    codes = list(codes)
    if severe_codes:
        codes = list(severe_codes) + codes
        if label in ("healthy", UNKNOWN):
            if label == "healthy":
                codes.append("severe_signal_not_dismissable")
            return Route(label, HUMAN, tuple(codes), tuple(calls), True)
        return Route(label, RUNBOOK, tuple(codes), tuple(calls), True)
    if label == "healthy":
        if not known_shape:
            codes.append("unrecognized_evidence")
            return Route(label, HUMAN, tuple(codes), tuple(calls))
        return Route(label, DISMISS, tuple(codes), tuple(calls))
    if label == UNKNOWN:
        return Route(label, HUMAN, tuple(codes), tuple(calls))
    return Route(label, RUNBOOK, tuple(codes), tuple(calls))


def route(fields, strategy, *, classifier=None, reasoner=None, timeout_s=30.0,
          instruction_rule=True, log=None, incident_id=None):
    """`instruction_rule=False` reproduces chapter 05's rules exactly, so
    its recorded comparison stays reproducible. Nothing else should turn it
    off. With `log`, the decision is appended as a `route_decision` event."""
    if strategy not in STRATEGIES:
        raise ValueError("unknown strategy")
    decision, payload = _decide(fields, strategy, classifier, reasoner, timeout_s,
                                instruction_rule)
    if log is not None:
        log.append_event(
            ROUTE_DECISION, incident_id, decision_id=uuid.uuid4().hex,
            strategy=strategy, instruction_rule=instruction_rule,
            label=decision.label, action=decision.action,
            reason_codes=list(decision.reason_codes), calls=list(decision.calls),
            severe=decision.severe,
            payload_sha256=(hashlib.sha256(payload.text.encode("utf-8")).hexdigest()
                            if payload is not None else None))
    return decision


def explain(event):
    """Sentences explaining a recorded route_decision, from the event
    alone."""
    lines = [f"{event['strategy']}: labelled {event['label']}, "
             f"{ACTION_EXPLANATIONS.get(event['action'], 'unexplained action')}"]
    lines.append("models called: " + (", ".join(event["calls"]) or "none"))
    if event["severe"]:
        lines.append("a severe signal applied, so it could not be dismissed")
    lines += [f"{code}: {EXPLANATIONS.get(code, 'UNEXPLAINED CODE')}"
              for code in event["reason_codes"]]
    return lines


def _decide(fields, strategy, classifier, reasoner, timeout_s, instruction_rule):
    """(Route, CheckedPayload or None)."""
    severe_codes = rule_signals(fields)
    if instruction_rule:
        severe_codes += boundaries.instruction_signals(fields)
    known_shape = recognized(fields)

    payload, gate_codes = model_call.prepare_payload(fields)
    if payload is None:
        # The evidence gate refused: no model of any kind sees this.
        return Route("sensitive_data", HUMAN, ("evidence_gate_refused",) + gate_codes,
                     (), True), None

    if strategy == RULES_ONLY:
        return _finish(_rules_label(fields, severe_codes), severe_codes, (), ()), payload

    calls, codes = [], []
    if strategy == RULES_PLUS_CLASSIFIER:
        calls.append("classifier")
        label, confidence, code = _ask(payload, classifier, timeout_s)
        if code is None and confidence >= CONFIDENCE_THRESHOLD:
            return _finish(label, severe_codes, codes, calls, known_shape), payload
        codes.append(code or "low_confidence")

    calls.append("reasoning")
    label, _confidence, code = _ask(payload, reasoner, timeout_s)
    if code is not None:
        codes.append(code)
    return _finish(label, severe_codes, codes, calls, known_shape), payload


def evaluate(cases, strategy, *, classifier=None, reasoner=None, instruction_rule=True):
    """Score one strategy on labelled cases: [{"case_id", "fields",
    "expected_label", "severe"}]. With fake models, these numbers describe
    the fakes' scripted answers and this harness -- nothing about Jev or a
    real reasoning model."""
    routes = [route(c["fields"], strategy, classifier=classifier, reasoner=reasoner,
                    instruction_rule=instruction_rule)
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
