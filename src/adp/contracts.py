"""Contract checks: schema diff and row validation against a DatasetSpec.

Source extracts arrive as strings (CSV, REST, a JDBC dump). Each value is cast
by its declared type; a value that cannot be cast is never coerced (no silent
zero, no silent null). The row goes to quarantine with its raw payload and a
reason code instead.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Row-level reason codes. Stable strings: the investigator, the eval set and the
# runbooks all key on them.
MISSING_REQUIRED = "missing_required"
CAST_FAILED = "cast_failed"
INVALID_ENUM = "invalid_enum"
NULL_PRIMARY_KEY = "null_primary_key"
DUPLICATE_KEY = "duplicate_key"


def schema_diff(spec, observed_columns):
    """Compare the columns a source delivered with the contract."""
    observed = set(observed_columns)
    declared = set(spec.columns)
    return {
        "added": sorted(observed - declared),
        "removed": sorted(declared - observed),
        "removed_required": sorted(c.name for c in spec.required_columns if c.name not in observed),
    }


def _cast(value, column):
    if column.type == "string":
        return str(value)
    text = str(value).strip()
    if column.type == "int":
        if not text.lstrip("-").isdigit():
            raise ValueError
        return int(text)
    if column.type == "decimal":
        try:
            d = Decimal(text)
        except InvalidOperation:
            raise ValueError from None
        if not d.is_finite():
            raise ValueError
        return d.quantize(Decimal(1).scaleb(-column.scale))
    if column.type == "date":
        return date.fromisoformat(text)
    if column.type == "timestamp":
        return datetime.fromisoformat(text)
    if column.type == "bool":
        if text.lower() not in ("true", "false"):
            raise ValueError
        return text.lower() == "true"
    if column.type == "enum":
        return text
    raise ValueError(f"unhandled type {column.type}")


def validate_row(spec, raw):
    """Return (typed_row, None) or (None, [{"column", "reason"}...]).

    Every problem in the row is reported, not just the first, so evidence for
    an incident shows the full shape of a bad batch.
    """
    problems = []
    typed = {}
    for name, column in spec.columns.items():
        value = raw.get(name)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            if column.required:
                code = NULL_PRIMARY_KEY if name in spec.primary_key else MISSING_REQUIRED
                problems.append({"column": name, "reason": code})
            else:
                typed[name] = None
            continue
        try:
            typed[name] = _cast(value, column)
        except ValueError:
            problems.append({"column": name, "reason": CAST_FAILED})
            continue
        if column.type == "enum" and typed[name] not in column.values:
            problems.append({"column": name, "reason": INVALID_ENUM})
    return (None, problems) if problems else (typed, None)
