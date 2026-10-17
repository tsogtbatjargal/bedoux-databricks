"""Legacy-vs-lakehouse reconciliation: the parallel-run gate before cutover.

Compares two row sets on a business key. Counts must match exactly; money within a
tolerance. Returns a report, never raises on mismatch: the caller decides whether a
failed report blocks cutover (the job task does).
"""

KEY = ("domain", "region", "product_category", "order_date")
EXACT = ("order_count", "units")
MONEY = ("revenue",)
TOLERANCE = 0.01


def _index(rows, key):
    out = {}
    for r in rows:
        k = tuple(r[c] for c in key)
        if k in out:
            raise ValueError(f"duplicate key {k}: reconciliation needs a unique key")
        out[k] = r
    return out


def reconcile(new_rows, legacy_rows, key=KEY, exact=EXACT, money=MONEY,
              tolerance=TOLERANCE, sample=10):
    new, old = _index(new_rows, key), _index(legacy_rows, key)
    only_new = sorted(set(new) - set(old))
    only_legacy = sorted(set(old) - set(new))
    mismatches = []
    for k in sorted(set(new) & set(old)):
        for col in exact:
            if new[k][col] != old[k][col]:
                mismatches.append({"key": k, "column": col, "new": new[k][col], "legacy": old[k][col]})
        for col in money:
            if abs(new[k][col] - old[k][col]) > tolerance:
                mismatches.append({"key": k, "column": col, "new": new[k][col], "legacy": old[k][col]})
    return {
        "passed": not (only_new or only_legacy or mismatches),
        "new_rows": len(new),
        "legacy_rows": len(old),
        "only_in_new": len(only_new),
        "only_in_legacy": len(only_legacy),
        "value_mismatches": len(mismatches),
        "sample_missing": [list(k) for k in (only_new + only_legacy)[:sample]],
        "sample_mismatches": mismatches[:sample],
    }
