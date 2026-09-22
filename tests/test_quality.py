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


def test_duplicate_row_that_also_fails_classification_gets_both_reasons():
    # A row can be a duplicate AND independently fail classification -- reasons
    # are the union of both checks, not "duplicate short-circuits everything
    # else" (see reconcile()'s docstring for why this must match silver.py).
    known = {1}
    leads = [
        {"lead_id": 1, "campaign_id": None, "stage": "new"},
        {"lead_id": 1, "campaign_id": None, "stage": "new"},  # duplicate AND null campaign_id
    ]
    accepted, quarantined = quality.reconcile(leads, "lead_id", quality.classify_lead, known)
    assert accepted == []
    assert len(quarantined) == 2
    assert quarantined[0][1] == ["null_campaign_id"]
    assert quarantined[1][1] == ["null_campaign_id", "duplicate_lead_id"]


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


def test_eligible_campaign_ids_excludes_negative_budget_and_null_client():
    campaigns = [
        {"campaign_id": 1, "client_id": 10, "budget": 500},
        {"campaign_id": 2, "client_id": 11, "budget": -50},  # campaigns_clean drops: budget < 0
        {"campaign_id": 3, "client_id": None, "budget": 200},  # campaigns_clean drops: null client_id
    ]
    assert quality.eligible_campaign_ids(campaigns) == {1}


def test_lead_referencing_a_campaign_campaigns_clean_would_reject_is_quarantined():
    # ADVERSARIAL: a review found that leads_flagged/web_events_flagged
    # checked campaign existence against campaigns_raw, not campaigns_clean.
    # campaigns_clean drops a campaign with a negative budget via its own
    # expect_or_drop; a lead referencing that campaign must be quarantined
    # as unknown_campaign_id, not accepted as if the campaign were eligible
    # -- otherwise it passes Silver, conserves, passes the gate, and vanishes
    # from Gold's inner join (gold_client_funnel) with no record at all. The
    # seeded generator never produces a droppable campaign (budget is always
    # uniform(200, 5000), client_id is always set), so this gap is latent on
    # real fixture data -- this fixture is what keeps it from regressing.
    campaigns_raw = [
        {"campaign_id": 1, "client_id": 10, "budget": 500},
        {"campaign_id": 2, "client_id": 11, "budget": -50},
    ]
    eligible = quality.eligible_campaign_ids(campaigns_raw)

    leads = [{"lead_id": 100, "campaign_id": 2, "stage": "new"}]
    accepted, quarantined = quality.reconcile(leads, "lead_id", quality.classify_lead, eligible)
    assert accepted == []
    assert len(quarantined) == 1
    assert quarantined[0][1] == ["unknown_campaign_id"]

    # Using the un-filtered Bronze set instead would wrongly accept it --
    # pinning that this is a real behavioral difference, not a vacuous check.
    bronze_known = {c["campaign_id"] for c in campaigns_raw}
    accepted_wrong, _ = quality.reconcile(leads, "lead_id", quality.classify_lead, bronze_known)
    assert accepted_wrong == leads


def test_web_event_referencing_a_campaign_campaigns_clean_would_reject_is_quarantined():
    campaigns_raw = [{"campaign_id": 1, "client_id": None, "budget": 500}]  # dropped: null client_id
    eligible = quality.eligible_campaign_ids(campaigns_raw)
    assert eligible == set()

    events = [{"event_id": 1, "campaign_id": 1, "session_duration_seconds": 5}]
    accepted, quarantined = quality.reconcile(events, "event_id", quality.classify_web_event, eligible)
    assert accepted == []
    assert quarantined[0][1] == ["unknown_campaign_id"]


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


# ---------------------------------------------------------------------------
# Gate rate must count rows, not exploded reasons (regression: a review found
# silver.py's gate_status originally summed quality_metrics' per-reason
# row_count, so a multi-reason row inflated both numerator and denominator).
# ---------------------------------------------------------------------------


def test_gate_rate_counts_rows_not_reasons_for_multi_reason_batch():
    # 100 leads: 90 clean, plus 10 replays of lead_ids 1-10 that are also
    # missing a campaign_id -- each replay carries two reasons at once.
    # True rate: 10 quarantined rows / 100 total = 10% (at the threshold, so
    # the gate should still publish). The bug this regression-tests computed
    # 20 "reason units" over 110 "reason units" = 18.2%, which would wrongly
    # withhold Gold.
    known = {1}
    leads = [{"lead_id": i, "campaign_id": 1, "stage": "new"} for i in range(1, 91)]
    leads += [{"lead_id": i, "campaign_id": None, "stage": "new"} for i in range(1, 11)]
    assert len(leads) == 100

    accepted, quarantined = quality.reconcile(leads, "lead_id", quality.classify_lead, known)
    assert len(accepted) == 90
    assert len(quarantined) == 10  # one unit per row, not per reason
    for _row, reasons in quarantined:
        assert set(reasons) == {"null_campaign_id", "duplicate_lead_id"}

    total_reason_units = sum(len(reasons) for _row, reasons in quarantined)
    assert total_reason_units == 20  # confirms each quarantined row does carry two reasons

    rate = quality.quarantine_rate(len(leads), len(quarantined))
    assert rate == pytest.approx(0.10)
    assert rate != pytest.approx(20 / 110)  # the buggy exploded-count arithmetic
    assert quality.gate_passed(len(leads), len(quarantined)) is True


