"""Guarded outbound model-call path (chapter 04, first increment).

The call site chapter 03's "a failed check prevents the external call"
criterion was waiting on: evidence goes through evidence.py's gate, and
only a packet that passed is serialized and handed to a provider. A failed
gate returns before the provider is touched.

Pure Python, no network. The provider is injected; this project ships no
real one (see known-gaps.md, "Chapter 04's runtime model provider is
deliberately not built"), so every call made through here today goes to a
test fake. Nothing in bedoux_analytics_job calls this module yet.

Outcomes carry fixed reason codes only -- never evaluate_evidence_gate's
problem strings, raw provider errors, or an unvalidated response -- so a
caller can log or persist an outcome without re-checking it.
"""

import json
from dataclasses import dataclass
from typing import Protocol

from . import evidence

BLOCKED = "blocked"   # the gate refused; the provider was never called
PENDING = "pending"   # the provider was called but gave no usable report
REPORTED = "reported"  # the provider returned a report that validated

# Required report fields and their types. Anything else in a response is
# dropped rather than passed through unchecked.
REPORT_FIELDS = {"summary": str, "uncertainty": str, "proposed_recovery": str}


class ProviderTimeout(Exception):
    """Raised by a provider when `complete` exceeds its `timeout_s`."""


class Provider(Protocol):
    """One method. Enforcing `timeout_s` is the provider's job (a real
    adapter would pass it to its HTTP client); this module only decides what
    a timeout means for the outcome."""

    def complete(self, payload: str, *, timeout_s: float) -> str: ...


@dataclass(frozen=True)
class CallOutcome:
    status: str
    reason_codes: tuple = ()
    report: dict | None = None


def serialize_packet(packet) -> str:
    """The exact bytes a provider receives. `ensure_ascii=False` keeps
    non-ASCII text literal, so the final check below sees the same
    characters the provider does instead of `\\uXXXX` escapes. `default=str`
    renders timestamps and other non-JSON values -- which is also why the
    final check exists: `str()` of an object can produce text that the
    dict-level gate never saw."""
    return json.dumps(packet, sort_keys=True, ensure_ascii=False, default=str)


def _gate_reason_codes(problems):
    codes = set()
    for problem in problems:
        if problem.startswith("canary"):
            codes.add("canary_present")
        elif problem.startswith("sensitive value"):
            codes.add("sensitive_value_leak")
        else:
            codes.add("evidence_gate_failed")
    return tuple(sorted(codes))


def _final_payload_problems(fields, payload):
    """Re-check the serialized string itself, against the original input
    as the independent source -- the same two checks evaluate_evidence_gate
    runs on the dict, applied to what actually leaves the process."""
    codes = set()
    if evidence.contains_canary(payload):
        codes.add("canary_present")
    for _path, value in evidence._collect_sensitive_values(fields):
        if evidence._value_leaked(payload, value):
            codes.add("sensitive_value_leak")
    return tuple(sorted(codes))


def _parse_report(raw):
    """Return (report, None) or (None, reason_code). Never raises."""
    if not isinstance(raw, str):
        return None, "malformed_response"
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None, "malformed_response"
    if not isinstance(parsed, dict):
        return None, "malformed_response"
    report = {}
    for name, kind in REPORT_FIELDS.items():
        value = parsed.get(name)
        if not isinstance(value, kind) or not value.strip():
            return None, "malformed_response"
        report[name] = value
    return report, None


def call_model(fields, provider, *, timeout_s: float = 30.0) -> CallOutcome:
    """Gate `fields`, then (only if the gate passes) send the redacted,
    serialized packet to `provider` exactly once.

    - Gate fails, or the serialized payload fails the final check:
      BLOCKED, provider not called.
    - Provider times out or raises: PENDING, with a fixed code. The
      exception text is discarded, since it could echo the payload.
    - Response isn't a JSON object with non-empty string `summary`,
      `uncertainty`, and `proposed_recovery`: PENDING.
    - Otherwise REPORTED, with only those three fields kept.

    No retries: one attempt per call. A PENDING outcome is meant to be
    visible and retried deliberately, not looped on here.
    """
    allowed, problems = evidence.evaluate_evidence_gate(fields)
    if not allowed:
        return CallOutcome(BLOCKED, _gate_reason_codes(problems))

    payload = serialize_packet(evidence.redact_evidence_packet(fields))
    final_problems = _final_payload_problems(fields, payload)
    if final_problems:
        return CallOutcome(BLOCKED, final_problems)

    try:
        raw = provider.complete(payload, timeout_s=timeout_s)
    except (ProviderTimeout, TimeoutError):
        return CallOutcome(PENDING, ("provider_timeout",))
    except Exception:
        return CallOutcome(PENDING, ("provider_error",))

    report, code = _parse_report(raw)
    if report is None:
        return CallOutcome(PENDING, (code,))
    return CallOutcome(REPORTED, (), report)
