"""Agent C: legacy T-SQL to Databricks SQL modernization (Track 4).

A deterministic workflow, not a free-form rewrite:

1. Scan the legacy script for constructs with no safe automatic translation
   (cursors, loops, TRY/CATCH, transactions, temp tables, dynamic SQL,
   @@ROWCOUNT, non-deterministic clock functions). Any hit means
   NEEDS_MANUAL_REDESIGN: no SQL is proposed, the blockers are listed.
2. Parse with SQLGlot (dialect "tsql") and apply this module's semantic
   rewrite rules where SQLGlot's default output would change results:
   - string `+` becomes `||` (Databricks `+` is numeric),
   - LEN(x) becomes LENGTH(RTRIM(x)) (T-SQL LEN ignores trailing spaces).
   Each applied rule is listed in the report.
3. Generate Databricks SQL, then record warnings for behaviour that changed
   but was kept deliberately (CONVERT becoming TRY_CAST, dropped lock hints).
4. Validate: execute the generated SQL against fixture tables and compare with
   an independently written reference query. VALIDATED only on an exact match
   after normalization (order kept when the query orders and limits).

Limitation, stated in every report: execution is local DuckDB, reached by
transpiling the generated Databricks SQL once more. It is evidence about the
logic on fixtures, not proof of behaviour on a Databricks SQL warehouse.
"""

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import sqlglot
from sqlglot import exp

VALIDATED = "validated"
MISMATCH = "mismatch"
NEEDS_MANUAL_REDESIGN = "needs_manual_redesign"
TRANSPILE_ERROR = "transpile_error"
EXECUTION_ERROR = "execution_error"

LIMITATION = ("Validated on local DuckDB fixtures via a second transpilation; "
              "not executed on a Databricks SQL warehouse.")

# (code, pattern) scanned on the legacy text with comments stripped.
BLOCKERS = (
    ("cursor", r"\bDECLARE\s+\w+\s+CURSOR\b|\bFETCH\s+NEXT\b"),
    ("while_loop", r"\bWHILE\b"),
    ("try_catch", r"\bBEGIN\s+TRY\b|\bBEGIN\s+CATCH\b"),
    ("transaction", r"\bBEGIN\s+TRAN(SACTION)?\b|\bCOMMIT\b|\bROLLBACK\b"),
    ("temp_table", r"(?<![\w@])#\w+"),
    ("dynamic_sql", r"\bsp_executesql\b|\bEXEC(UTE)?\s*\("),
    ("rowcount_error_globals", r"@@(ROWCOUNT|ERROR|TRANCOUNT)\b"),
    ("nondeterministic_clock", r"\b(GETDATE|SYSDATETIME|CURRENT_TIMESTAMP|GETUTCDATE)\b"),
)

_STRING_TYPES = {exp.DataType.Type.VARCHAR, exp.DataType.Type.NVARCHAR,
                 exp.DataType.Type.CHAR, exp.DataType.Type.NCHAR, exp.DataType.Type.TEXT}


def _strip_comments(sql):
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


def scan_blockers(sql):
    text = _strip_comments(sql)
    return sorted({code for code, pattern in BLOCKERS if re.search(pattern, text, re.IGNORECASE)})


def _is_stringish(node):
    if isinstance(node, exp.Literal) and node.is_string:
        return True
    if isinstance(node, (exp.Cast, exp.TryCast)) and node.to.this in _STRING_TYPES:
        return True
    if isinstance(node, exp.DPipe):
        return True
    return isinstance(node, exp.Add) and (_is_stringish(node.this) or _is_stringish(node.expression))


def semantic_hazards(tree):
    """Constructs SQLGlot translates without error but whose meaning differs
    between T-SQL and Databricks in a way the local DuckDB check can't see
    (DuckDB happens to share the T-SQL behaviour, so a second transpilation
    hides the difference). Found by review of sql17; see docs/contracts-adp.md.
    """
    hazards = set()
    for node in tree.find_all(exp.DateDiff):
        unit = (node.text("unit") or "DAY").upper()
        if unit not in ("DAY", "DD", "D"):
            # T-SQL counts unit boundaries crossed; Databricks counts whole
            # units elapsed (Oct 1 -> Nov 1 00:00 is 1 month vs 0).
            hazards.add("datediff_boundary_semantics")
    return sorted(hazards)


def _is_int_operand(node, int_columns):
    if isinstance(node, exp.Paren):
        return _is_int_operand(node.this, int_columns)
    if isinstance(node, exp.Literal):
        return not node.is_string and node.this.lstrip("-").isdigit()
    if isinstance(node, exp.Column):
        return node.name.lower() in int_columns
    if isinstance(node, exp.Cast):
        return node.to.this in {exp.DataType.Type.INT, exp.DataType.Type.BIGINT,
                                exp.DataType.Type.SMALLINT, exp.DataType.Type.TINYINT}
    return False


def _is_trailing_trim(node):
    return isinstance(node, exp.Trim) and str(node.args.get("position", "")).upper() == "TRAILING"


