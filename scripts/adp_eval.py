"""Track 4 evaluation: incident investigation, defect detection, SQL modernization.

    uv run --locked python scripts/adp_eval.py                 # offline, fake agent
    uv run --locked python scripts/adp_eval.py --write         # also record docs/adp/evaluation-results.md
    uv run --group agents python scripts/adp_eval.py --provider claude --max-usd 5 --cases one-per-defect --write
                                                               # real model; billed, opt-in, hard cap

Three levels, reported separately so one can't hide another:
1. Rules: the deterministic classifier and the detection checks (no model).
2. Agent: the investigation loop with the chosen provider. With the default
   fake, this measures the harness (allowlist, citations, triage routing),
   not model quality.
3. SQL: modernization cases against independent reference queries.
"""

import argparse
import json
import platform
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adp import fakes, generator, investigator, modernize, pipeline  # noqa: E402
from src.adp.budget import Budget  # noqa: E402

MODEL, MAX_TOKENS = "claude-opus-5-5", 16000  # mirrors claude_provider; it imports anthropic
from src.bedoux.incidents import IncidentLog  # noqa: E402

CASES = ROOT / "tests" / "fixtures" / "adp_incident_cases.json"
RESULTS = ROOT / "docs" / "adp" / "evaluation-results.md"
RESULTS_CLAUDE = ROOT / "docs" / "adp" / "evaluation-results-claude.md"


def _primary_incident(case):
    sc = case["scenario"]
    scenario = generator.Scenario(seed=sc["seed"], defect=sc["defect"], defect_day=sc["defect_day"])
    store, days = pipeline.simulate(scenario)
    _, recon, incidents = days[sc["defect_day"]]
    return scenario, store, recon, incidents


def _detected_keys(scenario, store, recon):
    """Which injected keys the deterministic checks surfaced."""
    inj = scenario.injected
    keys = {tuple(map(str, k)) for k in inj["keys"]}
    if not keys:
        return None
    defect = scenario.defect
    if defect in ("bad_unit_price", "invalid_status", "duplicate_key", "null_key"):
        ds = inj["dataset"]
        pk = {"sales.orders": ("order_id",), "sales.order_lines": ("order_id", "line_no"),
              "sales.payments": ("payment_id",)}[ds]
        if defect == "null_key":
            pk = ("order_id",)
        found = {tuple(str(q["raw"].get(c)) for c in pk) for q in store.quarantine.get(ds, [])}
    elif defect in ("duplicate_charge", "missing_payment"):
        r = recon["payments_vs_orders"]
        sample = r["sample_overpaid"] if defect == "duplicate_charge" else r["sample_unpaid"]
        found = {(str(o),) for o in sample}
    elif defect == "late_arrival":
        # Detection here is per business date, the grain of the check.
        hit = bool(recon["source_to_target"]["value_mismatches"] or recon["source_to_target"]["only_in_legacy"])
        return (len(keys), len(keys) if hit else 0)
    else:
        return None
    return (len(keys), len(keys & found))


def select_cases(spec):
    cases = json.loads(CASES.read_text())
    if spec == "all":
        return cases
    if spec == "one-per-defect":
        seen, picked = set(), []
        for c in cases:
            if c["scenario"]["defect"] not in seen:
                seen.add(c["scenario"]["defect"])
                picked.append(c)
        return picked
    wanted = spec.split(",")
    picked = [c for c in cases if c["case_id"] in wanted]
    if len(picked) != len(wanted):
        raise SystemExit(f"unknown case ids in {spec!r}")
    return picked


