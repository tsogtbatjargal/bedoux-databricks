"""Agent A: pipeline incident investigator (Track 4).

Starts from an incident the deterministic monitor opened (pipeline.py), asks
for read-only evidence through a fixed tool allowlist, and returns a cited
report naming one root-cause label. The report is checked by code before
anyone sees it:

- Every outbound packet goes through Sentinel's guarded path
  (bedoux.model_call.prepare_payload / send_payload): redaction, canary and
  leak checks, citation resolution, fixed reason codes.
- Tool names are compared against ALLOWED_TOOLS and screened by
  bedoux.boundaries.is_prohibited first. Nothing a model returns can add a
  tool, and none of the tools write.
- The model's label is compared with a rules-based classification
  (classify()). Disagreement, a missing label, or instruction-like text in the
  evidence sends the incident to a human instead of to a runbook.
- The loop is bounded (MAX_TOOL_CALLS, refused calls included).

The provider is injected. Tests and CI use fakes (fakes.py); the opt-in Claude
adapter is claude_provider.py.
"""

import json
from dataclasses import dataclass, field

from . import contracts, ingest
from ._compat import sibling

model_call = sibling("bedoux.model_call")
boundaries = sibling("bedoux.boundaries")

MAX_TOOL_CALLS = 5
MAX_SAMPLE_ROWS = 5

ROOT_CAUSES = (
    "SCHEMA_TYPE_CHANGE",          # values in a typed column stopped casting
    "SCHEMA_COLUMN_REMOVED",       # a required column is gone from the extract
    "SCHEMA_COLUMN_ADDED",         # additive drift; nothing broke yet
    "NULL_PRIMARY_KEY",
    "INVALID_DOMAIN_VALUE",        # enum value outside the contract
    "DUPLICATE_SOURCE_KEY",        # same key and cursor, different content
    "DUPLICATE_CHARGE",            # more paid than the order total
    "MISSING_PAYMENT",             # paid order with no settlement row
    "STALE_SOURCE",                # extract delivered nothing new
    "LATE_ARRIVAL_BEYOND_LOOKBACK",  # source rows older than watermark - lookback
)

NEEDS_HUMAN = "needs_human_triage"
ROUTED = "routed_to_runbook"


# -- read-only tools ------------------------------------------------------

@dataclass
class Context:
    """Everything the tools may read: the metadata store and that day's
    reconciliation reports. Tools get this object, never a workspace client."""
    store: ingest.MetadataStore
    recon: dict


def get_pipeline_run(ctx, run_id):
    run = ctx.store.run(run_id)
    if run is None:
        raise KeyError(run_id)
    return run


def get_schema_diff(ctx, dataset_id):
    runs = ctx.store.runs_for(dataset_id)
    if not runs:
        raise KeyError(dataset_id)
    return {"latest_run_id": runs[-1]["run_id"], "schema_diff": runs[-1]["schema_diff"],
            "last_accepted_columns": ctx.store.schemas.get(dataset_id)}


def get_contract_results(ctx, run_id, limit=MAX_SAMPLE_ROWS):
    run = get_pipeline_run(ctx, run_id)
    sample = [q for q in ctx.store.quarantine.get(run["dataset_id"], []) if q["run_id"] == run_id]
    return {"run_id": run_id, "quarantined": run["quarantined"],
            "rows_in_window": run["rows_in_window"],
            "quarantine_reasons": run["quarantine_reasons"],
            "sample": [{"raw": q["raw"], "problems": q["problems"]} for q in sample[:limit]]}


def get_recent_success(ctx, dataset_id):
    ok = [r for r in ctx.store.runs_for(dataset_id) if r["status"] != ingest.FAILED]
    if not ok:
        return {"dataset_id": dataset_id, "run": None}
    r = ok[-1]
    return {"dataset_id": dataset_id, "run": {k: r[k] for k in (
        "run_id", "status", "rows_new", "quarantined", "quarantine_reasons", "watermark_after")}}


