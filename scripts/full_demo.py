"""Chapter 07: one incident end to end, locally, with fakes only.

    uv run --locked python -m scripts.full_demo

Chapter 02's fault case (leads at 32.8%), through every control chapters
02-06 built, in the order they apply:

  gate refuses -> routing flags it severe -> incident saved before the first
  model call -> read-only tool calls -> a cited report -> human approvals ->
  an approved restore and replay with no duplicates

then two refusals: h07's embedded instruction can't dismiss an incident,
and a prohibited action (export) is refused on the tool and recovery paths.

What is real and what isn't: every decision below is made by the project's
own code (src/bedoux), unchanged. Everything around it is a stand-in. The
batches come from the seeded generator, in memory. The "model" is a scripted
fake: no provider exists in this repo and no real model is called. The tools
read in-memory fixtures built from those batches, not the Databricks tables.
The approvals are recorded by this script on a person's behalf. The
executors change a local variable and an in-memory store, not the workspace.
Nothing here touches the network or Databricks. See
docs/sentinel/chapters/07-full-demo.md for which steps match recorded live
evidence.

The output is deterministic: it prints counts, fixed reason codes, citation
paths and truncated SHA-256 hashes -- never a raw record field, the h07
text, or anything random (incident and approval ids are uuid4, so they
aren't printed).
"""

import hashlib
import json
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.bedoux import generator, incidents, quality, recovery, replay, routing, tools
from src.bedoux.model_call import REPORTED

FAULT_RATE = 0.30     # chapter 02's fault: bedoux_lead_invalid_rate=0.30
RESTORED_RATE = 0.02  # and its restore
APPROVER = "demo-script, standing in for a person"

# A fixed, fictional run boundary, so the gate's freshness check is
# deterministic. Not a real run's time.
RUN_START = datetime(2026, 1, 1, tzinfo=timezone.utc)

H07_ID = "h07"


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _campaigns():
    campaigns = generator.generate_campaigns(
        [c["client_id"] for c in generator.generate_clients()])
    return [c["campaign_id"] for c in campaigns], quality.eligible_campaign_ids(campaigns)


def _gate_row(source, total, quarantined, accepted):
    return {"source": source, "total": total, "quarantined": quarantined,
            "accepted_rows": accepted, "quarantined_rows": quarantined,
            "quarantine_rate": quality.quarantine_rate(total, quarantined),
            "gate_passed": quality.gate_passed(total, quarantined),
            "conserved": accepted + quarantined == total,
            "_computed_ts": RUN_START + timedelta(minutes=3)}


def _batch(lead_rate):
    """Silver's rules over one seeded batch, in pure Python: gate_status
    rows for the three sources, plus the quarantined leads."""
    ids, known = _campaigns()
    leads_ok, leads_q = quality.reconcile(generator.generate_leads(ids, invalid_rate=lead_rate),
                                          "lead_id", quality.classify_lead, known)
    web_ok, web_q = quality.reconcile(generator.generate_web_events(ids), "event_id",
                                      quality.classify_web_event, known)
    ops_ok, ops_q = quality.reconcile(generator.generate_ops_events(), "ops_event_id",
                                      quality.classify_ops_event)
    rows = [_gate_row("leads", len(leads_ok) + len(leads_q), len(leads_q), len(leads_ok)),
            _gate_row("web_events", len(web_ok) + len(web_q), len(web_q), len(web_ok)),
            _gate_row("ops_events", len(ops_ok) + len(ops_q), len(ops_q), len(ops_ok))]
    return rows, [row for row, _reasons in leads_q]


def _evidence(gate_row):
    """The incident's evidence: the failing source's gate_status fields,
    without the timestamp (not JSON)."""
    return {k: v for k, v in gate_row.items() if k != "_computed_ts"}


class ScriptedInvestigator:
    """The fake model. Asks for three read-only tools, then reports with
    citations. On its first call it checks that the incident is already
    on disk -- that's chapter 04's ordering guarantee, observed."""

    def __init__(self, log_path):
        self.log_path = Path(log_path)
        self.calls = 0
        self.incident_on_disk_first = None
        self.responses = [
            {"tool_request": {"tool": "read_gate_status", "args": {"source": "leads"}}},
            {"tool_request": {"tool": "read_quarantine_sample",
                              "args": {"source": "leads", "limit": 3}}},
            {"tool_request": {"tool": "read_evidence_log", "args": {"source": "leads"}}},
            {"summary": "leads quarantined above the threshold; rows were conserved, "
                        "so this is a real rejection, not lost rows",
             "uncertainty": "why the batch lacks campaign references is not in the evidence",
             "proposed_recovery": "restore the lead invalid rate, then replay the batch",
             "citations": ["evidence.quarantine_rate", "evidence.conserved",
                           "tool_results[0].result[0].gate_passed",
                           "tool_results[1].result[0].lead_id",
                           "tool_results[2].result[0].passed"]},
        ]

    def complete(self, payload, *, timeout_s):
        if self.calls == 0:
            events = [json.loads(line) for line in self.log_path.read_text().splitlines()]
            self.incident_on_disk_first = [e["event"] for e in events] == [incidents.OPENED]
        self.calls += 1
        return json.dumps(self.responses[self.calls - 1])


