"""Read-only investigation tools and a bounded tool loop (chapter 04, step 4).

Three tools, all reading local synthetic fixtures passed in by the caller --
never the workspace:

- read_gate_status(source): that source's gate_status rows.
- read_quarantine_sample(source, limit=5): up to 5 quarantined rows;
  a limit outside 1..5 is refused.
- read_evidence_log(source): that source's gate_evidence_log rows.

Which tools may run is decided here, in code: ALLOWED_TOOLS is a fixed
frozenset. A request for anything else -- restore, replay, deploy, write,
delete, or a name that merely looks like an allowed one -- is refused with
`tool_not_allowed` and never executed. The request is still recorded, as
evidence. Nothing a model returns can add to the allowlist: the name is
only ever compared against it, never looked up with getattr/globals.

Every tool result is new evidence going to the model, so it goes back
through model_call.prepare_payload -- the same gate and final check as the
first payload -- before it's sent. A result carrying the canary or a
copied secret stops the investigation (`tool_result_blocked`).

The loop is bounded: at most MAX_TOOL_CALLS tool calls per investigation,
counting refused ones; a request past that stops it as PENDING
(`tool_limit_reached`).
"""

from . import model_call
from .model_call import BLOCKED, PENDING, TOOL_REQUESTED, CallOutcome

MAX_TOOL_CALLS = 3
MAX_SAMPLE_ROWS = 5

# Tool-call statuses, as recorded in the incident log.
RAN = "ran"            # executed; result passed the gate and was sent
REFUSED = "refused"    # not executed (not allowed, or bad arguments)
FAILED = "failed"      # executed and raised; nothing sent
BLOCKED_RESULT = "blocked"  # executed; result failed the gate and was not sent
NOT_RUN = "not_run"    # over the call limit


def read_gate_status(fixtures, source):
    return [row for row in fixtures.get("gate_status", []) if row.get("source") == source]


def read_quarantine_sample(fixtures, source, limit=MAX_SAMPLE_ROWS):
    # _args_ok has already refused a limit outside 1..MAX_SAMPLE_ROWS.
    return list(fixtures.get("quarantine", {}).get(source, []))[:limit]


def read_evidence_log(fixtures, source):
    return [row for row in fixtures.get("gate_evidence_log", []) if row.get("source") == source]


ALLOWED_TOOLS = frozenset({"read_gate_status", "read_quarantine_sample", "read_evidence_log"})
# name -> (required args, optional args), each {arg: type}
_ARGS = {
    "read_gate_status": ({"source": str}, {}),
    "read_quarantine_sample": ({"source": str}, {"limit": int}),
    "read_evidence_log": ({"source": str}, {}),
}
IMPLEMENTATIONS = {
    "read_gate_status": read_gate_status,
    "read_quarantine_sample": read_quarantine_sample,
    "read_evidence_log": read_evidence_log,
}


def _args_ok(tool, args):
    required, optional = _ARGS[tool]
    if not set(required) <= set(args) <= set(required) | set(optional):
        return False
    kinds = {**required, **optional}
    # bool is an int subclass; don't let `true` pass as a limit.
    if not all(isinstance(v, kinds[k]) and not isinstance(v, bool) for k, v in args.items()):
        return False
    # A negative limit would slice from the end ("rows[:-1]" is all but one
    # row), bypassing the cap; refuse anything outside 1..MAX_SAMPLE_ROWS.
    return 1 <= args.get("limit", 1) <= MAX_SAMPLE_ROWS


def execute_tool_request(request, fixtures, implementations=IMPLEMENTATIONS):
    """Return (status, reason_codes, result). The allowlist is checked
    first and alone decides whether anything runs: `implementations` may
    hold other callables (tests pass a recording recovery tool), and they
    are unreachable unless their name is in ALLOWED_TOOLS."""
    tool, args = request["tool"], request["args"]
    if tool not in ALLOWED_TOOLS:
        return REFUSED, ("tool_not_allowed",), None
    if not _args_ok(tool, args):
        return REFUSED, ("invalid_tool_args",), None
    try:
        return RAN, (), implementations[tool](fixtures, **args)
    except Exception:
        return FAILED, ("tool_error",), None  # exception text discarded


def _packet(fields, tool_results):
    return {"evidence": fields, "available_tools": sorted(ALLOWED_TOOLS),
            "tool_results": tool_results}


def investigate_with_tools(fields, provider, log, fixtures, *, timeout_s=30.0,
                           max_tool_calls=MAX_TOOL_CALLS, implementations=IMPLEMENTATIONS):
    """Like incidents.investigate, but the provider may ask for tools.

    Each round sends one CheckedPayload: the original evidence plus every
    tool result so far, all gated together by prepare_payload. Citations in
    the final report resolve against that last payload, so a report can
    cite a tool result (`tool_results[0].result[0].stage`).

    Each tool call is recorded in the incident log: the request, its status
    and codes, and -- only if it passed the gate -- the checked payload that
    carried its result. Never raw fields or a raw result.
    Returns (incident_id, CallOutcome).
    """
    tool_results = []
    payload, codes = model_call.prepare_payload(_packet(fields, tool_results))
    incident_id = log.open_incident(payload.text if payload is not None else None)
    if payload is None:
        outcome = CallOutcome(BLOCKED, codes)
        log.record_outcome(incident_id, outcome)
        return incident_id, outcome

    calls = 0
    while True:
        outcome = model_call.send_payload(payload, provider, timeout_s=timeout_s,
                                          accept_tool_requests=True)
        if outcome.status != TOOL_REQUESTED:
            break
        request = outcome.tool_request
        if calls >= max_tool_calls:
            log.record_tool_call(incident_id, request, NOT_RUN, ("tool_limit_reached",))
            outcome = CallOutcome(PENDING, ("tool_limit_reached",))
            break
        calls += 1
        status, codes, result = execute_tool_request(request, fixtures, implementations)
        entry = {"tool": request["tool"], "args": request["args"], "status": status,
                 "reason_codes": list(codes), "result": result}
        next_payload, gate_codes = model_call.prepare_payload(
            _packet(fields, tool_results + [entry]))
        if next_payload is None:
            log.record_tool_call(incident_id, request, BLOCKED_RESULT, gate_codes)
            outcome = CallOutcome(PENDING, ("tool_result_blocked",) + gate_codes)
            break
        tool_results.append(entry)
        payload = next_payload
        log.record_tool_call(incident_id, request, status, codes, payload.text)

    log.record_outcome(incident_id, outcome)
    return incident_id, outcome
