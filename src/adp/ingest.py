"""Metadata-driven incremental ingestion with audit records (Track 4).

Pure Python. The same engine runs in pytest and inside the Databricks task
(src/adp/ingest_task.py), which only adds Delta reads and writes around it.

Rules, each covered by tests/test_adp_ingest.py:

- Cursor: composite (cursor_column, *primary_key). A row is new if its cursor
  is greater than the stored watermark, so rows sharing one timestamp are never
  skipped at a batch boundary.
- Lookback: the read window starts lookback_hours before the watermark, which
  picks up late-arriving versions. Replaying them is safe because the merge is
  deterministic: a version replaces the stored one only if its cursor is newer.
- Schema: a missing required column fails the run before any row is written.
  An added column is recorded in the schema diff and otherwise ignored.
- Rows that fail the contract go to quarantine with their raw payload. If the
  quarantined share exceeds max_quarantine_ratio, the whole run fails and
  nothing is written.
- The watermark advances only after a run succeeds. A failed run leaves the
  watermark and the target exactly as they were.
"""

import copy
import json
from datetime import datetime, timedelta

from . import contracts

SUCCEEDED = "succeeded"
SUCCEEDED_WITH_QUARANTINE = "succeeded_with_quarantine"
FAILED = "failed"

# Run-level failure codes.
SCHEMA_REQUIRED_COLUMN_MISSING = "schema_required_column_missing"
QUARANTINE_RATIO_EXCEEDED = "quarantine_ratio_exceeded"

MAX_QUARANTINE_SAMPLE = 50


def _json_default(value):
    return str(value)


class MetadataStore:
    """Watermarks, audit runs, schema snapshots, quarantine and target tables.

    In memory, serializable to JSON. On Databricks the same fields map to Delta
    tables in the adp_meta schema; see ingest_task.py.
    """

    def __init__(self):
        self.watermarks = {}   # dataset_id -> [cursor_ts_iso, [pk values]]
        self.runs = []         # audit records, append-only
        self.quarantine = {}   # dataset_id -> [{run_id, raw, problems}]
        self.tables = {}       # dataset_id -> {pk tuple: typed row}
        self.schemas = {}      # dataset_id -> last observed column list

    def run(self, run_id):
        return next((r for r in self.runs if r["run_id"] == run_id), None)

    def runs_for(self, dataset_id):
        return [r for r in self.runs if r["dataset_id"] == dataset_id]

    def copy(self):
        return copy.deepcopy(self)

    def to_json(self):
        return json.dumps({
            "watermarks": self.watermarks, "runs": self.runs, "quarantine": self.quarantine,
            "schemas": self.schemas,
            "tables": {ds: [row for row in t.values()] for ds, t in self.tables.items()},
        }, default=_json_default, sort_keys=True)

    @classmethod
    def from_json(cls, text, specs):
        """Inverse of to_json. Target rows are re-typed through their contract,
        so a restored store merges exactly like the one that was saved."""
        raw = json.loads(text)
        store = cls()
        store.watermarks, store.runs = raw["watermarks"], raw["runs"]
        store.quarantine, store.schemas = raw["quarantine"], raw["schemas"]
        for ds, rows in raw["tables"].items():
            spec = specs[ds]
            table = store.tables.setdefault(ds, {})
            for row in rows:
                typed, problems = contracts.validate_row(spec, row)
                if typed is None:
                    raise ValueError(f"stored row of {ds} no longer matches its contract: {problems}")
                table[tuple(typed[k] for k in spec.primary_key)] = typed
        return store


def _cursor(row, spec):
    return (row[spec.cursor_column], tuple(row[k] for k in spec.primary_key))


def _watermark_cursor(store, spec):
    wm = store.watermarks.get(spec.dataset_id)
    if wm is None:
        return None
    return (datetime.fromisoformat(wm[0]), tuple(wm[1]))


def _new_run_id(store, spec, label):
    return f"{spec.dataset_id}:{label}:{len(store.runs_for(spec.dataset_id)) + 1}"


