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
import re
from dataclasses import dataclass
from typing import Protocol

from . import evidence

BLOCKED = "blocked"   # the gate refused; the provider was never called
PENDING = "pending"   # the provider was called but gave no usable report
REPORTED = "reported"  # the provider returned a report that validated

# Required text fields of a report. `citations` is required too and checked
# separately. Anything else in a response is dropped rather than passed
# through unchecked.
REPORT_FIELDS = {"summary": str, "uncertainty": str, "proposed_recovery": str}

# One segment of a citation path: a key name, then any number of [n]
# indices. Same format evidence._format_path writes: "rows[0].stage".
_SEGMENT = re.compile(r"^([^.\[\]]*)((?:\[\d+\])*)$")


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
    citations = parsed.get("citations")
    if citations is None or citations == []:
        return None, "no_citations"
    if not isinstance(citations, list) or not all(
            isinstance(c, str) and c.strip() for c in citations):
        return None, "malformed_response"
    report["citations"] = list(citations)
    return report, None


_MISSING = object()


def resolve_citation(packet, citation):
    """Follow a dotted path like "rows[0].stage" through `packet`. Returns
    the value there, or _MISSING if any step doesn't exist. Key names
    containing ".", "[" or "]" can't be cited -- a known limit of the
    format."""
    node = packet
    for position, segment in enumerate(citation.split(".")):
        match = _SEGMENT.match(segment)
        if not match:
            return _MISSING
        key, indices = match.groups()
        if key:
            if not isinstance(node, dict) or key not in node:
                return _MISSING
            node = node[key]
        elif position > 0 or not indices:
            return _MISSING  # an empty key only makes sense as "[0]" at the root
        for index in re.findall(r"\[(\d+)\]", indices):
            index = int(index)
            if not isinstance(node, list) or index >= len(node):
                return _MISSING
            node = node[index]
    return node


def _check_citations(report, payload_text):
    """None if every citation resolves in the payload the provider was sent
    and none lands on a redacted value; otherwise a reason code.

    A citation of a redacted value refuses the whole report rather than
    being dropped: the provider never saw that value, so whatever the
    report claims from it has no basis in the evidence. Citing a container
    (e.g. "rows[0]") that holds some redacted fields is allowed -- it also
    holds values the provider did see."""
    packet = json.loads(payload_text)
    for citation in report["citations"]:
        value = resolve_citation(packet, citation)
        if value is _MISSING:
            return "unresolved_citation"
        if value == evidence.REDACTED:
            return "redacted_citation"
    return None


_PREPARED = object()


class CheckedPayload:
    """A payload string that has passed prepare_payload's gate and final
    check. send_payload accepts nothing else, so skipping the gate takes a
    deliberate workaround instead of an easy mistake like
    `send_payload(json.dumps(fields), provider)`.

    Only prepare_payload can create one: the constructor requires a
    module-private token. A slotted class, not a frozen dataclass, because
    `dataclasses.replace` would copy the token onto new, unchecked text.
    This guards against misuse, not against hostile code in the same
    process -- Python can't stop that.
    """

    __slots__ = ("_text",)

    def __init__(self, text, *, _token=None):
        if _token is not _PREPARED:
            raise TypeError("CheckedPayload is only created by prepare_payload")
        object.__setattr__(self, "_text", text)

    def __setattr__(self, name, value):
        raise AttributeError("CheckedPayload is immutable")

    @property
    def text(self) -> str:
        return self._text

    def __repr__(self):
        return f"CheckedPayload(<{len(self._text)} chars>)"


def prepare_payload(fields):
    """Gate `fields` and build the exact string a provider would receive.

    Returns `(CheckedPayload, ())` when both the gate and the final
    serialized check pass, or `(None, reason_codes)` when either refuses.
    The wrapped text is the only form of the evidence that is ever safe to
    send or store: it is
    redacted, and it has been checked for the canary and copied secrets
    after serialization. Redaction alone is not enough -- it doesn't remove
    the canary.
    """
    allowed, problems = evidence.evaluate_evidence_gate(fields)
    if not allowed:
        return None, _gate_reason_codes(problems)

    payload = serialize_packet(evidence.redact_evidence_packet(fields))
    final_problems = _final_payload_problems(fields, payload)
    if final_problems:
        return None, final_problems
    return CheckedPayload(payload, _token=_PREPARED), ()


def send_payload(payload, provider, *, timeout_s: float = 30.0) -> CallOutcome:
    """Send a CheckedPayload once and classify the result. Raises TypeError
    for anything else -- including a plain string -- before the provider is
    touched."""
    if not isinstance(payload, CheckedPayload):
        raise TypeError("send_payload needs a CheckedPayload from prepare_payload")
    try:
        raw = provider.complete(payload.text, timeout_s=timeout_s)
    except (ProviderTimeout, TimeoutError):
        return CallOutcome(PENDING, ("provider_timeout",))
    except Exception:
        return CallOutcome(PENDING, ("provider_error",))

    report, code = _parse_report(raw)
    if report is None:
        return CallOutcome(PENDING, (code,))
    code = _check_citations(report, payload.text)
    if code is not None:
        return CallOutcome(PENDING, (code,))
    return CallOutcome(REPORTED, (), report)


def screen_report(fields, outcome):
    """Refuse a report that carries the canary or a sensitive value from
    the original `fields`. The provider only saw redacted evidence, so
    either one in its reply means something is wrong -- and the report
    must not reach a caller or the incident log. Same two checks as the
    final payload check, run on the report's serialized text."""
    if outcome.status != REPORTED:
        return outcome
    if _final_payload_problems(fields, serialize_packet(outcome.report)):
        return CallOutcome(PENDING, ("report_leak",))
    return outcome


def call_model(fields, provider, *, timeout_s: float = 30.0) -> CallOutcome:
    """Gate `fields`, then (only if the gate passes) send the redacted,
    serialized packet to `provider` exactly once.

    - Gate fails, or the serialized payload fails the final check:
      BLOCKED, provider not called.
    - Provider times out or raises: PENDING, with a fixed code. The
      exception text is discarded, since it could echo the payload.
    - Response isn't a JSON object with non-empty string `summary`,
      `uncertainty`, and `proposed_recovery`: PENDING (malformed_response).
    - `citations` missing or empty (no_citations), or any citation doesn't
      resolve in the payload that was sent (unresolved_citation) or lands
      on a redacted value (redacted_citation): PENDING.
    - The report carries the canary or a copied secret: PENDING
      (report_leak).
    - Otherwise REPORTED, with only those four fields kept.

    No retries: one attempt per call. A PENDING outcome is meant to be
    visible and retried deliberately, not looped on here.
    """
    payload, codes = prepare_payload(fields)
    if payload is None:
        return CallOutcome(BLOCKED, codes)
    return screen_report(fields, send_payload(payload, provider, timeout_s=timeout_s))