def _rewrite(tree, int_columns=frozenset()):
    """Apply the semantic rules children-first, so nested expressions such as
    a + '-' + b are rewritten at every level."""
    applied = set()
    for node in reversed(list(tree.dfs())):
        if isinstance(node, exp.Add) and (_is_stringish(node.this) or _is_stringish(node.expression)):
            node.replace(exp.DPipe(this=node.this, expression=node.expression, safe=True))
            applied.add("string_plus_to_concat")
        elif isinstance(node, exp.Length) and not _is_trailing_trim(node.this):
            node.set("this", exp.Trim(this=node.this, position="TRAILING"))
            applied.add("len_ignores_trailing_spaces")
        elif isinstance(node, exp.Div) and _is_int_operand(node.this, int_columns) \
                and _is_int_operand(node.expression, int_columns):
            node.replace(exp.IntDiv(this=node.this, expression=node.expression))
            applied.add("integer_division")
    return tree, sorted(applied)


def _warnings(legacy_tree, generated_sql):
    warnings = []
    if "TRY_CAST" in generated_sql.upper() and not legacy_tree.find(exp.TryCast):
        warnings.append("convert_became_try_cast: invalid input now yields NULL instead of an error")
    if re.search(r"\bNOLOCK\b", legacy_tree.sql(dialect="tsql"), re.IGNORECASE) or \
            legacy_tree.find(exp.WithTableHint):
        warnings.append("lock_hint_dropped: Delta reads are snapshot-isolated")
    return warnings


def translate(legacy_sql, int_columns=frozenset()):
    """Return a report dict without executing anything.

    `int_columns` (lower-case names) enables the integer-division rule: T-SQL
    int / int truncates, Databricks `/` does not. Without a schema the rule
    can't fire and validation is what catches the difference.
    """
    report = {"status": None, "blockers": scan_blockers(legacy_sql), "rewrites": [],
              "warnings": [], "databricks_sql": None, "error": None, "limitation": LIMITATION}
    if report["blockers"]:
        report["status"] = NEEDS_MANUAL_REDESIGN
        return report
    try:
        trees = sqlglot.parse(legacy_sql, read="tsql")
        if len(trees) != 1 or trees[0] is None or isinstance(trees[0], exp.Command):
            raise ValueError("expected exactly one parseable statement")
        legacy_tree = trees[0]
        hazards = semantic_hazards(legacy_tree)
        if hazards:
            report.update(status=NEEDS_MANUAL_REDESIGN, blockers=hazards)
            return report
        rewritten, report["rewrites"] = _rewrite(legacy_tree.copy(), int_columns)
        report["databricks_sql"] = rewritten.sql(dialect="databricks", pretty=True)
        report["warnings"] = _warnings(legacy_tree, report["databricks_sql"])
    except Exception as exc:  # parse errors carry SQL text, not data
        report.update(status=TRANSPILE_ERROR, error=type(exc).__name__ + ": " + str(exc)[:200])
    return report


def _norm_value(v):
    if isinstance(v, float):
        v = Decimal(repr(v))
    if isinstance(v, Decimal):
        return str(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if isinstance(v, datetime):
        return v.date().isoformat() if v.time() == datetime.min.time() else v.isoformat(sep=" ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, int) and not isinstance(v, bool):
        return str(Decimal(v).quantize(Decimal("0.01")))
    return v


def _normalize(rows, ordered):
    out = [tuple(_norm_value(v) for v in row) for row in rows]
    return out if ordered else sorted(out, key=lambda r: tuple((x is None, str(x)) for x in r))


def _ordered(sql):
    tree = sqlglot.parse_one(sql, read="duckdb")
    return bool(tree.args.get("order") and tree.args.get("limit"))


def validate(report, reference_sql, connection):
    """Execute generated vs reference on `connection` (a DuckDB connection
    with fixtures loaded). Mutates and returns `report`."""
    if report["status"] is not None:
        return report
    try:
        duck_sql = sqlglot.transpile(report["databricks_sql"], read="databricks", write="duckdb")[0]
        got = connection.execute(duck_sql).fetchall()
    except Exception as exc:
        report.update(status=EXECUTION_ERROR, error=type(exc).__name__ + ": " + str(exc)[:200])
        return report
    want = connection.execute(reference_sql).fetchall()
    ordered = _ordered(reference_sql)
    g, w = _normalize(got, ordered), _normalize(want, ordered)
    report["rows_compared"] = len(w)
    if g == w:
        report["status"] = VALIDATED
    else:
        report["status"] = MISMATCH
        missing = [r for r in w if r not in g][:5]
        extra = [r for r in g if r not in w][:5]
        report["diff_sample"] = {"expected_not_produced": missing, "produced_not_expected": extra,
                                 "order_only": not missing and not extra}
    return report


FIXTURES = Path(__file__).resolve().parents[2] / "migrations" / "adp" / "fixtures.sql"
CASES = Path(__file__).resolve().parents[2] / "migrations" / "adp" / "cases.yml"


def fixture_connection(path=FIXTURES):
    import duckdb  # dev dependency; not needed to translate

    con = duckdb.connect(":memory:")
    con.execute(Path(path).read_text())
    return con


def int_columns_of(connection):
    """Column names that are integer-typed in every fixture table that has them."""
    rows = connection.execute(
        "SELECT lower(column_name), bool_and(data_type IN ('INTEGER','BIGINT','SMALLINT','TINYINT')) "
        "FROM information_schema.columns GROUP BY 1").fetchall()
    return frozenset(name for name, all_int in rows if all_int)


def modernize(legacy_sql, reference_sql=None, connection=None, *, use_schema=True):
    ints = int_columns_of(connection) if connection is not None and use_schema else frozenset()
    report = translate(legacy_sql, ints)
    if reference_sql is not None and connection is not None:
        validate(report, reference_sql, connection)
    return report