# ---------------------------------------------------------------------------
# NULL-safety regressions: a plain `< 0` or `isin(...)` Spark comparison is
# NULL (not True) for a NULL input, so the corresponding row would silently
# pass through accepted unless the NULL case is handled explicitly. These pin
# quality.py's (already-correct) behavior; the bugs were in silver.py's
# native Spark expressions, fixed to match by adding an explicit isNull() check.
# ---------------------------------------------------------------------------


def test_classify_lead_quarantines_null_stage():
    reasons = quality.classify_lead({"campaign_id": 1, "stage": None}, {1})
    assert reasons == ["invalid_stage"]


def test_classify_web_event_quarantines_null_duration():
    reasons = quality.classify_web_event({"campaign_id": 1, "session_duration_seconds": None}, {1})
    assert reasons == ["invalid_duration"]


# ---------------------------------------------------------------------------
# Spec-sync check: silver.py can't be imported here (it needs a live `dlt`
# runtime this environment doesn't have), so this greps its source text for
# the REASON_* constants and _duplicate_reason(...) calls introduced to hold
# its reason-code literals, and checks them against quality.py's reason
# vocabulary. A renamed/typo'd/removed reason code on either side fails this
# test instead of silently diverging. No Spark/pyspark import required.
# ---------------------------------------------------------------------------


def test_silver_reason_constants_match_quality_spec():
    import re
    from pathlib import Path

    silver_src = (Path(__file__).parent.parent / "src" / "bedoux" / "silver.py").read_text()

    constant_values = set(re.findall(r'^REASON_\w+ = "([a-z_]+)"', silver_src, re.MULTILINE))
    duplicate_keys = set(re.findall(r'_duplicate_reason\("(\w+)"\)', silver_src))
    silver_reasons = constant_values | {f"duplicate_{key}" for key in duplicate_keys}

    expected = {
        "accepted",
        "null_campaign_id",
        "unknown_campaign_id",
        "invalid_stage",
        "invalid_duration",
        "invalid_latency",
        "duplicate_lead_id",
        "duplicate_event_id",
        "duplicate_ops_event_id",
    }
    assert silver_reasons == expected

    # Every REASON_* constant, and every duplicate key silver.py dedups on,
    # must actually be used at a lit(...) call site -- an unused constant
    # would mean a rule silently isn't wired into any _flagged view.
    for name in ("REASON_NULL_CAMPAIGN_ID", "REASON_UNKNOWN_CAMPAIGN_ID", "REASON_INVALID_STAGE",
                 "REASON_INVALID_DURATION", "REASON_INVALID_LATENCY", "REASON_ACCEPTED"):
        assert re.search(rf"lit\({name}\)", silver_src), f"{name} defined but never used in a lit(...) call"
    for key in ("lead_id", "event_id", "ops_event_id"):
        assert f'_duplicate_reason("{key}")' in silver_src


# ---------------------------------------------------------------------------
# Incident regression: array_remove(array(...), None) is null-intolerant in
# Spark -- a NULL *element* argument makes the WHOLE result NULL instead of
# stripping NULLs, so every when(...) with no .otherwise() (NULL when false)
# poisoned the entire _reasons array on every row. A live baseline run showed
# the consequence: leads_clean/leads_quarantine (and the same pair for
# web_events/ops_events) came out completely empty while gate_status reported
# a clean pass. Fixed with array_compact(...), which does strip NULL
# elements. This is a source-text check, like
# test_silver_reason_constants_match_quality_spec above, for the same reason:
# silver.py needs a live `dlt`/pyspark runtime this environment doesn't have,
# so it can't be imported and exercised directly. No Spark/pyspark import
# required. See docs/sentinel/chapters/02-quality-gate.md for the incident.
# ---------------------------------------------------------------------------


def test_silver_does_not_use_null_intolerant_array_remove():
    import ast
    from pathlib import Path

    silver_src = (Path(__file__).parent.parent / "src" / "bedoux" / "silver.py").read_text()

    # AST-parsed (silver.py can be parsed without a live dlt/pyspark runtime,
    # just not imported/executed), not grepped, so the explanatory comments
    # above that mention "array_remove(...)" in prose don't trip a substring
    # match -- only an actual `from pyspark.sql.functions import array_remove`
    # or a call would.
    tree = ast.parse(silver_src)
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "array_remove" not in imported_names, (
        "array_remove(array(...), None) is null-intolerant in Spark -- a NULL "
        "element argument makes the whole result NULL. Use array_compact(...) "
        "instead."
    )
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "array_remove" not in called_names

    assert silver_src.count("array_compact(") == 3, (
        "expected array_compact(...) at all three *_flagged views "
        "(leads/web_events/ops_events)"
    )
    assert silver_src.count('@dlt.expect_or_fail("reasons_not_null", "_reasons IS NOT NULL")') == 3, (
        "each *_flagged view should fail loudly, not silently empty its "
        "downstream tables, if _reasons is ever NULL again"
    )
