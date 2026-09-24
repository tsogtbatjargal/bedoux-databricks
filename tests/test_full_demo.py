"""Chapter 07's local demonstration (scripts/full_demo.py): runs it and
checks the outcomes the chapter doc and demo script rely on."""

import json

import pytest

from scripts import full_demo
from src.bedoux import generator, quality, routing
from src.bedoux.routing import DISMISS, HUMAN, RUNBOOK


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    return full_demo.run(tmp_path_factory.mktemp("demo") / "incidents.jsonl")


def test_the_gate_refuses_chapter_02s_fault_batch_with_its_live_numbers(demo):
    _, r = demo
    # (total, accepted, quarantined, gate_passed, conserved): the numbers
    # chapter 02's live fault run 330174171866992 recorded.
    assert r["gate"]["leads"] == (500, 336, 164, False, True)
    assert r["gate"]["web_events"] == (2000, 1954, 46, True, True)
    assert r["gate"]["ops_events"] == (365, 357, 8, True, True)
    assert r["gate_passed"] is False and r["gate_failing"] == ["leads"]


def test_routing_flags_the_incident_severe_without_a_model(demo):
    route = demo[1]["route"]
    assert (route.label, route.action, route.severe, route.calls) \
        == ("data_quality", RUNBOOK, True, ())
    assert route.reason_codes == ("gate_failed",)


def test_the_incident_is_on_disk_before_the_first_model_call(demo):
    assert demo[1]["incident_on_disk_first"] is True


def test_three_read_only_tools_run_and_the_report_is_cited(demo):
    _, r = demo
    assert r["tool_calls"] == [("read_gate_status", "ran"),
                               ("read_quarantine_sample", "ran"),
                               ("read_evidence_log", "ran")]
    assert r["outcome"] == "reported" and r["model_calls"] == 4
    assert len(r["citations"]) == 5


def test_approved_recovery_runs_once_per_approval_and_duplicates_nothing(demo):
    _, r = demo
    restore, first, retry_codes, second = r["recovery"]
    assert (restore, first, second) == ("executed", "executed", "executed")
    assert retry_codes == ("approval_already_used",)
    # The reused approval never reached the executor: three approvals,
    # three calls, and the prohibited attempt added none.
    assert r["executor_calls"] == ["restore_lead_invalid_rate", "replay_batch", "replay_batch"]
    again = r["replays"][1]
    assert (again.inserted, again.updated) == (0, 0)
    assert again.unchanged == 490
    assert r["max_copies"] == 1
    assert r["accepted_leads"] == 490 + r["stale"]


def test_leads_accepted_only_in_the_fault_batch_are_not_removed(demo):
    """The documented limit, shown rather than hidden: the merge never
    removes, so these stay in the store after the restore."""
    _, r = demo
    assert r["stale"] > 0
    assert r["accepted_leads"] == r["fault_accepted"] + r["replays"][0].inserted


def test_h07_is_never_dismissed_even_when_every_model_says_healthy(demo):
    for strategy, route in demo[1]["h07"].items():
        assert route.action != DISMISS, strategy
        assert "instruction_in_evidence" in route.reason_codes
    assert demo[1]["h07"][routing.RULES_PLUS_CLASSIFIER].action == HUMAN


def test_export_is_refused_on_the_tool_and_recovery_paths(demo):
    tool_status, tool_codes, approval, recovery_codes, executor_calls = demo[1]["prohibited"]
    assert (tool_status, tool_codes) == ("refused", ("prohibited_action",))
    assert approval.startswith("refused")
    assert recovery_codes == ("prohibited_action",)
    assert executor_calls == 0


def test_the_output_is_deterministic(demo, tmp_path):
    lines, _ = full_demo.run(tmp_path / "incidents.jsonl")
    assert lines == demo[0]


def test_the_output_holds_no_raw_fields_or_instruction_text(demo):
    text = "\n".join(demo[0])
    ids, known = full_demo._campaigns()
    _, quarantined = quality.reconcile(generator.generate_leads(ids, invalid_rate=0.30),
                                       "lead_id", quality.classify_lead, known)
    for row, _reasons in quarantined[:5]:
        assert row["created_ts"] not in text
        assert f"@{row['email_domain']}" not in text and row["email_domain"] not in text
    cases = json.loads((full_demo.Path(full_demo.__file__).resolve().parent.parent
                        / "tests" / "fixtures" / "routing_cases.json").read_text())
    h07 = next(c for c in cases["held_out"] if c["case_id"] == "h07")
    assert h07["fields"]["rows"][0]["message"] not in text
    assert "ignore" not in text.lower()
