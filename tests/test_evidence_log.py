from datetime import datetime, timezone

import pytest

from src.bedoux import evidence, evidence_log

RUN_START_MS = 1_779_000_000_000
WRITTEN_TS = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

GATE_STATUS_ROWS = [
    {
        "source": "web_events", "gate_passed": True, "conserved": True,
        "total": 500, "quarantined": 10, "accepted_rows": 490,
        "quarantined_rows": 10, "quarantine_rate": 0.02,
        "_computed_ts": WRITTEN_TS,
    },
    {
        "source": "leads", "gate_passed": True, "conserved": True,
        "total": 300, "quarantined": 5, "accepted_rows": 295,
        "quarantined_rows": 5, "quarantine_rate": 0.0166,
        "_computed_ts": WRITTEN_TS,
    },
]


# ---------------------------------------------------------------------------
# build_evidence_record: shape
# ---------------------------------------------------------------------------


def test_build_record_copies_verdict_and_problems_verbatim():
    record = evidence_log.build_evidence_record(
        GATE_STATUS_ROWS, True, [], RUN_START_MS, WRITTEN_TS
    )
    assert record["passed"] is True
    assert record["problems"] == []
    assert record["run_start_ms"] == RUN_START_MS
    assert record["written_ts"] == WRITTEN_TS


def test_build_record_preserves_failure_verdict_and_problems():
    problems = ["leads: gate_passed is False"]
    record = evidence_log.build_evidence_record(
        GATE_STATUS_ROWS, False, problems, RUN_START_MS, WRITTEN_TS
    )
    assert record["passed"] is False
    assert record["problems"] == problems
    # Must not be the same list object the caller passed in.
    problems.append("mutated after the fact")
    assert record["problems"] == ["leads: gate_passed is False"]


def test_build_record_sorts_sources_by_name():
    record = evidence_log.build_evidence_record(
        GATE_STATUS_ROWS, True, [], RUN_START_MS, WRITTEN_TS
    )
    assert [s["source"] for s in record["sources"]] == ["leads", "web_events"]


def test_build_record_keeps_per_source_counts_and_renames_computed_ts():
    record = evidence_log.build_evidence_record(
        GATE_STATUS_ROWS, True, [], RUN_START_MS, WRITTEN_TS
    )
    leads = next(s for s in record["sources"] if s["source"] == "leads")
    assert leads["total"] == 300
    assert leads["quarantined_rows"] == 5
    assert leads["conserved"] is True
    assert leads["computed_ts"] == WRITTEN_TS


def test_build_record_derives_run_start_ts_from_run_start_ms():
    record = evidence_log.build_evidence_record(
        GATE_STATUS_ROWS, True, [], RUN_START_MS, WRITTEN_TS
    )
    assert record["run_start_ts"] == evidence_log.quality.utc_from_epoch_ms(RUN_START_MS)


# ---------------------------------------------------------------------------
# build_evidence_record: fail closed on a malformed run identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_run_start_ms", [0, -1, "1779000000000", 1.5, None, True])
def test_build_record_rejects_malformed_run_start_ms(bad_run_start_ms):
    with pytest.raises(ValueError):
        evidence_log.build_evidence_record(
            GATE_STATUS_ROWS, True, [], bad_run_start_ms, WRITTEN_TS
        )


@pytest.mark.parametrize(
    "bad_written_ts",
    [datetime(2026, 9, 22, 12, 0, 0), "2026-09-22T12:00:00Z", None, RUN_START_MS],
)
def test_build_record_rejects_naive_or_non_datetime_written_ts(bad_written_ts):
    with pytest.raises(ValueError):
        evidence_log.build_evidence_record(
            GATE_STATUS_ROWS, True, [], RUN_START_MS, bad_written_ts
        )


def test_build_record_rejects_non_list_rows():
    with pytest.raises(ValueError):
        evidence_log.build_evidence_record(None, True, [], RUN_START_MS, WRITTEN_TS)


# ---------------------------------------------------------------------------
# build_evidence_record: a malformed individual source row is recorded, not dropped
# ---------------------------------------------------------------------------


def test_build_record_keeps_a_malformed_source_row_with_nulled_fields():
    rows = GATE_STATUS_ROWS + ["not-a-dict"]
    record = evidence_log.build_evidence_record(rows, True, [], RUN_START_MS, WRITTEN_TS)
    assert len(record["sources"]) == 3
    malformed = next(s for s in record["sources"] if s["source"] is None)
    assert malformed["total"] is None
    assert malformed["computed_ts"] is None


def test_build_record_keeps_a_source_row_missing_some_fields():
    rows = [{"source": "ops_events", "gate_passed": False}]
    record = evidence_log.build_evidence_record(rows, False, ["x"], RUN_START_MS, WRITTEN_TS)
    entry = record["sources"][0]
    assert entry["source"] == "ops_events"
    assert entry["gate_passed"] is False
    assert entry["total"] is None
    assert entry["computed_ts"] is None


# ---------------------------------------------------------------------------
# gate_and_redact: evaluate_evidence_gate's first real caller
# ---------------------------------------------------------------------------


def test_gate_and_redact_passes_a_healthy_record_through():
    record = evidence_log.build_evidence_record(
        GATE_STATUS_ROWS, True, [], RUN_START_MS, WRITTEN_TS
    )
    packet = evidence_log.gate_and_redact(record)
    assert packet["passed"] is True
    assert packet["problems"] == []
    assert packet["run_start_ms"] == RUN_START_MS


def test_gate_and_redact_never_drops_the_row_when_the_evidence_gate_objects():
    # gate_status-derived fields should never trip evaluate_evidence_gate in
    # practice; this plants a canary marker directly to prove the fallback
    # path -- packet still returned, forced to failed, never silently lost.
    record = {
        "run_start_ms": RUN_START_MS,
        "run_start_ts": WRITTEN_TS,
        "written_ts": WRITTEN_TS,
        "passed": True,
        "problems": [f"unexpected: {evidence.CANARY_MARKER}"],
        "sources": [],
    }
    allowed, _ = evidence.evaluate_evidence_gate(record)
    assert allowed is False  # sanity: the fixture actually trips the gate

    packet = evidence_log.gate_and_redact(record)
    assert packet is not None
    assert packet["passed"] is False
    assert packet["run_start_ms"] == RUN_START_MS
    assert any("canary" in p for p in packet["problems"])


def test_gate_and_redact_still_redacts_a_sensitive_field_if_one_ever_appears():
    record = evidence_log.build_evidence_record(
        GATE_STATUS_ROWS, True, [], RUN_START_MS, WRITTEN_TS
    )
    record["ssn"] = "000-00-0000"
    packet = evidence_log.gate_and_redact(record)
    assert packet["ssn"] == evidence.REDACTED
