"""Deterministic stand-ins for a model (Track 4). Tests, CI and the offline
eval use these; none of them is evidence of how a real model behaves.

- PlaybookAgent follows a fixed per-trigger evidence plan and labels from what
  the tools returned. It exists to exercise the loop, the allowlist, the
  citation checks and the eval scoring end to end without a network call.
- ScriptedProvider replays canned responses (adversarial and malformed cases).
"""

import json


class ScriptedProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.payloads = []

    def complete(self, payload, *, timeout_s):
        self.payloads.append(payload)
        if not self.responses:
            raise RuntimeError("script exhausted")
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt if isinstance(nxt, str) else json.dumps(nxt)


def _request(tool, **args):
    return json.dumps({"tool_request": {"tool": tool, "args": args}})


def _report(label, summary, citations, uncertainty="Fixture-only fake; no model judgment."):
    return json.dumps({
        "summary": f"ROOT_CAUSE: {label}\n{summary}",
        "uncertainty": uncertainty,
        "proposed_recovery": "Follow the runbook for this label; a human approves any change.",
        "citations": citations,
    })


class PlaybookAgent:
    """A fake investigator. One call per round; reads its own prior tool
    results from the payload, exactly like a stateless model would."""

    def __init__(self):
        self.calls = 0

    def complete(self, payload, *, timeout_s):
        self.calls += 1
        packet = json.loads(payload)
        inc, results = packet["incident"], packet["tool_results"]
        have = {r["tool"]: (i, r) for i, r in enumerate(results) if r["status"] == "ran"}
        trigger = inc["trigger"]

        if trigger == "no_new_data":
            if "get_dataset_runs" not in have:
                return _request("get_dataset_runs", dataset_id=inc["dataset_id"])
            i, _ = have["get_dataset_runs"]
            return _report("STALE_SOURCE", "The latest run read no new rows.",
                           [f"tool_results[{i}].result"])

        if trigger == "schema_drift_additive":
            if "get_schema_diff" not in have:
                return _request("get_schema_diff", dataset_id=inc["dataset_id"])
            i, _ = have["get_schema_diff"]
            return _report("SCHEMA_COLUMN_ADDED", "The extract carries a column the contract lacks.",
                           [f"tool_results[{i}].result.schema_diff.added"])

        if trigger in ("payments_vs_orders_mismatch", "source_to_target_mismatch"):
            check = "payments_vs_orders" if trigger.startswith("payments") else "source_to_target"
            if "get_reconciliation" not in have:
                return _request("get_reconciliation", check=check)
            i, r = have["get_reconciliation"]
            if check == "source_to_target":
                if "get_dataset_runs" not in have:
                    return _request("get_dataset_runs", dataset_id="sales.payments")
                j, _ = have["get_dataset_runs"]
                return _report("LATE_ARRIVAL_BEYOND_LOOKBACK",
                               "Source has settlements the target never ingested, while runs succeeded.",
                               [f"tool_results[{i}].result.sample_mismatches",
                                f"tool_results[{j}].result"])
            res = r["result"]
            label = "DUPLICATE_CHARGE" if res["overpaid_orders"] > res["unpaid_orders"] else "MISSING_PAYMENT"
            field = "overpaid_orders" if label == "DUPLICATE_CHARGE" else "unpaid_orders"
            return _report(label, f"{res[field]} orders affected.", [f"tool_results[{i}].result.{field}"])

        # ingestion_failed / rows_quarantined
        if "get_pipeline_run" not in have:
            return _request("get_pipeline_run", run_id=inc["run_id"])
        i, run = have["get_pipeline_run"]
        if run["result"]["failure_code"] == "schema_required_column_missing":
            if "get_schema_diff" not in have:
                return _request("get_schema_diff", dataset_id=inc["dataset_id"])
            j, _ = have["get_schema_diff"]
            return _report("SCHEMA_COLUMN_REMOVED", "A required column is missing from the extract.",
                           [f"tool_results[{i}].result.failure_code",
                            f"tool_results[{j}].result.schema_diff.removed_required"])
        if "get_contract_results" not in have:
            return _request("get_contract_results", run_id=inc["run_id"])
        j, cr = have["get_contract_results"]
        if "get_recent_success" not in have:
            return _request("get_recent_success", dataset_id=inc["dataset_id"])
        k, _ = have["get_recent_success"]
        reasons = cr["result"]["quarantine_reasons"]
        totals = {}
        for key, n in reasons.items():
            totals[key.rsplit(":", 1)[1]] = totals.get(key.rsplit(":", 1)[1], 0) + n
        top = max(totals, key=totals.get)
        label = {"cast_failed": "SCHEMA_TYPE_CHANGE", "null_primary_key": "NULL_PRIMARY_KEY",
                 "invalid_enum": "INVALID_DOMAIN_VALUE", "duplicate_key": "DUPLICATE_SOURCE_KEY",
                 "missing_required": "SCHEMA_COLUMN_REMOVED"}[top]
        return _report(label, f"Dominant quarantine reason: {top}.",
                       [f"tool_results[{j}].result.quarantine_reasons",
                        f"tool_results[{k}].result.run"])