def get_dataset_runs(ctx, dataset_id):
    return [{k: r[k] for k in ("run_id", "status", "rows_in_source", "rows_new", "failure_code")}
            for r in ctx.store.runs_for(dataset_id)[-3:]]


def get_reconciliation(ctx, check):
    if check not in ctx.recon:
        raise KeyError(check)
    return ctx.recon[check]


TOOLS = {
    # name: (implementation, required args, optional args, description)
    "get_pipeline_run": (get_pipeline_run, {"run_id": str}, {},
                         "Audit record of one ingestion run."),
    "get_schema_diff": (get_schema_diff, {"dataset_id": str}, {},
                        "Columns added/removed in the latest extract vs the contract."),
    "get_contract_results": (get_contract_results, {"run_id": str}, {"limit": int},
                             "Quarantine reason counts and up to 5 raw rejected rows."),
    "get_recent_success": (get_recent_success, {"dataset_id": str}, {},
                           "The most recent non-failed run of a dataset."),
    "get_dataset_runs": (get_dataset_runs, {"dataset_id": str}, {},
                         "Last three runs of a dataset: status, rows read, rows new."),
    "get_reconciliation": (get_reconciliation, {"check": str}, {},
                           "check = source_to_target | payments_vs_orders."),
}
ALLOWED_TOOLS = frozenset(TOOLS)


def _args_ok(tool, args):
    _, required, optional, _ = TOOLS[tool]
    if not set(required) <= set(args) <= set(required) | set(optional):
        return False
    kinds = {**required, **optional}
    if not all(isinstance(v, kinds[k]) and not isinstance(v, bool) for k, v in args.items()):
        return False
    return 1 <= args.get("limit", 1) <= MAX_SAMPLE_ROWS


def execute_tool(request, ctx):
    """(status, reason_codes, result). Prohibited names are refused first,
    then anything not allowlisted; exception text is discarded."""
    tool, args = request["tool"], request["args"]
    if boundaries.is_prohibited(tool):
        return "refused", (boundaries.PROHIBITED_ACTION,), None
    if tool not in ALLOWED_TOOLS:
        return "refused", ("tool_not_allowed",), None
    if not _args_ok(tool, args):
        return "refused", ("invalid_tool_args",), None
    try:
        return "ran", (), json.loads(json.dumps(TOOLS[tool][0](ctx, **args), default=str))
    except Exception:
        return "failed", ("tool_error",), None


# -- rules-based classification (the reference the model is checked against)

def classify(incident, ctx):
    """Deterministic root cause from the store and reconciliation alone."""
    trigger = incident["trigger"]
    if trigger == "no_new_data":
        return "STALE_SOURCE"
    if trigger == "schema_drift_additive":
        return "SCHEMA_COLUMN_ADDED"
    if trigger == "payments_vs_orders_mismatch":
        r = ctx.recon["payments_vs_orders"]
        return "DUPLICATE_CHARGE" if r["overpaid_orders"] > r["unpaid_orders"] else "MISSING_PAYMENT"
    if trigger == "source_to_target_mismatch":
        return "LATE_ARRIVAL_BEYOND_LOOKBACK"
    run = ctx.store.run(incident["run_id"])
    if run["failure_code"] == ingest.SCHEMA_REQUIRED_COLUMN_MISSING:
        return "SCHEMA_COLUMN_REMOVED"
    reasons = {}
    for key, n in run["quarantine_reasons"].items():
        reason = key.rsplit(":", 1)[1]
        reasons[reason] = reasons.get(reason, 0) + n
    top = max(reasons, key=reasons.get) if reasons else None
    return {
        contracts.CAST_FAILED: "SCHEMA_TYPE_CHANGE",
        contracts.NULL_PRIMARY_KEY: "NULL_PRIMARY_KEY",
        contracts.INVALID_ENUM: "INVALID_DOMAIN_VALUE",
        contracts.DUPLICATE_KEY: "DUPLICATE_SOURCE_KEY",
        contracts.MISSING_REQUIRED: "SCHEMA_COLUMN_REMOVED",
    }.get(top)


