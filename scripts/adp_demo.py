"""Track 4 demo: one incident from a broken source to an approval request,
then one legacy SQL migration. Local and deterministic.

    uv run --locked python scripts/adp_demo.py
    uv run --locked python scripts/adp_demo.py --defect late_arrival
    uv run --group agents python scripts/adp_demo.py --provider claude   # billed, opt-in

What's real: every decision is made by src/adp code (ingestion, contracts,
reconciliation, rules classification, triage, runbook selection, SQL
validation). What's a stand-in: the source (seeded generator), the store (in
memory) and, by default, the model (fakes.PlaybookAgent). Nothing touches
Databricks. The same engine runs in the workspace through src/adp/ingest_task.py.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adp import fakes, generator, investigator, modernize, pipeline, runbooks  # noqa: E402
from src.bedoux.incidents import IncidentLog  # noqa: E402

LEGACY = """SELECT TOP 3 c.customer_id, LEN(c.name) AS name_len,
       'C-' + CAST(c.customer_id AS VARCHAR(10)) AS code,
       SUM(l.quantity * l.unit_price) AS revenue
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
JOIN order_lines l ON l.order_id = o.order_id
WHERE ISNULL(o.status, 'unknown') IN ('paid', 'shipped')
GROUP BY c.customer_id, c.name
ORDER BY revenue DESC, c.customer_id"""

REFERENCE = """SELECT c.customer_id, length(rtrim(c.name)) AS name_len,
       'C-' || CAST(c.customer_id AS VARCHAR) AS code, sum(l.quantity * l.unit_price) AS revenue
FROM customers c JOIN orders o USING (customer_id) JOIN order_lines l USING (order_id)
WHERE coalesce(o.status, 'unknown') IN ('paid', 'shipped')
GROUP BY c.customer_id, c.name ORDER BY revenue DESC, c.customer_id LIMIT 3"""


def section(title):
    print(f"\n== {title} " + "=" * max(0, 66 - len(title)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--defect", default="bad_unit_price", choices=generator.DEFECTS)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--provider", choices=("fake", "claude"), default="fake")
    args = parser.parse_args()

    section(f"1. Three source days, defect '{args.defect}' injected on day 3")
    store, days = pipeline.simulate(generator.Scenario(seed=args.seed, defect=args.defect))
    for day, (records, _, incidents) in days.items():
        for r in records:
            print(f"day{day} {r['dataset_id']:18} {r['status']:26} new={r['rows_new']:<4} "
                  f"ins={r['inserted']:<4} upd={r['updated']:<4} quarantined={r['quarantined']}")
        for i in incidents:
            print(f"     incident: {i['trigger']} on {i['dataset_id']}")
    records, recon, incidents = days[3]
    if not incidents:
        print("No incident opened.")
        return 0

    section("2. Investigation (read-only tools, guarded model path)")
    if args.provider == "claude":
        from src.adp.claude_provider import ClaudeProvider
        provider = ClaudeProvider()
    else:
        provider = fakes.PlaybookAgent()
        print("provider: deterministic fake (not a model)")
    with tempfile.TemporaryDirectory() as tmp:
        log = IncidentLog(str(Path(tmp) / "incidents.jsonl"))
        result = investigator.investigate(incidents[0], investigator.Context(store, recon), provider, log)
        for c in result.tool_calls:
            print(f"tool {c['tool']}({json.dumps(c['args'])}) -> {c['status']} {c['reason_codes'] or ''}")
        print(f"outcome: {result.outcome.status} {list(result.outcome.reason_codes)}")
        if result.outcome.report:
            print("report:", result.outcome.report["summary"].replace("\n", " | "))
            print("citations:", result.outcome.report["citations"])
        print(f"model label: {result.root_cause}   rules label: {result.rule_root_cause}")
        print(f"triage: {result.decision} {list(result.decision_reasons)}")

        section("3. Remediation proposal (approval gate; nothing is applied)")
        request = runbooks.request_approval(log, result)
        print(f"status: {request['status']}\naction: {request['action']}")
        for v in request["validations"]:
            print(f"  must pass: {v}")
        print(f"incident log events: {[e['event'] for e in log.events()]}")

    section("4. Legacy T-SQL modernization")
    report = modernize.modernize(LEGACY, REFERENCE, modernize.fixture_connection())
    print(report["databricks_sql"])
    print(f"status: {report['status']} rows={report.get('rows_compared')}  rewrites={report['rewrites']}"
          f"  warnings={[w.split(':')[0] for w in report['warnings']]}")
    print(f"limitation: {report['limitation']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