class AlwaysHealthy:
    """A fake classifier/reasoner that is fooled every time: healthy, 0.99."""

    def complete(self, payload, *, timeout_s):
        return json.dumps({"label": "healthy", "confidence": 0.99})


class RecordingExecutor:
    """A recovery executor that acts only on local state: the lead rate
    variable and an in-memory accepted-records store."""

    def __init__(self, store, known, ids):
        self.store, self.known, self.ids = store, known, ids
        self.lead_rate = FAULT_RATE
        self.calls = []
        self.replays = []

    def __call__(self, action, incident_id):
        self.calls.append(action)
        if action == "restore_lead_invalid_rate":
            self.lead_rate = RESTORED_RATE
        elif action == "replay_batch":
            batch = generator.generate_leads(self.ids, invalid_rate=self.lead_rate)
            self.replays.append(replay.replay_batch(batch, self.store, self.known))


def run(log_path):
    """Run the demonstration. Returns (lines, results): the printable lines
    and the outcomes a test checks."""
    lines, r = [], {}
    out = lines.append
    log = incidents.IncidentLog(log_path)

    # 1. Publication gate (chapter 02).
    gate_rows, quarantined_leads = _batch(FAULT_RATE)
    passed, problems = quality.evaluate_gate(gate_rows, min_computed_ts=RUN_START)
    failing = [row["source"] for row in gate_rows if row["gate_passed"] is not True]
    r["gate"] = {row["source"]: (row["total"], row["accepted_rows"], row["quarantined_rows"],
                                 row["gate_passed"], row["conserved"]) for row in gate_rows}
    r["gate_passed"], r["gate_failing"] = passed, failing
    out("1. publication gate (chapter 02)")
    for row in gate_rows:
        out(f"   {row['source']}: {row['total']} total, {row['accepted_rows']} accepted, "
            f"{row['quarantined_rows']} quarantined ({row['quarantine_rate']:.1%}), "
            f"gate_passed={row['gate_passed']}, conserved={row['conserved']}")
    out(f"   gate: {'passed' if passed else 'REFUSED'}; failing sources: {', '.join(failing)}; "
        f"{len(problems)} problem(s); Gold refresh withheld")

    # 2. Routing (chapters 05-06): rules only, so no model is called here.
    fields = _evidence(next(row for row in gate_rows if row["source"] == "leads"))
    decision = routing.route(fields, routing.RULES_ONLY)
    r["route"] = decision
    out("2. routing (chapters 05-06), rules only: no model call")
    out(f"   label={decision.label} action={decision.action} severe={decision.severe} "
        f"codes={','.join(decision.reason_codes)}")

    # 3-5. Incident, read-only tools, cited report (chapter 04).
    fixtures = {
        "gate_status": [_evidence(row) for row in gate_rows],
        "quarantine": {"leads": quarantined_leads},
        # A synthetic stand-in for chapter 03's failing gate_evidence_log
        # record (run 180753859499836), reduced to one source.
        "gate_evidence_log": [{"source": "leads", "passed": False,
                               "gate_passed": fields["gate_passed"],
                               "conserved": fields["conserved"]}],
    }
    model = ScriptedInvestigator(log_path)
    incident_id, outcome = tools.investigate_with_tools(fields, model, log, fixtures)
    incident = log.load()[incident_id]
    r["incident_on_disk_first"] = model.incident_on_disk_first
    r["model_calls"] = model.calls
    r["tool_calls"] = [(c["request"]["tool"], c["status"]) for c in incident.tool_calls]
    r["outcome"] = outcome.status
    r["citations"] = list(outcome.report["citations"]) if outcome.status == REPORTED else []
    out("3. incident (chapter 04)")
    out(f"   opened and fsynced before the first model call: {model.incident_on_disk_first}")
    out(f"   opening payload sha256 {_sha(incident.evidence_payload)}")
    out("4. read-only tools (chapter 04), requested by the fake model")
    for call in incident.tool_calls:
        out(f"   {call['request']['tool']}: {call['status']}, "
            f"payload sha256 {_sha(call['evidence_payload'])}")
    out(f"5. report: {outcome.status}, {model.calls} fake model calls, citations resolved:")
    for citation in r["citations"]:
        out(f"   {citation}")
    out(f"   report sha256 {_sha(json.dumps(outcome.report, sort_keys=True))}")

    # 6-7. Approvals and recovery (chapter 04).
    ids, known = _campaigns()
    store = replay.AcceptedRecords()
    # What the fault run had already accepted, before the gate withheld Gold.
    fault_first = replay.replay_batch(generator.generate_leads(ids, invalid_rate=FAULT_RATE),
                                      store, known)
    executor = RecordingExecutor(store, known, ids)
    reviewed = recovery.payload_sha256(recovery.current_payload(incident))
    out(f"6. approvals, bound to incident + action + payload sha256 {reviewed[:12]}")
    out(f"   before recovery: {len(store.rows())} accepted leads (fault batch)")

    def approve_and_run(action):
        approval_id = recovery.approve_recovery(log, incident_id, action, approver=APPROVER,
                                                payload_sha256=reviewed)
        return approval_id, recovery.execute_recovery(log, incident_id, action,
                                                      approval_id, executor)

    _, restore = approve_and_run("restore_lead_invalid_rate")
    replay_id, first = approve_and_run("replay_batch")
    retry = recovery.execute_recovery(log, incident_id, "replay_batch", replay_id, executor)
    _, second = approve_and_run("replay_batch")
    counts = Counter(row[replay.RECORD_KEY] for row in store.rows())
    r["recovery"] = [restore.status, first.status, retry.reason_codes, second.status]
    r["replays"] = executor.replays
    r["executor_calls"] = list(executor.calls)
    r["fault_accepted"] = fault_first.inserted
    r["accepted_leads"] = len(store.rows())
    r["max_copies"] = max(counts.values())
    restored_ok, _ = quality.reconcile(generator.generate_leads(ids, invalid_rate=RESTORED_RATE),
                                       replay.RECORD_KEY, quality.classify_lead, known)
    r["stale"] = len(set(counts) - {row[replay.RECORD_KEY] for row in restored_ok})
    out("7. recovery (chapter 04), executors act on local state only")
    out(f"   restore_lead_invalid_rate: {restore.status} (lead rate {FAULT_RATE} -> "
        f"{executor.lead_rate})")
    def replay_line(label, outcome_, result):
        out(f"   {label}: {outcome_.status}, inserted={result.inserted} "
            f"updated={result.updated} unchanged={result.unchanged} "
            f"quarantined={result.quarantined}")

    replay_line("replay_batch", first, executor.replays[0])
    out(f"   same approval again: {retry.status} ({','.join(retry.reason_codes)}), "
        "executor not called")
    replay_line("replay_batch, new approval", second, executor.replays[1])
    out(f"   after recovery: {len(store.rows())} accepted leads, "
        f"at most {r['max_copies']} copy of each lead_id")
    out(f"   of those, {r['stale']} were accepted only in the fault batch and stay: "
        "a replay merges, it never removes (known limit)")

    # 8. Refusal: h07's embedded instruction (chapter 06).
    cases = json.loads((Path(__file__).resolve().parent.parent / "tests" / "fixtures"
                        / "routing_cases.json").read_text())
    h07 = next(c for c in cases["held_out"] if c["case_id"] == H07_ID)
    fooled = AlwaysHealthy()
    r["h07"] = {s: routing.route(h07["fields"], s, classifier=fooled, reasoner=fooled)
                for s in routing.STRATEGIES}
    out("8. refusal: h07's embedded instruction (chapter 06); every fake model says healthy")
    for strategy, decision in r["h07"].items():
        out(f"   {strategy}: label={decision.label} action={decision.action} "
            f"codes={','.join(decision.reason_codes)}")

    # 9. Refusal: a prohibited action (chapter 06).
    tool_status, tool_codes, _ = tools.execute_tool_request(
        {"tool": "export_leads", "args": {"source": "leads"}}, fixtures)
    try:
        recovery.approve_recovery(log, incident_id, "export_leads", approver=APPROVER,
                                  payload_sha256=reviewed)
        approval = "recorded"
    except ValueError:
        approval = "refused (ValueError, nothing recorded)"
    calls_before = len(executor.calls)
    prohibited = recovery.execute_recovery(log, incident_id, "export_leads", replay_id, executor)
    r["prohibited"] = (tool_status, tool_codes, approval, prohibited.reason_codes,
                       len(executor.calls) - calls_before)
    out("9. refusal: prohibited action export_leads (chapter 06)")
    out(f"   as a tool: {tool_status} ({','.join(tool_codes)})")
    out(f"   approval: {approval}")
    out(f"   as a recovery, with a real approval id: {prohibited.status} "
        f"({','.join(prohibited.reason_codes)}), executor calls: {r['prohibited'][4]}")

    event_counts = Counter(e["event"] for e in log.events())
    out("incident log events: " + ", ".join(f"{k}={v}" for k, v in sorted(event_counts.items())))
    out("no real model, table, or workspace was touched; see the chapter 07 doc")
    r["events"] = dict(event_counts)
    return lines, r


def main():
    with tempfile.TemporaryDirectory() as tmp:
        lines, _ = run(Path(tmp) / "incidents.jsonl")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
