"""Track 3 (docs/contracts-aglc.md): generator, expectations, rules, legacy, reconcile, governance.

Local fixtures only. These tests don't exercise Spark, DLT or Unity Catalog.
"""

import pytest

from src.aglc import expectations, generator, governance, legacy, reconcile, rules


@pytest.fixture(scope="module")
def data():
    players = generator.generate_players()
    sessions, wagers, deposits = generator.generate_gaming_activity([p["player_id"] for p in players])
    licensees = generator.generate_licensees()
    orders = generator.generate_orders(licensees)
    return {
        "players": players, "sessions": sessions, "wagers": wagers,
        "deposits": deposits, "licensees": licensees, "orders": orders,
    }


@pytest.fixture(scope="module")
def clean(data):
    return {k: expectations.keep_valid(k, v) for k, v in data.items()}


# --- generator -------------------------------------------------------------

def test_generator_is_deterministic():
    a = generator.generate_gaming_activity([1, 2, 3])
    b = generator.generate_gaming_activity([1, 2, 3])
    assert a == b


def test_keys_are_unique(data):
    for entity, key in [("players", "player_id"), ("sessions", "session_id"),
                        ("wagers", "wager_id"), ("deposits", "deposit_id"),
                        ("licensees", "licensee_id"), ("orders", "order_id")]:
        ids = [r[key] for r in data[entity]]
        assert len(ids) == len(set(ids)), entity


@pytest.mark.parametrize("entity", ["sessions", "wagers", "deposits", "orders"])
def test_some_rows_are_deliberately_invalid(data, clean, entity):
    dropped = len(data[entity]) - len(clean[entity])
    assert 0 < dropped < 0.06 * len(data[entity])


def test_pii_is_synthetic(data):
    assert all(p["email"].split("@")[1].endswith((".com", ".test")) for p in data["players"])
    assert all(p["email"].startswith(f"player{p['player_id']}@") for p in data["players"])


# --- expectations ----------------------------------------------------------

@pytest.mark.parametrize("entity, row, ok", [
    ("wagers", {"player_id": 1, "stake": 0.01, "payout": 0.0}, True),
    ("wagers", {"player_id": 1, "stake": 0.0, "payout": 0.0}, False),
    ("wagers", {"player_id": None, "stake": 5.0, "payout": 0.0}, False),
    ("sessions", {"player_id": 1, "duration_minutes": 0}, True),
    ("sessions", {"player_id": 1, "duration_minutes": -1}, False),
    ("orders", {"licensee_id": 1, "amount": 0.0, "quantity": 1}, True),
    ("orders", {"licensee_id": 1, "amount": -0.01, "quantity": 1}, False),
    ("licensees", {"licensee_id": 1, "domain": "tobacco"}, False),
])
def test_expectation_boundaries(entity, row, ok):
    assert expectations.is_valid(entity, row) is ok


def test_every_expectation_has_sql():
    for entity in expectations.EXPECTATIONS:
        assert all(sql.strip() for sql in expectations.sql_rules(entity).values())


# --- responsible-gaming rules ---------------------------------------------

@pytest.fixture(scope="module")
def flags(clean):
    rows = rules.player_flags(clean["players"], clean["sessions"], clean["wagers"], clean["deposits"])
    return {r["player_id"]: r for r in rows}


@pytest.mark.parametrize("flag, planted", [
    ("flag_chasing_losses", "chasing_losses"),
    ("flag_deposit_spike", "deposit_spike"),
    ("flag_long_session", "long_session"),
    ("flag_self_exclusion_breach", "self_exclusion_breach"),
])
def test_flags_fire_exactly_on_planted_players(flags, flag, planted):
    fired = sorted(pid for pid, r in flags.items() if r[flag])
    assert fired == generator.PLANTED[planted]


def test_risk_levels(flags):
    assert flags[2]["risk_level"] == "high"   # chasing + spike
    assert flags[5]["risk_level"] == "high"   # self-exclusion breach
    assert flags[4]["risk_level"] == "medium"
    assert flags[50]["risk_level"] == "low"
    assert flags[50]["explanation"] == "no rule triggered"


def test_deposit_spike_needs_history():
    few = [{"deposit_total": t, "deposit_count": 1} for t in (10, 10, 10, 1000)]
    assert rules.deposit_spike(few) is False
    enough = few + [{"deposit_total": 10, "deposit_count": 1}]
    assert rules.deposit_spike(enough) is True


