"""Local incident log for chapter 04's investigation path.

An append-only JSON Lines file. Each incident gets two events: `opened`,
written and fsynced *before* the model is called, and `outcome`, written
after. An incident with no `outcome` event is pending -- so if the process
dies between the two, the incident is still there, and still pending, the
next time the file is read.

Local on purpose: chapter 04's investigation service runs locally (see
docs/sentinel/README.md, "Scope"), not inside a Databricks job. Nothing in
bedoux_analytics_job writes here.

What gets stored: the exact payload prepared for the provider -- redacted
and checked for the canary and copied secrets -- or no evidence at all when
the gate blocks. Never the raw fields. Outcomes store the status, fixed
reason codes, and -- only for a REPORTED outcome -- the report, which by
then has had its citations resolved against the sent payload and been
screened for the canary and copied secrets -- both inside send_payload.
"""

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from . import model_call

OPENED = "opened"
OUTCOME = "outcome"
TOOL_CALL = "tool_call"


@dataclass(frozen=True)
class Incident:
    incident_id: str
    opened_ts: str
    evidence_payload: str | None  # None when the gate blocked
    status: str  # model_call.PENDING until an outcome is recorded
    reason_codes: tuple = ()
    report: dict | None = None  # only for REPORTED
    tool_calls: tuple = ()  # dicts, in order; see IncidentLog.record_tool_call


class IncidentLog:
    def __init__(self, path):
        self.path = path

    def _append(self, event):
        line = json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n"
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def open_incident(self, evidence_payload):
        incident_id = uuid.uuid4().hex
        self._append({
            "event": OPENED,
            "incident_id": incident_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "evidence_payload": evidence_payload,
        })
        return incident_id

    def record_outcome(self, incident_id, outcome):
        self._append({
            "event": OUTCOME,
            "incident_id": incident_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "status": outcome.status,
            "reason_codes": list(outcome.reason_codes),
            "report": outcome.report if outcome.status == model_call.REPORTED else None,
        })

    def record_tool_call(self, incident_id, request, status, reason_codes,
                         evidence_payload=None):
        """Record a tool request and what happened to it (tools.py). The
        request was screened by send_payload before it got here.
        `evidence_payload` is the checked payload that carried the result to
        the model -- None if the tool didn't run or its result was blocked,
        so a raw result is never stored."""
        self._append({
            "event": TOOL_CALL,
            "incident_id": incident_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "request": request,
            "status": status,
            "reason_codes": list(reason_codes),
            "evidence_payload": evidence_payload,
        })

    def append_event(self, event_type, incident_id, **fields):
        """Append any other event type (recovery.py's). Callers are
        responsible for the "never raw fields" rule for what they pass."""
        self._append({"event": event_type, "incident_id": incident_id,
                      "ts": datetime.now(timezone.utc).isoformat(), **fields})

    def events(self):
        """Every parsed event, in file order. A line that doesn't parse is
        skipped: a crash mid-write leaves a torn last line, and the write it
        belonged to never completed, so nothing depends on it."""
        if not os.path.exists(self.path):
            return
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue

    def load(self):
        """Replay the file into {incident_id: Incident}. Event types this
        method doesn't know (recovery events) are left to their readers."""
        incidents = {}
        for event in self.events():
            incident_id = event.get("incident_id")
            if event.get("event") == OPENED:
                incidents[incident_id] = Incident(
                    incident_id, event["ts"], event["evidence_payload"],
                    model_call.PENDING,
                )
            elif event.get("event") == OUTCOME and incident_id in incidents:
                opened = incidents[incident_id]
                incidents[incident_id] = Incident(
                    incident_id, opened.opened_ts, opened.evidence_payload,
                    event["status"], tuple(event["reason_codes"]),
                    event.get("report"), opened.tool_calls,
                )
            elif event.get("event") == TOOL_CALL and incident_id in incidents:
                current = incidents[incident_id]
                call = {k: event[k] for k in
                        ("request", "status", "reason_codes", "evidence_payload")}
                incidents[incident_id] = Incident(
                    incident_id, current.opened_ts, current.evidence_payload,
                    current.status, current.reason_codes, current.report,
                    current.tool_calls + (call,),
                )
        return incidents

    def pending(self):
        return [i for i in self.load().values() if i.status == model_call.PENDING]


def investigate(fields, provider, log, *, timeout_s=30.0):
    """Open an incident, then call the model, then record the outcome.

    Order matters: the incident is on disk before the provider is touched.
    If opening it fails, the exception propagates and the provider is never
    called -- no model call happens without a record. If recording the
    outcome fails, the incident stays visibly pending.

    The gate decides exactly as in model_call.call_model: the same
    prepare_payload runs, and a blocked incident never reaches the provider.
    Returns (incident_id, CallOutcome).
    """
    payload, codes = model_call.prepare_payload(fields)
    incident_id = log.open_incident(payload.text if payload is not None else None)
    if payload is None:
        outcome = model_call.CallOutcome(model_call.BLOCKED, codes)
    else:
        outcome = model_call.send_payload(payload, provider, timeout_s=timeout_s)
    log.record_outcome(incident_id, outcome)
    return incident_id, outcome
