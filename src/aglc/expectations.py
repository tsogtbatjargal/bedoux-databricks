"""Silver-layer expectations for Track 3, defined once.

Each entry holds the SQL text DLT enforces (`@dlt.expect_all_or_drop`) and a Python
predicate with the same meaning. The legacy report and the unit tests use the
predicates, so "what counts as valid" can't drift between the lakehouse and the
legacy side of the reconciliation. tests/test_aglc_expectations.py checks that each
pair agrees on boundary rows.
"""

EXPECTATIONS = {
    "players": {
        "valid_player_id": ("player_id IS NOT NULL", lambda r: r["player_id"] is not None),
    },
    "sessions": {
        "valid_player_id": ("player_id IS NOT NULL", lambda r: r["player_id"] is not None),
        "non_negative_duration": ("duration_minutes >= 0", lambda r: r["duration_minutes"] >= 0),
    },
    "wagers": {
        "valid_player_id": ("player_id IS NOT NULL", lambda r: r["player_id"] is not None),
        "positive_stake": ("stake > 0", lambda r: r["stake"] > 0),
        "non_negative_payout": ("payout >= 0", lambda r: r["payout"] >= 0),
    },
    "deposits": {
        "valid_player_id": ("player_id IS NOT NULL", lambda r: r["player_id"] is not None),
        "positive_amount": ("amount > 0", lambda r: r["amount"] > 0),
    },
    "licensees": {
        "valid_licensee_id": ("licensee_id IS NOT NULL", lambda r: r["licensee_id"] is not None),
        "known_domain": ("domain IN ('liquor', 'cannabis')", lambda r: r["domain"] in ("liquor", "cannabis")),
    },
    "orders": {
        "valid_licensee_id": ("licensee_id IS NOT NULL", lambda r: r["licensee_id"] is not None),
        "non_negative_amount": ("amount >= 0", lambda r: r["amount"] >= 0),
        "positive_quantity": ("quantity > 0", lambda r: r["quantity"] > 0),
    },
}


def sql_rules(entity):
    """{name: sql} for `@dlt.expect_all_or_drop`."""
    return {name: sql for name, (sql, _) in EXPECTATIONS[entity].items()}


def is_valid(entity, row):
    return all(check(row) for _, check in EXPECTATIONS[entity].values())


def keep_valid(entity, rows):
    return [r for r in rows if is_valid(entity, r)]
