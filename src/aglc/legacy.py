"""Simulated legacy report: what the old SSIS/SSRS stack would have exported.

Computed independently of the lakehouse, in plain Python, from the same synthetic
orders and licensees, so the reconciliation compares two separate implementations
rather than one implementation with itself.

`inject_discrepancy` deliberately changes one row (demo setting) to prove the
reconciliation catches a real difference.
"""

from collections import defaultdict

from . import expectations

INJECT_MODES = ("none", "revenue", "missing_row")


def retail_sales_daily(orders, licensees, inject_discrepancy="none"):
    if inject_discrepancy not in INJECT_MODES:
        raise ValueError(f"inject_discrepancy must be one of {INJECT_MODES}")
    valid_lic = {
        lic["licensee_id"]: lic for lic in expectations.keep_valid("licensees", licensees)
    }
    agg = defaultdict(lambda: {"order_count": 0, "units": 0, "revenue": 0.0})
    for o in expectations.keep_valid("orders", orders):
        lic = valid_lic.get(o["licensee_id"])
        if lic is None:
            continue
        key = (o["domain"], lic["region"], o["product_category"], o["order_date"])
        a = agg[key]
        a["order_count"] += 1
        a["units"] += o["quantity"]
        a["revenue"] += o["amount"]

    rows = [
        {
            "domain": k[0], "region": k[1], "product_category": k[2], "order_date": k[3],
            "order_count": v["order_count"], "units": v["units"], "revenue": round(v["revenue"], 2),
        }
        for k, v in sorted(agg.items())
    ]
    if rows and inject_discrepancy == "revenue":
        rows[0] = {**rows[0], "revenue": round(rows[0]["revenue"] + 125.0, 2)}
    elif rows and inject_discrepancy == "missing_row":
        rows = rows[1:]
    return rows