def run_incidents(provider_factory, log_dir, cases, budget=None):
    rows = []
    for case in cases:
        if budget is not None and budget.spent_usd + Budget.worst_case(MODEL, 40000, MAX_TOKENS) > budget.cap_usd:
            rows.append({"case_id": case["case_id"], "incident_opened": False, "detection": None,
                         "skipped": "budget"})
            continue
        scenario, store, recon, incidents = _primary_incident(case)
        detection = _detected_keys(scenario, store, recon)
        if not incidents:
            rows.append({"case_id": case["case_id"], "incident_opened": False, "detection": detection})
            continue
        ctx = investigator.Context(store, recon)
        provider = provider_factory()
        started = time.monotonic()
        result = investigator.investigate(incidents[0], ctx, provider,
                                          IncidentLog(str(Path(log_dir) / f"{case['case_id']}.jsonl")))
        executed = [c["tool"] for c in result.tool_calls if c["status"] == "ran"]
        rows.append({
            "case_id": case["case_id"], "defect": case["scenario"]["defect"], "incident_opened": True,
            "expected": case["expected_root_cause"], "rule": result.rule_root_cause,
            "model": result.root_cause, "status": result.outcome.status,
            "reason_codes": list(result.outcome.reason_codes), "decision": result.decision,
            "evidence_ok": all(t in executed for t in case["required_evidence"]),
            "forbidden_executed": [t for t in executed if t not in case["allowed_tools"]
                                   or t in case["forbidden_actions"]],
            "refused_calls": sum(c["status"] == "refused" for c in result.tool_calls),
            "cited": result.outcome.status == "reported" and bool(result.outcome.report["citations"]),
            "seconds": round(time.monotonic() - started, 3), "detection": detection,
            "usage": list(getattr(provider, "usage", [])),
        })
    return rows


def run_sql():
    con = modernize.fixture_connection()
    rows = []
    for case in yaml.safe_load(modernize.CASES.read_text()):
        r = modernize.modernize(case["legacy"], case.get("reference"), con)
        rows.append({"case_id": case["id"], "category": case["category"], "status": r["status"],
                     "expected": case["expected_status"], "must_flag": bool(case.get("must_flag")),
                     "rewrites": r["rewrites"], "warnings": [w.split(":")[0] for w in r["warnings"]],
                     "blockers": r["blockers"]})
    return rows


def summarize(inc, sql):
    opened = [r for r in inc if r["incident_opened"]]
    n = len(opened)
    calls = [u for r in opened for u in r["usage"]]
    det = [r["detection"] for r in inc if r["detection"]]
    injected = sum(d[0] for d in det)
    found = sum(d[1] for d in det)
    tokens_in = sum(u["input_tokens"] for r in opened for u in r["usage"])
    tokens_out = sum(u["output_tokens"] for r in opened for u in r["usage"])
    return {
        "incident_cases": len(inc), "incidents_opened": n,
        "rule_root_cause_accuracy": sum(r["rule"] == r["expected"] for r in opened) / n if n else 0,
        "agent_root_cause_accuracy": sum(r["model"] == r["expected"] for r in opened) / n if n else 0,
        "agent_reported": sum(r["status"] == "reported" for r in opened),
        "routed_to_runbook": sum(r["decision"] == investigator.ROUTED for r in opened),
        "required_evidence_present": sum(r["evidence_ok"] for r in opened),
        "final_reports_with_citations": sum(r["cited"] for r in opened),
        "forbidden_tool_executions": sum(len(r["forbidden_executed"]) for r in opened),
        "seeded_defect_rows": injected, "seeded_defect_rows_detected": found,
        "detection_recall": found / injected if injected else 0,
        "sql_cases": len(sql),
        "sql_status_matches_expected": sum(r["status"] == r["expected"] for r in sql),
        "sql_validated": sum(r["status"] == modernize.VALIDATED for r in sql),
        "sql_must_flag_accepted": sum(r["must_flag"] and r["status"] == modernize.VALIDATED for r in sql),
        "input_tokens": tokens_in, "output_tokens": tokens_out,
        "model_calls": len(calls),
        "cost_usd": round(sum(u.get("cost_usd") or 0 for u in calls), 4),
        "mean_seconds_per_call": round(sum(u.get("seconds", 0) for u in calls) / len(calls), 2) if calls else 0,
        "agent_pending": sum(r["status"] != "reported" for r in opened),
        "cases_skipped_for_budget": sum(r.get("skipped") == "budget" for r in inc),
    }


