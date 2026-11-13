"""Gold models and deterministic reconciliation (Track 4).

Money is Decimal end to end. Two checks, both pure Python:

- source_to_target: daily payment totals computed straight from the source
  extract versus the same totals from the ingested table. A difference means
  ingestion lost or invented rows (a late arrival outside the lookback window,
  for example). The comparison itself is Track 3's reconcile(), reused with a
  zero money tolerance.
- payments_vs_orders: order-level anti-joins between Gold revenue and settled
  payments. Finds unpaid, overpaid and orphan payments, each with the order ids
  as evidence.

The investigator reads these through a read-only tool. Model output never
substitutes for them.
"""

from decimal import Decimal

from ._compat import sibling
from .contracts import validate_row

ZERO = Decimal("0.00")
PAID_STATUSES = {"paid", "shipped"}


def order_totals(orders, lines):
    """{order_id: (order_date, status, total)} for live orders."""
    totals = {}
    for line in lines:
        if line.get("is_deleted"):
            continue
        totals[line["order_id"]] = totals.get(line["order_id"], ZERO) + line["unit_price"] * line["quantity"]
    return {o["order_id"]: (o["order_date"], o["status"], totals.get(o["order_id"], ZERO))
            for o in orders if not o.get("is_deleted")}


def daily_revenue(orders, lines):
    """Gold `daily_revenue`: recognized revenue (paid or shipped) by order date."""
    out = {}
    for order_date, status, total in order_totals(orders, lines).values():
        if status in PAID_STATUSES:
            row = out.setdefault(order_date, {"business_date": order_date.isoformat(),
                                              "order_count": 0, "revenue": ZERO})
            row["order_count"] += 1
            row["revenue"] += total
    return [out[d] for d in sorted(out)]


def daily_payments(payments):
    out = {}
    for p in payments:
        if p.get("is_deleted"):
            continue
        d = p["settled_date"].isoformat()
        row = out.setdefault(d, {"business_date": d, "payment_count": 0, "amount": ZERO})
        row["payment_count"] += 1
        row["amount"] += p["amount"]
    return [out[d] for d in sorted(out)]


def source_to_target(spec, source_rows, target_rows):
    """Daily payments from the raw source vs the ingested table.

    Source rows that fail the contract are skipped here: they are accounted for
    by quarantine, not by this check.
    """
    typed = {}
    for raw in source_rows:
        row, problems = validate_row(spec, raw)
        if row is not None:
            typed[tuple(row[k] for k in spec.primary_key)] = row
    return sibling("aglc.reconcile").reconcile(
        daily_payments(target_rows), daily_payments(typed.values()),
        key=("business_date",), exact=("payment_count",), money=("amount",), tolerance=ZERO,
    )


def payments_vs_orders(orders, lines, payments, business_date=None, sample=10):
    """Order-level reconciliation. With `business_date`, only orders placed that day."""
    totals = order_totals(orders, lines)
    paid = {}
    orphan = []
    for p in payments:
        if p.get("is_deleted"):
            continue
        if p["order_id"] not in totals:
            orphan.append(p["payment_id"])
            continue
        paid[p["order_id"]] = paid.get(p["order_id"], ZERO) + p["amount"]

    unpaid, overpaid, underpaid = [], [], []
    expected = received = ZERO
    for oid, (order_date, status, total) in sorted(totals.items()):
        if business_date and order_date.isoformat() != business_date:
            continue
        got = paid.get(oid, ZERO)
        if status in PAID_STATUSES:
            expected += total
            received += got
            if got == ZERO:
                unpaid.append(oid)
            elif got > total:
                overpaid.append(oid)
            elif got < total:
                underpaid.append(oid)
    return {
        "business_date": business_date,
        "passed": not (unpaid or overpaid or underpaid or orphan),
        "expected_revenue": str(expected), "payments_received": str(received),
        "difference": str(received - expected),
        "unpaid_orders": len(unpaid), "overpaid_orders": len(overpaid),
        "underpaid_orders": len(underpaid), "orphan_payments": len(orphan),
        "sample_unpaid": unpaid[:sample], "sample_overpaid": overpaid[:sample],
        "sample_underpaid": underpaid[:sample], "sample_orphan": orphan[:sample],
    }
