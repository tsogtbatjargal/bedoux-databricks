"""Pure logic for the append-only gate-evidence log (chapter 03) -- spark/
dlt/network-free, unit testable in plain pytest, same split as quality.py/
evidence.py. See docs/sentinel/chapters/03-protect-evidence.md's "Append-only
evidence log" sections for the design this implements and what it does and
does not close.

This module makes no gate decisions of its own: passed/problems always come
from quality.evaluate_gate, copied verbatim. It only shapes gate_check.py's
already-collected inputs into one durable row and runs that row through
evidence.py's redaction/canary gate before the caller (gate_check.py's thin
Spark writer) appends it.
"""

from datetime import datetime

from . import evidence, quality

EVIDENCE_LOG_TABLE = "workspace.bedoux_silver.gate_evidence_log"

_SOURCE_ROW_FIELDS = (
    "source", "gate_passed", "conserved", "total", "quarantined",
    "accepted_rows", "quarantined_rows", "quarantine_rate",
)


def _build_source_entry(row):
    entry = {field: (row.get(field) if isinstance(row, dict) else None) for field in _SOURCE_ROW_FIELDS}
    entry["computed_ts"] = row.get("_computed_ts") if isinstance(row, dict) else None
    return entry


def build_evidence_record(rows, passed, problems, run_start_ms, written_ts):
    """Build one append-only evidence-log row from exactly what gate_check.py
    already has right after calling quality.evaluate_gate: the collected
    gate_status rows, the verdict, the problem strings, and the run's
    declared start.

    Fails closed on a malformed run identity: a non-positive/non-integer
    run_start_ms or a written_ts that isn't an aware datetime raises
    ValueError rather than building a row that would misattribute a
    decision to the wrong run -- a row with a fabricated run identity is
    worse than no row. A malformed individual source row (not a dict, or
    missing fields) is not fatal: it is still recorded, with whatever
    fields are present and the rest None, rather than silently dropped --
    dropping it would lose evidence, not just skip a detail.
    """
    if isinstance(run_start_ms, bool) or not isinstance(run_start_ms, int) or run_start_ms <= 0:
        raise ValueError("run_start_ms must be a positive epoch-millisecond integer")
    if not isinstance(written_ts, datetime) or written_ts.utcoffset() is None:
        raise ValueError("written_ts must be a timezone-aware datetime")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list of gate_status records")

    sources = [
        _build_source_entry(row)
        for row in sorted(rows, key=lambda r: str(r.get("source")) if isinstance(r, dict) else str(r))
    ]

    return {
        "run_start_ms": run_start_ms,
        "run_start_ts": quality.utc_from_epoch_ms(run_start_ms),
        "written_ts": written_ts,
        "passed": bool(passed),
        "problems": list(problems) if problems else [],
        "sources": sources,
    }


def gate_and_redact(record):
    """Run `record` through evidence.py's redaction/canary gate before it is
    ever written -- evaluate_evidence_gate's first real caller in this
    project. Always returns a packet safe to write: redact_evidence_packet's
    output, with `passed` forced False and the evidence gate's own problems
    appended to `problems` if evaluate_evidence_gate objects. Blocking never
    means losing the row -- it means the row records that the evidence gate
    itself fired, which should not happen against gate_status-derived fields
    but must not silently vanish if it ever does.

    Not the roadmap's "a failed check prevents the external call" criterion:
    a Delta append is not an external call. This is the same control shape
    applied to a durable boundary instead -- see the chapter doc.
    """
    allowed, evidence_problems = evidence.evaluate_evidence_gate(record)
    packet = evidence.redact_evidence_packet(record)
    if not allowed:
        packet["passed"] = False
        packet["problems"] = list(packet.get("problems", [])) + evidence_problems
    return packet