def test_player_daily_net_loss():
    rows = rules.player_daily(
        sessions=[{"player_id": 1, "start_ts": "2026-01-05T10:00:00", "duration_minutes": 30}],
        wagers=[{"player_id": 1, "wager_ts": "2026-01-05T10:05:00", "stake": 10.0, "payout": 4.0}],
        deposits=[{"player_id": 1, "deposit_ts": "2026-01-05T09:00:00", "amount": 20.0}],
    )
    assert rows == [{"player_id": 1, "activity_date": "2026-01-05", "total_stake": 10.0,
                     "total_payout": 4.0, "net_loss": 6.0, "deposit_total": 20.0,
                     "deposit_count": 1, "session_minutes": 30}]


# --- legacy + reconciliation ----------------------------------------------

def _lakehouse_sales(clean):
    """Stand-in for gold_retail_sales_daily: the legacy logic, run on Silver-clean rows."""
    return legacy.retail_sales_daily(clean["orders"], clean["licensees"])


def test_reconcile_passes_when_both_sides_agree(data, clean):
    report = reconcile.reconcile(_lakehouse_sales(clean),
                                 legacy.retail_sales_daily(data["orders"], data["licensees"]))
    assert report["passed"], report
    assert report["new_rows"] == report["legacy_rows"] > 0


@pytest.mark.parametrize("mode, field", [("revenue", "value_mismatches"),
                                         ("missing_row", "only_in_new")])
def test_reconcile_catches_injected_discrepancy(data, clean, mode, field):
    broken = legacy.retail_sales_daily(data["orders"], data["licensees"], inject_discrepancy=mode)
    report = reconcile.reconcile(_lakehouse_sales(clean), broken)
    assert not report["passed"]
    assert report[field] == 1


def test_reconcile_tolerates_rounding_only():
    k = {"domain": "liquor", "region": "South", "product_category": "beer", "order_date": "2026-01-05",
         "order_count": 1, "units": 2}
    assert reconcile.reconcile([{**k, "revenue": 10.0}], [{**k, "revenue": 10.005}])["passed"]
    assert not reconcile.reconcile([{**k, "revenue": 10.0}], [{**k, "revenue": 10.02}])["passed"]


def test_reconcile_rejects_duplicate_keys():
    k = {"domain": "liquor", "region": "South", "product_category": "beer", "order_date": "2026-01-05",
         "order_count": 1, "units": 1, "revenue": 1.0}
    with pytest.raises(ValueError, match="duplicate key"):
        reconcile.reconcile([k, k], [k])


def test_unknown_inject_mode_is_rejected(data):
    with pytest.raises(ValueError):
        legacy.retail_sales_daily(data["orders"], data["licensees"], inject_discrepancy="typo")


# --- governance ------------------------------------------------------------

def test_functions_cover_masks_and_filter():
    sql = "\n".join(governance.function_statements("workspace"))
    for fn in ("mask_email", "mask_dob", "filter_domain"):
        assert f"FUNCTION workspace.aglc_governance.{fn}(" in sql
    for group in governance.GROUPS.values():
        assert f"is_account_group_member('{group}')" in sql


def test_players_schema_masks_pii_only_when_enforced():
    on = governance.players_schema("workspace", enforce=True)
    assert "email STRING MASK workspace.aglc_governance.mask_email" in on
    assert "date_of_birth STRING MASK workspace.aglc_governance.mask_dob" in on
    assert "MASK" not in governance.players_schema("workspace", enforce=False)


def test_players_schema_matches_bronze_columns():
    """Silver drops _row_id; every other Bronze column must be declared, in order."""
    declared = [c.split()[0] for c in governance.players_schema(enforce=False).split(", ")]
    bronze = [c.split()[0] for c in generator.RAW_SCHEMAS["players"].split(", ")] + ["_ingest_ts", "_source_table"]
    assert declared == bronze


def test_row_filter_clause():
    assert governance.retail_row_filter("workspace") == \
        "ROW FILTER workspace.aglc_governance.filter_domain ON (domain)"
    assert governance.retail_row_filter("workspace", enforce=False) is None


def test_analysts_get_gold_only():
    for stmt in governance.grant_statements():
        if "analyst" in stmt:
            assert "aglc_gold" in stmt or "ON CATALOG" in stmt, stmt


def test_every_group_gets_catalog_access():
    sql = "\n".join(governance.grant_statements())
    for group in governance.GROUPS.values():
        assert f"ON CATALOG workspace TO `{group}`" in sql


@pytest.mark.parametrize("bad", ["work space", "x;DROP", "1abc", "", None])
def test_unsafe_catalog_names_are_rejected(bad):
    with pytest.raises(ValueError, match="unsafe identifier"):
        governance.function_statements(bad)


@pytest.mark.parametrize("value, expected", [("true", True), ("FALSE", False), (" true ", True)])
def test_as_bool(value, expected):
    assert governance.as_bool(value) is expected


@pytest.mark.parametrize("value", ["yes", "1", ""])
def test_as_bool_rejects_ambiguous(value):
    with pytest.raises(ValueError):
        governance.as_bool(value)
