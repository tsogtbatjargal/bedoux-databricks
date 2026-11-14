"""Remediation proposals and the approval gate (Track 4).

A proposal is text plus the validations that must pass. Nothing here executes
a change: `request_approval` records an approval request in the incident log
and returns it. Applying a change, replaying quarantine or deploying is a
human action outside this package (ADR 0009).

Runbooks are keyed by the rules-based label, not the model's, so a persuasive
but wrong report can't pick the remediation.
"""

RUNBOOKS = {
    "SCHEMA_TYPE_CHANGE": {
        "action": "Keep malformed rows in quarantine with raw payloads; ask the source owner to "
                  "restore the declared type. Replay quarantine after the fix. Never cast to zero.",
        "validations": ["quarantined rows are accounted for (window = accepted + quarantined)",
                        "no silent conversion: affected column has no zero/null substitutes",
                        "source_to_target reconciliation passes after replay"],
    },
    "SCHEMA_COLUMN_REMOVED": {
        "action": "Hold the dataset (watermark stays). Confirm with the source owner whether the "
                  "removal is intended; if so, version the contract and its consumers together.",
        "validations": ["watermark unchanged since the failed run", "contract version bumped if accepted"],
    },
    "SCHEMA_COLUMN_ADDED": {
        "action": "No data impact. Review whether the new column belongs in the contract; add it in "
                  "a contract PR if consumers need it.",
        "validations": ["contract tests pass with the column declared optional"],
    },
    "NULL_PRIMARY_KEY": {
        "action": "Quarantine keyless rows; ask the source owner for keyed re-delivery.",
        "validations": ["no keyless rows in the target", "re-delivered rows merge without duplicates"],
    },
    "INVALID_DOMAIN_VALUE": {
        "action": "Confirm whether the new value is a legitimate status. If so, extend the enum in a "
                  "contract PR and replay quarantine; otherwise the source fixes the data.",
        "validations": ["enum change reviewed by the data product owner", "replay creates no duplicates"],
    },
    "DUPLICATE_SOURCE_KEY": {
        "action": "Both versions stay quarantined. The source must say which version is correct.",
        "validations": ["exactly one version per key after re-delivery"],
    },
    "DUPLICATE_CHARGE": {
        "action": "Report the overpaid orders to finance with payment ids. Do not delete payments "
                  "from the lakehouse; refunds happen in the source system.",
        "validations": ["payments_vs_orders passes after source correction"],
    },
    "MISSING_PAYMENT": {
        "action": "List paid orders without settlements for the payments team; request the missing "
                  "settlement rows (or tombstones) from the provider.",
        "validations": ["unpaid_orders = 0 or every remaining order has a ticket"],
    },
    "STALE_SOURCE": {
        "action": "Check the extract schedule and source connectivity. Do not move the watermark.",
        "validations": ["next run reads new rows", "watermark unchanged meanwhile"],
    },
    "LATE_ARRIVAL_BEYOND_LOOKBACK": {
        "action": "Run a bounded backfill for the affected business dates (the merge is idempotent), "
                  "then review whether lookback_hours fits the source's real delivery delay.",
        "validations": ["source_to_target passes for affected dates", "backfill creates no duplicates"],
    },
}


def propose(rule_root_cause):
    runbook = RUNBOOKS.get(rule_root_cause)
    if runbook is None:
        return {"root_cause": rule_root_cause, "action": "No runbook; human triage required.",
                "validations": []}
    return {"root_cause": rule_root_cause, **runbook}


def request_approval(log, investigation):
    """Record an approval request; returns it. Status is always 'awaiting_approval'."""
    proposal = propose(investigation.rule_root_cause)
    request = {"status": "awaiting_approval", "decision": investigation.decision,
               "decision_reasons": list(investigation.decision_reasons), **proposal}
    log.append_event("approval_requested", investigation.incident_id, **request)
    return request