# -- the bounded investigation loop ---------------------------------------

@dataclass
class Investigation:
    incident_id: str
    outcome: object                 # model_call.CallOutcome
    root_cause: str | None          # parsed from the report, None if absent/unknown
    rule_root_cause: str | None
    decision: str                   # ROUTED or NEEDS_HUMAN
    decision_reasons: tuple
    tool_calls: list = field(default_factory=list)  # [{tool, args, status, reason_codes}]


def _packet(incident, tool_results):
    return {
        "incident": incident,
        "root_cause_labels": list(ROOT_CAUSES),
        "available_tools": {n: {"args": {**{a: t.__name__ for a, t in spec[1].items()},
                                         **{a: t.__name__ + "?" for a, t in spec[2].items()}},
                                "description": spec[3]} for n, spec in sorted(TOOLS.items())},
        "tool_results": tool_results,
    }


def parse_root_cause(report):
    """The summary must start with 'ROOT_CAUSE: <LABEL>'."""
    if not report:
        return None
    head = report["summary"].strip().split("\n", 1)[0]
    if not head.upper().startswith("ROOT_CAUSE:"):
        return None
    label = head.split(":", 1)[1].strip().split()[0].strip(".,;") if ":" in head else ""
    return label if label in ROOT_CAUSES else None


def investigate(incident, ctx, provider, log, *, timeout_s=60.0, max_tool_calls=MAX_TOOL_CALLS):
    tool_results, calls = [], []
    instruction_seen = False
    payload, codes = model_call.prepare_payload(_packet(incident, tool_results))
    incident_id = log.open_incident(payload.text if payload is not None else None)
    rule = classify(incident, ctx)

    def finish(outcome, extra_reasons=()):
        log.record_outcome(incident_id, outcome)
        label = parse_root_cause(outcome.report) if outcome.status == model_call.REPORTED else None
        reasons = list(extra_reasons)
        if outcome.status != model_call.REPORTED:
            reasons.append(f"outcome_{outcome.status}")
        elif label is None:
            reasons.append("no_root_cause_label")
        elif label != rule:
            reasons.append("disagrees_with_rules")
        if instruction_seen:
            reasons.append(boundaries.INSTRUCTION_IN_EVIDENCE)
        decision = NEEDS_HUMAN if reasons else ROUTED
        log.append_event("triage_decision", incident_id, decision=decision,
                         reasons=reasons, model_root_cause=label, rule_root_cause=rule)
        return Investigation(incident_id, outcome, label, rule, decision, tuple(reasons), calls)

    if payload is None:
        return finish(model_call.CallOutcome(model_call.BLOCKED, codes))

    while True:
        outcome = model_call.send_payload(payload, provider, timeout_s=timeout_s,
                                          accept_tool_requests=True)
        if outcome.status != model_call.TOOL_REQUESTED:
            return finish(outcome)
        request = outcome.tool_request
        if len(calls) >= max_tool_calls:
            log.record_tool_call(incident_id, request, "not_run", ("tool_limit_reached",))
            calls.append({**request, "status": "not_run", "reason_codes": ["tool_limit_reached"]})
            return finish(model_call.CallOutcome(model_call.PENDING, ("tool_limit_reached",)))
        status, codes, result = execute_tool(request, ctx)
        calls.append({**request, "status": status, "reason_codes": list(codes)})
        if result is not None and boundaries.instruction_signals(result):
            instruction_seen = True
        entry = {"tool": request["tool"], "args": request["args"], "status": status,
                 "reason_codes": list(codes), "result": result}
        next_payload, gate_codes = model_call.prepare_payload(_packet(incident, tool_results + [entry]))
        if next_payload is None:
            log.record_tool_call(incident_id, request, "blocked", gate_codes)
            return finish(model_call.CallOutcome(model_call.PENDING, ("tool_result_blocked",) + gate_codes))
        tool_results.append(entry)
        payload = next_payload
        log.record_tool_call(incident_id, request, status, codes, payload.text)
