"""Publication-gate POLICY tests (chapter 02).

Scope and limits -- read this before citing these tests as evidence.

These exercise `quality.evaluate_gate`, the pure decision function that
`src/bedoux/gate_check.py` runs as `bedoux_gate_task`. They prove what the
policy decides given a set of gate_status rows. They do NOT prove:

  - that Spark/DLT produces those rows correctly (no Spark here),
  - that the job graph actually stops Gold when the task fails,
  - that a withheld Gold table really retains its previous content,
  - that any of this runs on Databricks Free Edition serverless.

All four of those need a live pipeline run, which has never happened for this
chapter -- see docs/sentinel/chapters/02-quality-gate.md. Nothing in this file
is runtime evidence.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.bedoux import quality

RUN_START = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
DURING_RUN = RUN_START + timedelta(seconds=30)
BEFORE_RUN = RUN_START - timedelta(hours=6)


def _row(source, passed=True, rate=0.02, computed=DURING_RUN):
    return {
        "source": source,
        "gate_passed": passed,
        "quarantine_rate": rate,
        "total": 500,
        "quarantined": 10,
        "_computed_ts": computed,
    }


def _all_good():
    return [_row(s) for s in quality.REQUIRED_SOURCES]


# ---------------------------------------------------------------------------
# Normal input
# ---------------------------------------------------------------------------


def test_normal_input_publishes():
    passed, problems = quality.evaluate_gate(_all_good(), min_computed_ts=RUN_START)
    assert passed is True
    assert problems == []


def test_row_computed_exactly_at_run_start_is_fresh_enough():
    rows = [_row(s, computed=RUN_START) for s in quality.REQUIRED_SOURCES]
    passed, _ = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is True


def test_unrelated_extra_source_does_not_block_publication():
    rows = _all_good() + [_row("some_future_source", passed=False, rate=0.9)]
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is True, problems


# ---------------------------------------------------------------------------
# Failed gate
# ---------------------------------------------------------------------------


def test_one_failing_source_withholds_everything():
    rows = _all_good()
    rows[0] = _row(quality.REQUIRED_SOURCES[0], passed=False, rate=0.31)
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False
    assert len(problems) == 1
    assert "gate_passed is false" in problems[0]
    assert "31.0%" in problems[0]


def test_every_failing_source_is_reported_not_just_the_first():
    rows = [_row(s, passed=False, rate=0.5) for s in quality.REQUIRED_SOURCES]
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False
    assert len(problems) == len(quality.REQUIRED_SOURCES)


# ---------------------------------------------------------------------------
# Missing / null / ambiguous evidence -- the fail-closed cases. The earlier
# in-dataset implementation treated every one of these as a pass.
# ---------------------------------------------------------------------------


def test_missing_source_row_is_not_a_pass():
    rows = [_row(s) for s in quality.REQUIRED_SOURCES[1:]]
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False
    assert "no gate_status row" in problems[0]


def test_completely_empty_gate_status_is_not_a_pass():
    passed, problems = quality.evaluate_gate([], min_computed_ts=RUN_START)
    assert passed is False
    assert len(problems) == len(quality.REQUIRED_SOURCES)


def test_null_gate_passed_is_not_a_pass():
    rows = _all_good()
    rows[1] = _row(quality.REQUIRED_SOURCES[1], passed=None)
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False
    assert "null" in problems[0]


def test_duplicate_rows_for_one_source_are_ambiguous_not_a_pass():
    rows = _all_good() + [_row(quality.REQUIRED_SOURCES[0])]
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False
    assert "expected exactly 1" in problems[0]


def test_duplicate_rows_fail_even_when_both_say_passed():
    rows = [_row(s) for s in quality.REQUIRED_SOURCES] + [_row(quality.REQUIRED_SOURCES[2])]
    passed, _ = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False


# ---------------------------------------------------------------------------
# Run binding: evidence must describe the batch being published
# ---------------------------------------------------------------------------


def test_stale_gate_status_from_an_earlier_run_is_rejected():
    rows = [_row(s, computed=BEFORE_RUN) for s in quality.REQUIRED_SOURCES]
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False
    assert all("stale evidence" in p for p in problems)


def test_stale_but_passing_evidence_still_withholds():
    rows = [_row(s, passed=True, computed=BEFORE_RUN) for s in quality.REQUIRED_SOURCES]
    passed, _ = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False


def test_null_computed_ts_cannot_prove_freshness():
    rows = [_row(s, computed=None) for s in quality.REQUIRED_SOURCES]
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False
    assert all("_computed_ts is null" in p for p in problems)


def test_without_a_run_boundary_publication_is_blocked():
    rows = [_row(s, computed=BEFORE_RUN) for s in quality.REQUIRED_SOURCES]
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=None)
    assert passed is False
    assert "run boundary" in problems[0]


@pytest.mark.parametrize("boundary", ["2026-09-21", RUN_START.replace(tzinfo=None)])
def test_invalid_or_naive_run_boundary_withholds(boundary):
    assert quality.evaluate_gate(_all_good(), min_computed_ts=boundary)[0] is False


@pytest.mark.parametrize("computed", ["2026-09-21", DURING_RUN.replace(tzinfo=None)])
def test_invalid_or_naive_evidence_timestamp_withholds(computed):
    rows = [_row(s, computed=computed) for s in quality.REQUIRED_SOURCES]
    assert quality.evaluate_gate(rows, min_computed_ts=RUN_START)[0] is False


def test_timezone_offsets_compare_the_same_instant():
    local = DURING_RUN.astimezone(timezone(timedelta(hours=-6)))
    rows = [_row(s, computed=local) for s in quality.REQUIRED_SOURCES]
    assert quality.evaluate_gate(rows, min_computed_ts=RUN_START)[0] is True


def test_empty_required_sources_cannot_authorize_publication():
    assert quality.evaluate_gate([], required_sources=(), min_computed_ts=RUN_START)[0] is False


@pytest.mark.parametrize("value", [None, "", "{{job.start_time.timestamp_ms}}", "NaN", "1.5", -1, 0, True, "9" * 40])
def test_invalid_epoch_milliseconds_are_rejected(value):
    with pytest.raises(ValueError):
        quality.utc_from_epoch_ms(value)


def test_epoch_milliseconds_produce_explicit_utc():
    milliseconds = int(RUN_START.timestamp() * 1000)
    assert quality.utc_from_epoch_ms(str(milliseconds)) == RUN_START
    assert quality.utc_from_epoch_ms(milliseconds).tzinfo is timezone.utc


# ---------------------------------------------------------------------------
# First run with a failing gate
# ---------------------------------------------------------------------------


def test_first_run_failure_still_fails_so_nothing_is_published():
    # The old in-dataset gate published fresh rejected data here, because no
    # previous Gold version existed to fall back to. The policy has no such
    # branch: a failing gate fails, the task fails, and bedoux_gold_task never
    # runs, so no Gold table is created at all.
    rows = [_row(s, passed=False, rate=0.4) for s in quality.REQUIRED_SOURCES]
    passed, problems = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert passed is False
    assert problems
    assert not any("first" in p.lower() for p in problems)


# ---------------------------------------------------------------------------
# Repeated processing
# ---------------------------------------------------------------------------


def test_repeated_evaluation_is_deterministic():
    rows = _all_good()
    first = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    second = quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert first == second


def test_evaluate_gate_does_not_mutate_its_input():
    rows = _all_good()
    import copy

    before = copy.deepcopy(rows)
    quality.evaluate_gate(rows, min_computed_ts=RUN_START)
    assert rows == before


def test_replayed_batch_that_newly_fails_flips_the_decision():
    good = _all_good()
    assert quality.evaluate_gate(good, min_computed_ts=RUN_START)[0] is True
    degraded = _all_good()
    degraded[0] = _row(quality.REQUIRED_SOURCES[0], passed=False, rate=0.25)
    assert quality.evaluate_gate(degraded, min_computed_ts=RUN_START)[0] is False


# ---------------------------------------------------------------------------
# The gate task wires the policy up correctly (source check, no Spark import)
# ---------------------------------------------------------------------------


def test_gate_check_task_fails_closed_and_binds_the_run():
    from pathlib import Path

    src = (Path(__file__).parent.parent / "src" / "bedoux" / "gate_check.py").read_text()
    assert src.splitlines()[0] == "# Databricks notebook source"
    assert "quality.evaluate_gate" in src
    assert "min_computed_ts=min_computed_ts" in src
    # A failing gate must raise; returning quietly would let Gold refresh.
    assert "raise RuntimeError" in src
    assert "run_start_ms" in src


def test_required_sources_cover_every_gold_source():
    # Gold reads leads_clean, campaigns_clean and ops_events_clean. campaigns
    # is a dimension with its own expect_or_drop rules and no quarantine table,
    # so it has no gate_status row; leads and ops_events must both be required.
    assert "leads" in quality.REQUIRED_SOURCES
    assert "ops_events" in quality.REQUIRED_SOURCES
    assert "web_events" in quality.REQUIRED_SOURCES