def render(summary, inc, sql, provider_name, command):
    lines = [
        "# Track 4 evaluation results", "",
        "Recorded by `scripts/adp_eval.py`. Regenerate rather than edit by hand.", "",
        f"- Command: `{command}`",
        f"- Recorded: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Environment: Python {platform.python_version()}, local fixtures, no Databricks workspace",
        f"- Provider: `{provider_name}`" + (
            " (deterministic fake: these agent numbers measure the harness, not a model)"
            if provider_name == "fake" else
            " (claude-opus-5-5, effort medium, no server-side fallback, hard spend cap)"), "",
        "## Summary", "", "| Metric | Result |", "|---|---|",
    ]
    lines += [f"| {k} | {round(v, 3) if isinstance(v, float) else v} |" for k, v in summary.items()]
    lines += ["", "## Incident cases", "",
              "| Case | Defect | Expected | Rules | Agent | Decision | Evidence | Cited |",
              "|---|---|---|---|---|---|---|---|"]
    for r in inc:
        if r.get("skipped"):
            lines.append(f"| {r['case_id']} | — | skipped: {r['skipped']} cap | | | | | |")
            continue
        if not r["incident_opened"]:
            lines.append(f"| {r['case_id']} | — | no incident opened | | | | | |")
            continue
        lines.append(f"| {r['case_id']} | {r['defect']} | {r['expected']} | {r['rule']} | {r['model']} | "
                     f"{r['decision']} | {'yes' if r['evidence_ok'] else 'no'} | {'yes' if r['cited'] else 'no'} |")
    lines += ["", "## SQL modernization cases", "",
              "| Case | Category | Status | Expected | Rewrites | Warnings | Blockers |",
              "|---|---|---|---|---|---|---|"]
    for r in sql:
        lines.append(f"| {r['case_id']} | {r['category']} | {r['status']} | {r['expected']} | "
                     f"{', '.join(r['rewrites'])} | {', '.join(r['warnings'])} | {', '.join(r['blockers'])} |")
    lines += ["", "## Limitations", "",
              "- All data is synthetic and generated locally; no live Databricks run is included.",
              "- SQL validation runs on DuckDB after a second transpilation. A difference DuckDB "
              "shares with T-SQL can hide; sql17 was such a case and is now blocked by a hazard rule.",
              "- With the fake provider, agent accuracy equals the fake's playbook by construction.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("fake", "claude"), default="fake")
    parser.add_argument("--write", action="store_true", help=f"write {RESULTS.relative_to(ROOT)}")
    parser.add_argument("--json", action="store_true", help="print raw rows as JSON")
    parser.add_argument("--cases", default="all", help="all | one-per-defect | comma-separated case ids")
    parser.add_argument("--max-usd", type=float, help="hard spend cap; required with --provider claude")
    args = parser.parse_args()

    budget = None
    if args.provider == "claude":
        if not args.max_usd:
            parser.error("--provider claude needs --max-usd")
        from src.adp.claude_provider import ClaudeProvider
        budget = Budget(args.max_usd)
        def factory():
            return ClaudeProvider(budget=budget, fallback=False)
    else:
        factory = fakes.PlaybookAgent

    with tempfile.TemporaryDirectory() as log_dir:
        inc = run_incidents(factory, log_dir, select_cases(args.cases), budget)
    sql = run_sql()
    summary = summarize(inc, sql)
    if args.json:
        print(json.dumps({"summary": summary, "incidents": inc, "sql": sql}, indent=1, default=str))
    else:
        print(json.dumps(summary, indent=1))
    if args.write:
        command = " ".join(["uv run --locked python scripts/adp_eval.py"] + sys.argv[1:])
        out = RESULTS_CLAUDE if args.provider == "claude" else RESULTS
        out.write_text(render(summary, inc, sql, args.provider, command))
        print(f"wrote {out.relative_to(ROOT)}")
    failed = (summary["forbidden_tool_executions"] or summary["sql_must_flag_accepted"]
              or summary["sql_status_matches_expected"] != summary["sql_cases"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
