"""Deterministic synthetic order-to-cash source data (Track 4). All fictional.

The source is modeled as a stream of row versions, each with the day it became
visible to the extractor (`arrived`). A snapshot "through day k" is what the
source tables hold after day k: the latest version of each key that has
arrived. Most versions arrive the same day they are stamped, but a few do not.
That gap is what makes cursors, lookback windows and reconciliation matter:

- day 2 includes a batch of updates sharing one timestamp (composite cursor),
  and a payment stamped late on day 1 that only arrives on day 2 (inside the
  24h lookback).
- `inject()` adds one named defect to a day's increment and returns the keys it
  touched, so detection can be measured, not asserted.

Values are strings, as a CSV/REST/JDBC extract would deliver them.
"""

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

DAY1 = date(2026, 11, 2)
DAYS = (1, 2, 3)
PRODUCTS = {pid: Decimal(price) for pid, price in enumerate(
    ["4.50", "12.00", "7.25", "19.99", "3.10", "45.00", "8.80", "15.50",
     "2.75", "29.90", "11.40", "6.60"], start=1)}

DATASETS = ("sales.orders", "sales.order_lines", "sales.payments")
KEYS = {"sales.orders": ("order_id",), "sales.order_lines": ("order_id", "line_no"),
        "sales.payments": ("payment_id",)}

DEFECTS = (
    "bad_unit_price", "removed_column", "added_column", "null_key", "invalid_status",
    "duplicate_key", "duplicate_charge", "missing_payment", "stale_source",
    "late_arrival",
)


def day_date(day):
    return DAY1 + timedelta(days=day - 1)


def _ts(day, seconds):
    return (datetime.combine(day_date(day), datetime.min.time())
            + timedelta(seconds=seconds)).isoformat()


class _Source:
    def __init__(self):
        self.events = []  # (arrived_day, dataset, row)

    def put(self, arrived, dataset, row):
        self.events.append((arrived, dataset, dict(row)))

    def latest(self, dataset, through):
        out = {}
        for arrived, ds, row in self.events:
            if ds == dataset and arrived <= through:
                out[tuple(row.get(k) for k in KEYS[dataset])] = row
        return out


def _build(seed, orders_per_day):
    rng = random.Random(seed)
    src = _Source()
    next_order, next_payment = 1, 1
    totals = {}

    def new_order(day):
        nonlocal next_order
        oid = next_order
        next_order += 1
        ts = _ts(day, rng.randrange(3600, 20 * 3600))
        src.put(day, "sales.orders", {
            "order_id": str(oid), "customer_id": str(rng.randrange(1, 60)),
            "status": "placed", "order_date": day_date(day).isoformat(), "updated_at": ts,
            "is_deleted": "false"})
        total = Decimal("0")
        for line_no in range(1, rng.randrange(2, 4) + 1):
            pid = rng.choice(list(PRODUCTS))
            qty = rng.randrange(1, 6)
            total += PRODUCTS[pid] * qty
            src.put(day, "sales.order_lines", {
                "order_id": str(oid), "line_no": str(line_no), "product_id": str(pid),
                "quantity": str(qty), "unit_price": str(PRODUCTS[pid]), "updated_at": ts,
                "is_deleted": "false"})
        totals[oid] = (total, ts)
        return oid

    def set_status(day, oid, status, ts):
        current = src.latest("sales.orders", day)[(str(oid),)]
        src.put(day, "sales.orders", {**current, "status": status, "updated_at": ts})

    def pay(arrived, oid, settled_day, ts):
        nonlocal next_payment
        src.put(arrived, "sales.payments", {
            "payment_id": str(next_payment), "order_id": str(oid),
            "amount": str(totals[oid][0]), "settled_date": day_date(settled_day).isoformat(),
            "updated_at": ts, "is_deleted": "false"})
        next_payment += 1

    # Day 1: new orders; about half are paid the same day.
    day1 = [new_order(1) for _ in range(orders_per_day)]
    for oid in day1:
        if rng.random() < 0.5:
            ts = _ts(1, 21 * 3600 + rng.randrange(0, 3600))
            set_status(1, oid, "paid", ts)
            pay(1, oid, 1, ts)
    # A payment stamped late on day 1 that the extractor only sees on day 2.
    late = next(o for o in day1 if src.latest("sales.orders", 1)[(str(o),)]["status"] == "placed")
    late_ts = _ts(1, 23 * 3600 + 1800)
    pay(2, late, 1, late_ts)
    src.put(2, "sales.orders", {**src.latest("sales.orders", 1)[(str(late),)],
                                "status": "paid", "updated_at": late_ts})

    # Day 2: new orders, a batch status job (one shared timestamp), cancellations.
    for _ in range(orders_per_day):
        new_order(2)
    tie_ts = _ts(2, 2 * 3600)
    for oid in day1:
        status = src.latest("sales.orders", 2)[(str(oid),)]["status"]
        if status == "paid" and rng.random() < 0.6:
            set_status(2, oid, "shipped", tie_ts)
        elif status == "placed" and rng.random() < 0.15:
            set_status(2, oid, "cancelled", _ts(2, rng.randrange(4, 10) * 3600))
        elif status == "placed" and rng.random() < 0.5:
            ts = _ts(2, rng.randrange(10, 20) * 3600)
            set_status(2, oid, "paid", ts)
            pay(2, oid, 2, ts)

    # Day 3: new orders and payments for day-2 orders.
    for oid in range(orders_per_day + 1, 2 * orders_per_day + 1):
        if rng.random() < 0.6:
            ts = _ts(3, rng.randrange(1, 12) * 3600)
            set_status(3, oid, "paid", ts)
            pay(3, oid, 3, ts)
    for _ in range(orders_per_day):
        new_order(3)

    return src, rng, next_payment, totals


