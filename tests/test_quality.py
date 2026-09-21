import pytest

from src.bedoux import quality


# ---------------------------------------------------------------------------
# dedup_by_key / reconcile primitives
# ---------------------------------------------------------------------------


def test_dedup_by_key_keeps_first_occurrence():
    rows = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}, {"id": 1, "v": "c"}]
    kept, dups = quality.dedup_by_key(rows, "id")
    assert kept == [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
    assert dups == [{"id": 1, "v": "c"}]


def test_reconcile_conserves_every_row():
    rows = [{"id": i} for i in range(50)] + [{"id": 3}, {"id": 7}]  # two duplicates
    accepted, quarantined = quality.reconcile(rows, "id", lambda r: [])
    assert len(accepted) + len(quarantined) == len(rows)
    assert len(quarantined) == 2
    assert all(reasons == ["duplicate_id"] for _row, reasons in quarantined)


# ---------------------------------------------------------------------------
# Scenario A -- malformed lead batch (elevated null campaign_id rate)
# ---------------------------------------------------------------------------


def test_scenario_a_malformed_leads_are_quarantined_with_reason():
    known = {1, 2, 3}
    leads = (
        [{"lead_id": i, "campaign_id": 1, "stage": "new"} for i in range(1, 86)]
        + [{"lead_id": i, "campaign_id": None, "stage": "new"} for i in range(86, 101)]
    )
    accepted, quarantined = quality.reconcile(leads, "lead_id", quality.classify_lead, known)
    assert len(accepted) == 85
    assert len(quarantined) == 15
    assert all(reasons == ["null_campaign_id"] for _row, reasons in quarantined)
    # 15% quarantine rate is well past the 10% threshold -- the gate should withhold.
    rate = quality.quarantine_rate(len(leads), len(quarantined))
    assert rate == pytest.approx(0.15)
    assert quality.gate_passed(len(leads), len(quarantined)) is False


# ---------------------------------------------------------------------------
# Scenario B -- duplicate leads
# ---------------------------------------------------------------------------


def test_scenario_b_duplicate_lead_id_quarantined_not_double_counted():
    known = {1}
    leads = [
        {"lead_id": 1, "campaign_id": 1, "stage": "new"},
        {"lead_id": 2, "campaign_id": 1, "stage": "won"},
        {"lead_id": 1, "campaign_id": 1, "stage": "new"},  # replayed duplicate
    ]
    accepted, quarantined = quality.reconcile(leads, "lead_id", quality.classify_lead, known)
    assert [r["lead_id"] for r in accepted] == [1, 2]
    assert len(quarantined) == 1
    dup_row, reasons = quarantined[0]
    assert dup_row["lead_id"] == 1
    assert reasons == ["duplicate_lead_id"]
    # Gold aggregates (e.g. count("*")) over `accepted` count lead_id 1 exactly once.
    assert sum(1 for r in accepted if r["lead_id"] == 1) == 1


# ---------------------------------------------------------------------------
# Scenario C -- missing campaign reference (non-null but unknown campaign_id)
# ---------------------------------------------------------------------------


def test_scenario_c_unknown_campaign_id_quarantined_not_silently_dropped():
    known = {1, 2}
    leads = [
        {"lead_id": 1, "campaign_id": 1, "stage": "new"},
        {"lead_id": 2, "campaign_id": 99, "stage": "qualified"},  # campaign 99 doesn't exist
    ]
    accepted, quarantined = quality.reconcile(leads, "lead_id", quality.classify_lead, known)
    assert [r["lead_id"] for r in accepted] == [1]
    assert len(quarantined) == 1
    row, reasons = quarantined[0]
    assert row["lead_id"] == 2
    assert reasons == ["unknown_campaign_id"]


def test_classify_lead_distinguishes_null_from_unknown_campaign_id():
    known = {1, 2}
    assert quality.classify_lead({"campaign_id": None, "stage": "new"}, known) == ["null_campaign_id"]
    assert quality.classify_lead({"campaign_id": 99, "stage": "new"}, known) == ["unknown_campaign_id"]
    assert quality.classify_lead({"campaign_id": 1, "stage": "new"}, known) == []


def test_classify_lead_can_report_multiple_reasons():
    reasons = quality.classify_lead({"campaign_id": None, "stage": "bogus"}, {1})
    assert set(reasons) == {"null_campaign_id", "invalid_stage"}


# ---------------------------------------------------------------------------
# Normal control -- healthy batch at the generator's ~2% baseline
# ---------------------------------------------------------------------------


def test_normal_control_passes_the_gate():
    known = set(range(1, 31))
    leads = (
        [{"lead_id": i, "campaign_id": (i % 30) + 1, "stage": "new"} for i in range(1, 991)]
        + [{"lead_id": i, "campaign_id": None, "stage": "new"} for i in range(991, 1001)]  # 1% null
    )
    accepted, quarantined = quality.reconcile(leads, "lead_id", quality.classify_lead, known)
    assert len(quarantined) == 10
    assert quality.gate_passed(len(leads), len(quarantined)) is True


def test_classify_web_event_and_ops_event():
    known = {1}
    assert quality.classify_web_event({"campaign_id": 1, "session_duration_seconds": 5}, known) == []
    assert quality.classify_web_event({"campaign_id": None, "session_duration_seconds": 5}, known) == ["null_campaign_id"]
    assert quality.classify_web_event({"campaign_id": 1, "session_duration_seconds": -1}, known) == ["invalid_duration"]
    assert quality.classify_ops_event({"latency_seconds": 1.5}) == []
    assert quality.classify_ops_event({"latency_seconds": None}) == ["invalid_latency"]
    assert quality.classify_ops_event({"latency_seconds": -0.1}) == ["invalid_latency"]


# ---------------------------------------------------------------------------
# Replay -- reprocessing the same batch must not duplicate or drift
# ---------------------------------------------------------------------------


def test_replay_is_idempotent():
    known = {1, 2}
    leads = [
        {"lead_id": 1, "campaign_id": 1, "stage": "new"},
        {"lead_id": 2, "campaign_id": None, "stage": "new"},
        {"lead_id": 3, "campaign_id": 99, "stage": "won"},
    ]
    first = quality.reconcile(leads, "lead_id", quality.classify_lead, known)
    second = quality.reconcile(leads, "lead_id", quality.classify_lead, known)
    assert first == second


def test_gate_threshold_is_five_times_generator_baseline_invalid_rate():
    from src.bedoux.generator import INVALID_RATE

    assert quality.QUARANTINE_RATE_THRESHOLD == pytest.approx(INVALID_RATE * 5)
