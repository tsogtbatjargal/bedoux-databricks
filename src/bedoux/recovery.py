"""Approved recovery (chapter 04, step 5).

"Recovery requires the defined approval." The approval, as defined here:

- Only the actions in RECOVERY_ACTIONS exist. This module ships no
  executor: the caller injects one, and the only executors in this repo are
  test fakes that record their calls. Nothing here touches the workspace.
- An approval is recorded by approve_recovery -- a human-side call; no
  model path in this project calls it. It names the approver and binds one
  incident, one action, and the SHA-256 of the exact checked payload the
  approver reviewed (the incident's latest stored payload). It gets a
  random approval_id and can be used once.
- execute_recovery runs the action only with a valid approval: one that
  exists in the log, for this incident, this action, and a payload hash
  that still matches the incident's latest payload, and that hasn't been
  used. Anything else is refused with a fixed reason code and the executor
  is never called. A model's proposed_recovery is report text -- evidence
  -- and never an approval; the only thing that counts is an approval_id
  that approve_recovery wrote to the log.

Idempotency: the approval_id is the idempotency key. execute_recovery
writes `recovery_started` (fsynced) *before* calling the executor, which
consumes the approval. A retry with the same approval never runs the
action again: if the first attempt's result was recorded it's refused as
`approval_already_used`; if the first attempt died before recording a
result, it's `recovery_outcome_unknown` and needs a person to check.
At-most-once, not exactly-once -- a crash can leave an action that may or
may not have happened, and this says so instead of re-running it.

Everything is recorded in the incident log: the request, the approval, the
start, and the result. Never raw fields or payload text: approvals store a
hash, results store a status and fixed codes, and an approval_id that
isn't a known one is not stored at all (it could be anything a caller or
model made up).
"""

import hashlib
import uuid
from dataclasses import dataclass

RECOVERY_ACTIONS = frozenset({"restore_lead_invalid_rate", "replay_batch"})

APPROVED = "recovery_approved"
REQUESTED = "recovery_requested"
STARTED = "recovery_started"
RESULT = "recovery_result"

EXECUTED = "executed"
REFUSED = "refused"
FAILED = "failed"


@dataclass(frozen=True)
class RecoveryOutcome:
    status: str
    reason_codes: tuple = ()


def payload_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current_payload(incident):
    """The latest checked payload stored for an incident: the last tool
    call's, if any carried one, else the one it was opened with. None when
    the gate blocked and nothing was stored."""
    for call in reversed(incident.tool_calls):
        if call["evidence_payload"] is not None:
            return call["evidence_payload"]
    return incident.evidence_payload


def approve_recovery(log, incident_id, action, *, approver, payload_sha256):
    """Record a human's approval and return its approval_id.

    `payload_sha256` is the hash of the payload the approver reviewed; it's
    stored as given and checked at execution time, so an approval based on
    anything other than the incident's latest payload won't execute.
    Raises ValueError -- and records nothing -- for an unknown incident, an
    action that doesn't exist, a blank approver, or an incident with no
    stored payload to base an approval on."""
    if action not in RECOVERY_ACTIONS:
        raise ValueError("no such recovery action")
    if not isinstance(approver, str) or not approver.strip():
        raise ValueError("an approval must name its approver")
    incident = log.load().get(incident_id)
    if incident is None:
        raise ValueError("no such incident")
    if current_payload(incident) is None:
        raise ValueError("incident has no stored payload to approve against")
    approval_id = uuid.uuid4().hex
    log.append_event(APPROVED, incident_id, approval_id=approval_id, action=action,
                     approver=approver, payload_sha256=payload_sha256)
    return approval_id


def _approval_state(log, approval_id):
    """(approval event or None, started?, result event or None)."""
    approval, started, result = None, False, None
    for event in log.events():
        if event.get("approval_id") != approval_id:
            continue
        kind = event.get("event")
        if kind == APPROVED:
            approval = event
        elif kind == STARTED:
            started = True
        elif kind == RESULT:
            result = event
    return approval, started, result


def _refuse(log, incident_id, action, approval_id, code):
    log.append_event(REQUESTED, incident_id, action=action if action in RECOVERY_ACTIONS else None,
                     approval_id=approval_id, status=REFUSED, reason_codes=[code])
    return RecoveryOutcome(REFUSED, (code,))


def execute_recovery(log, incident_id, action, approval_id, executor):
    """Run `executor(action, incident_id)` once, only with a valid approval.
    Returns a RecoveryOutcome; the executor's own return value and any
    exception text are discarded."""
    known = isinstance(approval_id, str) and approval_id
    approval, started, result = _approval_state(log, approval_id) if known else (None, False, None)
    recorded_id = approval_id if approval is not None else None

    if action not in RECOVERY_ACTIONS:
        return _refuse(log, incident_id, action, recorded_id, "unknown_recovery_action")
    if approval is None:
        return _refuse(log, incident_id, action, None, "no_approval")
    if approval["incident_id"] != incident_id:
        return _refuse(log, incident_id, action, recorded_id, "approval_incident_mismatch")
    if approval["action"] != action:
        return _refuse(log, incident_id, action, recorded_id, "approval_action_mismatch")
    incident = log.load().get(incident_id)
    payload = current_payload(incident) if incident is not None else None
    if payload is None or payload_sha256(payload) != approval["payload_sha256"]:
        return _refuse(log, incident_id, action, recorded_id, "approval_payload_mismatch")
    if started:
        if result is None:
            return _refuse(log, incident_id, action, recorded_id, "recovery_outcome_unknown")
        return _refuse(log, incident_id, action, recorded_id, "approval_already_used")

    log.append_event(STARTED, incident_id, approval_id=approval_id, action=action)
    try:
        executor(action, incident_id)
    except Exception:
        outcome = RecoveryOutcome(FAILED, ("recovery_error",))
    else:
        outcome = RecoveryOutcome(EXECUTED)
    log.append_event(RESULT, incident_id, approval_id=approval_id, action=action,
                     status=outcome.status, reason_codes=list(outcome.reason_codes))
    return outcome
