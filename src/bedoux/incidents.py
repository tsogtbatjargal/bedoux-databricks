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
the gate blocks. Never the raw fields. Outcomes store the status and fixed
reason codes only, not the provider's report text: report content isn't
validated against its evidence yet (a later increment).
"""

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from . import model_call

OPENED = "opened"
OUTCOME = "outcome"


@dataclass(frozen=True)
class Incident:
    incident_id: str
    opened_ts: str
    evidence_payload: str | None  # None when the gate blocked
    status: str  # model_call.PENDING until an outcome is recorded
    reason_codes: tuple = ()


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
        })

    def load(self):
        """Replay the file into {incident_id: Incident}. A line that doesn't
        parse is skipped: a crash mid-write leaves a torn last line, and the
        write it belonged to never completed, so nothing depends on it."""
        incidents = {}
        if not os.path.exists(self.path):
            return incidents
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
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
    incident_id = log.open_incident(payload)
    if payload is None:
        outcome = model_call.CallOutcome(model_call.BLOCKED, codes)
    else:
        outcome = model_call.send_payload(payload, provider, timeout_s=timeout_s)
    log.record_outcome(incident_id, outcome)
    return incident_id, outcome