def run_ingestion(spec, source_rows, store, *, label="run"):
    """Ingest one extract into `store`. Returns the audit record (also appended
    to store.runs). Never raises on bad data; a bad batch is a FAILED run."""
    run_id = _new_run_id(store, spec, label)
    wm = _watermark_cursor(store, spec)
    observed = sorted({c for row in source_rows for c in row}) if source_rows else \
        sorted(store.schemas.get(spec.dataset_id, spec.columns))
    diff = contracts.schema_diff(spec, observed)
    record = {
        "run_id": run_id, "dataset_id": spec.dataset_id, "label": label,
        "contract_version": spec.contract_version, "status": None, "failure_code": None,
        "rows_in_source": len(source_rows), "rows_in_window": 0, "rows_new": 0,
        "inserted": 0, "updated": 0, "unchanged": 0, "deleted": 0, "quarantined": 0,
        "quarantine_reasons": {}, "schema_diff": diff,
        "watermark_before": store.watermarks.get(spec.dataset_id),
        "watermark_after": store.watermarks.get(spec.dataset_id),
    }

    if diff["removed_required"]:
        record.update(status=FAILED, failure_code=SCHEMA_REQUIRED_COLUMN_MISSING)
        store.runs.append(record)
        return record

    # Validate everything first: the read window needs a typed cursor.
    typed_rows, quarantined = [], []
    for raw in source_rows:
        typed, problems = contracts.validate_row(spec, raw)
        if typed is None:
            quarantined.append({"run_id": run_id, "raw": dict(raw), "problems": problems})
        else:
            typed_rows.append((typed, raw))

    # Window: rows newer than (watermark - lookback). Quarantined rows whose
    # cursor can't be read are kept; rows that parse but sit before the window
    # are excluded from quarantine too, so old bad rows don't re-fire forever.
    if wm is not None:
        floor = wm[0] - timedelta(hours=spec.lookback_hours)
        typed_rows = [(t, r) for t, r in typed_rows if t[spec.cursor_column] >= floor]
        quarantined = [q for q in quarantined if _in_window(q["raw"], spec, floor)]

    # Same key and cursor with different content: no basis to choose.
    by_cursor = {}
    for typed, raw in typed_rows:
        by_cursor.setdefault(_cursor(typed, spec), []).append((typed, raw))
    accepted = []
    for group in by_cursor.values():
        if len({json.dumps(t, default=_json_default, sort_keys=True) for t, _ in group}) > 1:
            for _, raw in group:
                quarantined.append({"run_id": run_id, "raw": dict(raw), "problems": [
                    {"column": ",".join(spec.primary_key), "reason": contracts.DUPLICATE_KEY}]})
        else:
            accepted.append(group[0][0])

    window = len(accepted) + len(quarantined)
    record["rows_in_window"] = window
    record["quarantined"] = len(quarantined)
    reasons = {}
    for q in quarantined:
        for p in q["problems"]:
            key = f"{p['column']}:{p['reason']}"
            reasons[key] = reasons.get(key, 0) + 1
    record["quarantine_reasons"] = dict(sorted(reasons.items()))

    if window and len(quarantined) / window > spec.max_quarantine_ratio:
        record.update(status=FAILED, failure_code=QUARANTINE_RATIO_EXCEEDED)
        store.quarantine.setdefault(spec.dataset_id, []).extend(quarantined[:MAX_QUARANTINE_SAMPLE])
        store.runs.append(record)
        return record

    # Merge: latest cursor per key wins; replays and older versions are no-ops.
    target = store.tables.setdefault(spec.dataset_id, {})
    max_cursor = wm
    for typed in sorted(accepted, key=lambda t: _cursor(t, spec)):
        key = tuple(typed[k] for k in spec.primary_key)
        cur = _cursor(typed, spec)
        if wm is None or cur > wm:
            record["rows_new"] += 1
        existing = target.get(key)
        if existing is not None and _cursor(existing, spec) >= cur:
            record["unchanged"] += 1
        else:
            if spec.deletion_strategy == "tombstone" and typed.get("is_deleted"):
                record["deleted"] += 1
            elif existing is None:
                record["inserted"] += 1
            else:
                record["updated"] += 1
            target[key] = typed
        if max_cursor is None or cur > max_cursor:
            max_cursor = cur

    store.quarantine.setdefault(spec.dataset_id, []).extend(quarantined)
    store.schemas[spec.dataset_id] = observed
    if max_cursor is not None:
        store.watermarks[spec.dataset_id] = [max_cursor[0].isoformat(), list(max_cursor[1])]
    record["watermark_after"] = store.watermarks.get(spec.dataset_id)
    record["status"] = SUCCEEDED_WITH_QUARANTINE if quarantined else SUCCEEDED
    store.runs.append(record)
    return record


def _in_window(raw, spec, floor):
    try:
        return datetime.fromisoformat(str(raw.get(spec.cursor_column))) >= floor
    except ValueError:
        return True


def live_rows(store, dataset_id):
    """Current, non-deleted rows of a target table."""
    return [r for r in store.tables.get(dataset_id, {}).values() if not r.get("is_deleted")]
