"""Pure quality-gate logic for Track 2's Silver quarantine and Gold publication
gate -- spark/dlt-free, so it's unit testable in plain pytest. Same pattern as
transforms.py: silver.py/gold.py reimplement this logic as native Spark column
expressions; this module is the tested spec they must match.

Business decision (chapter 02): reject individual records by default -- a
malformed value, a duplicate lead_id, or an orphaned campaign_id only removes
that one row from `<source>_clean` and routes it to `<source>_quarantine` with
a reason code. Only when a run's quarantine rate for a source crosses
QUARANTINE_RATE_THRESHOLD does the gate withhold that source's Gold tables,
leaving their previously published content unchanged, instead of publishing an
aggregate built from a materially degraded sample. The generator's baseline
invalid rate is ~2% (INVALID_RATE in generator.py); 10% is five times that
baseline -- past it, the deviation is more likely a systemic pipeline problem
(a broken upstream mapping, a bad deploy) than expected background noise, and
Genie/BI users are better served by stale-but-correct numbers than by a
silently degraded refresh.
"""

QUARANTINE_RATE_THRESHOLD = 0.10

VALID_STAGES = {"new", "qualified", "won", "lost"}


def dedup_by_key(rows: list[dict], key: str) -> tuple[list[dict], list[dict]]:
    """Split rows into (kept, duplicates) by `key`, keeping the first
    occurrence in input order. Callers must supply rows in a deterministic
    order (e.g. Bronze's `_row_id`), not something tied like a shared
    per-run timestamp.
    """
    seen = set()
    kept, dups = [], []
    for row in rows:
        k = row[key]
        if k in seen:
            dups.append(row)
        else:
            seen.add(k)
            kept.append(row)
    return kept, dups


def classify_lead(lead: dict, known_campaign_ids: set) -> list[str]:
    """Quarantine reason codes for a lead row that has already passed dedup;
    empty list means accepted."""
    reasons = []
    campaign_id = lead.get("campaign_id")
    if campaign_id is None:
        reasons.append("null_campaign_id")
    elif campaign_id not in known_campaign_ids:
        reasons.append("unknown_campaign_id")
    if lead.get("stage") not in VALID_STAGES:
        reasons.append("invalid_stage")
    return reasons


def classify_web_event(event: dict, known_campaign_ids: set) -> list[str]:
    reasons = []
    campaign_id = event.get("campaign_id")
    if campaign_id is None:
        reasons.append("null_campaign_id")
    elif campaign_id not in known_campaign_ids:
        reasons.append("unknown_campaign_id")
    if event.get("session_duration_seconds") is None or event["session_duration_seconds"] < 0:
        reasons.append("invalid_duration")
    return reasons


def classify_ops_event(event: dict) -> list[str]:
    reasons = []
    latency = event.get("latency_seconds")
    if latency is None or latency < 0:
        reasons.append("invalid_latency")
    return reasons


def reconcile(rows: list[dict], key: str, classify_fn, *classify_args) -> tuple[list[dict], list[tuple[dict, list[str]]]]:
    """Dedup then classify. Returns (accepted, quarantined) where quarantined
    is a list of (row, reasons) pairs -- duplicates get reason
    `duplicate_<key>`. Every input row appears in exactly one output list
    (conservation), which is what "no double-counting" means at this layer.
    """
    kept, dups = dedup_by_key(rows, key)
    accepted: list[dict] = []
    quarantined: list[tuple[dict, list[str]]] = []
    for row in kept:
        reasons = classify_fn(row, *classify_args)
        if reasons:
            quarantined.append((row, reasons))
        else:
            accepted.append(row)
    for dup in dups:
        quarantined.append((dup, [f"duplicate_{key}"]))
    assert len(accepted) + len(quarantined) == len(rows), "reconcile must conserve every input row"
    return accepted, quarantined


def quarantine_rate(total: int, quarantined: int) -> float:
    if total == 0:
        return 0.0
    return quarantined / total


def gate_passed(total: int, quarantined: int, threshold: float = QUARANTINE_RATE_THRESHOLD) -> bool:
    """True if this run's quarantine rate is within the accepted threshold --
    i.e. the affected Gold tables should refresh normally. False means the
    caller should withhold that refresh and keep previously published data."""
    return quarantine_rate(total, quarantined) <= threshold