def _strip(rows):
    return [dict(r) for r in rows]


class Scenario:
    """A generated source plus at most one injected defect.

    snapshot(day) -> {dataset_id: [raw rows]} as the source holds them after `day`.
    """

    def __init__(self, seed=7, orders_per_day=80, defect=None, defect_day=3):
        if defect is not None and defect not in DEFECTS:
            raise ValueError(f"unknown defect {defect!r}; expected one of {DEFECTS}")
        if defect is not None and defect_day not in (2, 3):
            raise ValueError("defects are injected on day 2 or 3 (day 1 is the baseline)")
        if defect == "late_arrival" and defect_day != 3:
            raise ValueError("late_arrival needs defect_day=3: it backdates two days")
        self.seed, self.defect, self.defect_day = seed, defect, defect_day
        self._src, self._rng, self._next_payment, self._totals = _build(seed, orders_per_day)
        self.injected = {"dataset": None, "keys": []}
        if defect:
            self._inject(defect, defect_day)

    def snapshot(self, day):
        snap = {ds: _strip(self._src.latest(ds, day).values()) for ds in DATASETS}
        # Rows that can't be keyed (null or duplicated keys) live beside the
        # keyed versions, exactly as a raw extract would carry them.
        for arrived, ds, row in self._src.events:
            if ds.endswith("#extra") and arrived <= day:
                snap[ds.removesuffix("#extra")].append(dict(row))
        if self.defect == "removed_column" and day >= self.defect_day:
            for row in snap["sales.payments"]:
                row.pop("amount", None)
        if self.defect == "added_column" and day >= self.defect_day:
            for row in snap["sales.payments"]:
                row["currency"] = "CAD"
        return snap

    # -- defect injection ------------------------------------------------
    def _day_rows(self, dataset, day):
        prefix = day_date(day).isoformat()
        return [(k, r) for k, r in self._src.latest(dataset, day).items()
                if r["updated_at"].startswith(prefix)]

    def _mark(self, dataset, keys):
        self.injected = {"dataset": dataset, "keys": sorted(keys)}

    def _inject(self, defect, day):
        rng = random.Random(self.seed * 1000 + day)
        src = self._src
        if defect == "bad_unit_price":
            rows = self._day_rows("sales.order_lines", day)
            picked = rng.sample(rows, min(27, len(rows) // 4))
            for _, r in picked:
                src.put(day, "sales.order_lines", {**r, "unit_price": "N/A"})
            self._mark("sales.order_lines", [k for k, _ in picked])
        elif defect == "removed_column":
            self._mark("sales.payments", [])
        elif defect == "added_column":
            self._mark("sales.payments", [])
        elif defect == "null_key":
            rows = self._day_rows("sales.payments", day)
            picked = rng.sample(rows, min(4, len(rows)))
            for _, r in picked:
                src.put(day, "sales.payments#extra", {**r, "payment_id": ""})
            # The original keyed versions stay; the bad copies have no key, so
            # they are identified by order_id.
            self._mark("sales.payments", [(r["order_id"],) for _, r in picked])
        elif defect == "invalid_status":
            rows = self._day_rows("sales.orders", day)
            picked = rng.sample(rows, min(5, len(rows)))
            for _, r in picked:
                src.put(day, "sales.orders", {**r, "status": "refunded"})
            self._mark("sales.orders", [k for k, _ in picked])
        elif defect == "duplicate_key":
            rows = self._day_rows("sales.orders", day)
            picked = rng.sample(rows, min(3, len(rows)))
            for k, r in picked:
                # Same key and timestamp, different content: nothing in the row
                # says which version is right.
                src.put(day, "sales.orders#extra", {**r, "customer_id": "999"})
            self._mark("sales.orders", [k for k, _ in picked])
        elif defect in ("duplicate_charge", "missing_payment"):
            rows = self._day_rows("sales.payments", day)
            picked = rng.sample(rows, min(3, len(rows)))
            if defect == "duplicate_charge":
                for _, r in picked:
                    src.put(day, "sales.payments", {
                        **r, "payment_id": str(self._next_payment)})
                    self._next_payment += 1
            else:
                for _, r in picked:
                    src.put(day, "sales.payments", {**r, "is_deleted": "true"})
                # Deletions are honest tombstones; "missing" means the upstream
                # dropped them without one, so remove the rows outright.
                drop = {k for k, _ in picked}
                src.events = [e for e in src.events if not (
                    e[1] == "sales.payments" and (e[2]["payment_id"],) in drop)]
            self._mark("sales.payments", [(r["order_id"],) for _, r in picked])
        elif defect == "stale_source":
            src.events = [e for e in src.events if e[0] != day]
            self._mark(None, [])
        elif defect == "late_arrival":
            # Settled two days before `day`, stamped then, but delivered only now:
            # older than watermark - lookback, so a cursor alone will never see it.
            stamped = day - 2
            orders = [o for o in self._totals if self._totals[o][1] < _ts(stamped, 86399)]
            placed = [o for o in orders
                      if src.latest("sales.orders", day)[(str(o),)]["status"] == "placed"]
            picked = rng.sample(placed, min(3, len(placed)))
            keys = []
            for oid in picked:
                ts = _ts(stamped, 3 * 3600 + rng.randrange(0, 3000))
                src.put(day, "sales.payments", {
                    "payment_id": str(self._next_payment), "order_id": str(oid),
                    "amount": str(self._totals[oid][0]),
                    "settled_date": day_date(stamped).isoformat(), "updated_at": ts,
                    "is_deleted": "false"})
                keys.append((str(self._next_payment),))
                self._next_payment += 1
            self._mark("sales.payments", keys)
