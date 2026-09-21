"""Pure quality-gate logic for Track 2's Silver quarantine and Gold publication
gate -- spark/dlt-free, so it's unit testable in plain pytest. Same pattern as
transforms.py: silver.py mirrors the classification rules as Spark expressions;
the ordinary gate notebook calls evaluate_gate directly before Gold runs.

Business decision (chapter 02): reject individual records by default -- a
malformed value, a duplicate lead_id, or an orphaned campaign_id only removes
that one row from `<source>_clean` and routes it to `<source>_quarantine` with
a reason code. Only when a run's quarantine rate for a source crosses
QUARANTINE_RATE_THRESHOLD does the gate withhold the whole Gold pipeline,
leaving their previously published content unchanged, instead of publishing an
aggregate built from a materially degraded sample. The generator's baseline
invalid rate is ~2% (INVALID_RATE in generator.py); 10% is five times that
baseline -- past it, the deviation is more likely a systemic pipeline problem
(a broken upstream mapping, a bad deploy) than expected background noise, and
Genie/BI users are better served by stale-but-correct numbers than by a
silently degraded refresh.

A row's reasons are the union of every rule it fails, including
`duplicate_<key>` -- a duplicate row that also has a null campaign_id carries
both. This is a row-conservation model, not a reason-conservation one: the
gate's quarantine rate must be computed from row counts (one row = one unit),
never from a per-reason breakdown, or a multi-reason row inflates the rate.
See reconcile() below and gate_status/_row_counts in silver.py.
"""

from datetime import datetime, timezone

QUARANTINE_RATE_THRESHOLD = 0.10

VALID_STAGES = {"new", "qualified", "won", "lost"}


def dedup_by_key(rows: list[dict], key: str) -> tuple[list[dict], list[dict]]:
    """Split rows into (kept, duplicates) by `key`, keeping the first
    occurrence in input order. Callers must supply rows in a deterministic
    order (e.g. Bronze's `_row_id`), not something tied like a shared
    per-run timestamp.

    A standalone utility, not used by `reconcile` below (which needs
    per-row reasons alongside dedup, not a plain kept/duplicate split) --
    kept for callers that only need pure dedup.
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
    """Classify every row against `classify_fn`, and separately mark it a
    duplicate if its key already appeared earlier in `rows`. A row's reasons
    are the union of both checks -- a row can be both e.g. `null_campaign_id`
    *and* `duplicate_lead_id` at once. This is deliberately richer than
    "duplicates only ever get `duplicate_<key>`": it mirrors silver.py's
    Spark expressions, which evaluate every rule (classification and dedup)
    independently over the same row in one pass rather than short-circuiting
    once a row is known to be a duplicate, so the two must agree on what a
    multi-reason row looks like. It also means a quarantine count broken down
    by reason (see quality_metrics in silver.py) reflects every real problem
    with a row, not just the first one found.

    Returns (accepted, quarantined) where quarantined is a list of
    (row, reasons) pairs. Every input row appears in exactly one output list
    (conservation) -- that property, not exclusivity of reasons, is what "no
    double-counting" means at this layer: a row with two reasons is still one
    row, counted once, in `len(quarantined)`.
    """
    seen: set = set()
    accepted: list[dict] = []
    quarantined: list[tuple[dict, list[str]]] = []
    for row in rows:
        reasons = list(classify_fn(row, *classify_args))
        k = row[key]
        if k in seen:
            reasons.append(f"duplicate_{key}")
        else:
            seen.add(k)
        if reasons:
            quarantined.append((row, reasons))
        else:
            accepted.append(row)
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


# ---------------------------------------------------------------------------
# Publication-gate policy (chapter 02, revised)
#
# The gate decision is made BEFORE the Gold refresh by an orchestration task
# (src/bedoux/gate_check.py, run as bedoux_gate_task between the Silver and
# Gold pipeline tasks), not inside a Gold dataset function. A DLT dataset
# function is declarative: driver-side actions like .count()/.collect() and
# reads of the table being defined are not supported there. Moving the
# decision into a plain job task makes the imperative check legal, lets a
# failure stop the Gold refresh entirely, and means a first-ever run with a
# failing gate publishes nothing rather than publishing rejected data.
#
# The policy is fail-closed: anything other than explicit, fresh, unanimous
# evidence of passing is a failure. Missing sources, duplicated sources, null
# gate_passed values, and stale evidence all block publication.
# ---------------------------------------------------------------------------

REQUIRED_SOURCES = ("leads", "web_events", "ops_events")


def utc_from_epoch_ms(value):
    """Parse job/Spark epoch milliseconds without relying on the driver's timezone."""
    if not (
        type(value) is int
        or (isinstance(value, str) and value.isascii() and value.isdigit())
    ):
        raise ValueError("Expected positive epoch milliseconds; missing or unresolved run context")
    try:
        milliseconds = int(value)
        if milliseconds <= 0:
            raise ValueError
        return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise ValueError("Expected representable positive epoch milliseconds") from None


def _aware_datetime(value):
    return isinstance(value, datetime) and value.utcoffset() is not None


def evaluate_gate(rows, required_sources=REQUIRED_SOURCES, min_computed_ts=None):
    """Decide whether the Gold refresh may proceed.

    `rows` is the collected contents of workspace.bedoux_silver.gate_status as
    a list of dicts with keys: source, gate_passed, quarantine_rate,
    _computed_ts. `min_computed_ts` must be a timezone-aware job start time.
    Older evidence is rejected. Freshness alone does not establish batch
    identity: the demo requires a serialized job and no other writers.

    Returns (passed, problems). `problems` is a list of human-readable strings,
    empty exactly when `passed` is True. Every required source must appear
    exactly once, with gate_passed strictly True, computed at or after
    `min_computed_ts`. Sources outside `required_sources` are ignored: they
    carry no Gold table in this design, so they cannot block publication.
    """
    if not _aware_datetime(min_computed_ts):
        return False, ["Missing or invalid timezone-aware run boundary; withholding Gold"]
    if not required_sources:
        return False, ["No required sources configured; withholding Gold"]
    problems = []
    by_source = {}
    for row in rows:
        by_source.setdefault(row.get("source"), []).append(row)

    for source in required_sources:
        matches = by_source.get(source, [])
        if not matches:
            problems.append(f"{source}: no gate_status row (missing evidence, not a pass)")
            continue
        if len(matches) > 1:
            problems.append(f"{source}: {len(matches)} gate_status rows, expected exactly 1 (ambiguous evidence)")
            continue

        row = matches[0]
        passed = row.get("gate_passed")
        if passed is None:
            problems.append(f"{source}: gate_passed is null (undecided, not a pass)")
        elif passed is not True:
            rate = row.get("quarantine_rate")
            rate_text = "unknown" if rate is None else f"{rate:.1%}"
            problems.append(f"{source}: gate_passed is false (quarantine rate {rate_text})")

        computed = row.get("_computed_ts")
        if computed is None:
            problems.append(f"{source}: _computed_ts is null, cannot prove freshness")
        elif not _aware_datetime(computed):
            problems.append(f"{source}: _computed_ts must be a timezone-aware datetime")
        elif computed < min_computed_ts:
            problems.append(
                f"{source}: gate_status computed at {computed} predates this run "
                f"({min_computed_ts}); stale evidence from an earlier run"
            )

    return (not problems), problems
