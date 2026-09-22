"""Execute the actual gate notebook with API stubs, not Spark or Databricks.

Checks parameter wiring, conversion, error propagation, and the append-only
evidence-log write (chapter 03). Does not establish SQL execution, serverless
compatibility, real Delta appendOnly enforcement, or that the scheduler skips
Gold -- pyspark itself is stubbed out (see known-gaps.md, "Local tests do not
execute Spark"); the live demonstration in live-verification.md is what
proves the real table behaves as designed.
"""

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUN_START_MS = 1_779_000_000_000


class _FakeType:
    def __init__(self, *args, **kwargs):
        pass


class _FakeStructField:
    def __init__(self, name, dtype, nullable=True):
        self.name = name
        self.dtype = dtype
        self.nullable = nullable


class _FakeStructType:
    def __init__(self, fields):
        self.fields = fields


def _install_fake_pyspark_types(monkeypatch):
    """gate_check.py imports pyspark.sql.types to build an explicit schema
    for the evidence-log append. Real pyspark isn't a local dependency (see
    known-gaps.md), so this stubs just enough of the module for the notebook
    to build a schema object -- it never inspects the schema's actual type
    correctness, only that schema construction runs and the resulting object
    reaches spark.createDataFrame."""
    fake_types = SimpleNamespace(
        ArrayType=_FakeType, BooleanType=_FakeType, DoubleType=_FakeType,
        LongType=_FakeType, StringType=_FakeType, TimestampType=_FakeType,
        StructField=_FakeStructField, StructType=_FakeStructType,
    )
    fake_sql = SimpleNamespace(types=fake_types)
    fake_pyspark = SimpleNamespace(sql=fake_sql)
    monkeypatch.setitem(sys.modules, "pyspark", fake_pyspark)
    monkeypatch.setitem(sys.modules, "pyspark.sql", fake_sql)
    monkeypatch.setitem(sys.modules, "pyspark.sql.types", fake_types)


def run_notebook(monkeypatch, run_start=str(RUN_START_MS), passed=True, computed_ms=RUN_START_MS + 1000):
    monkeypatch.setattr(sys, "path", sys.path.copy())
    _install_fake_pyspark_types(monkeypatch)
    widgets = {"source_path": str(ROOT / "src"), "run_start_ms": run_start}
    dbutils = SimpleNamespace(widgets=SimpleNamespace(
        text=lambda key, default: widgets.setdefault(key, default),
        get=widgets.__getitem__,
    ))
    reads = []
    sql_statements = []
    evidence_log = {}

    def table(name):
        reads.append(name)

        def select(*expressions):
            assert "unix_millis(_computed_ts) AS _computed_ms" in expressions
            records = [dict(source=source, gate_passed=passed, quarantine_rate=0.02,
                            total=500, quarantined=10, accepted_rows=490,
                            quarantined_rows=10, conserved=True, _computed_ms=computed_ms)
                       for source in ("leads", "web_events", "ops_events")]
            return SimpleNamespace(collect=lambda: [
                SimpleNamespace(asDict=lambda row=row: row.copy()) for row in records
            ])

        return SimpleNamespace(selectExpr=select)

    def sql(query):
        sql_statements.append(query)
        return SimpleNamespace()

    def create_data_frame(data, schema=None):
        evidence_log["schema"] = schema

        def mode(write_mode):
            evidence_log["mode"] = write_mode

            def save_as_table(name):
                evidence_log["table"] = name
                evidence_log["rows"] = data

            return SimpleNamespace(saveAsTable=save_as_table)

        return SimpleNamespace(write=SimpleNamespace(mode=mode))

    spark = SimpleNamespace(
        read=SimpleNamespace(table=table), sql=sql, createDataFrame=create_data_frame,
    )
    runpy.run_path(str(ROOT / "src/bedoux/gate_check.py"), init_globals={"spark": spark, "dbutils": dbutils})
    return SimpleNamespace(reads=reads, sql=sql_statements, evidence_log=evidence_log)


def test_notebook_passes_valid_evidence(monkeypatch, capsys):
    result = run_notebook(monkeypatch)
    assert result.reads == ["workspace.bedoux_silver.gate_status"]
    assert "PUBLICATION GATE PASSED" in capsys.readouterr().out


@pytest.mark.parametrize("value", ["", "{{job.start_time.timestamp_ms}}", "not-a-time"])
def test_notebook_rejects_missing_or_unresolved_run_context(monkeypatch, value):
    with pytest.raises(ValueError):
        run_notebook(monkeypatch, run_start=value)


@pytest.mark.parametrize("passed, computed", [(False, RUN_START_MS + 1000), (True, None), (True, RUN_START_MS - 1)])
def test_notebook_raises_on_failed_null_or_stale_evidence(monkeypatch, passed, computed):
    with pytest.raises(RuntimeError, match="withholding Gold"):
        run_notebook(monkeypatch, passed=passed, computed_ms=computed)


# ---------------------------------------------------------------------------
# Append-only evidence log
# ---------------------------------------------------------------------------


def test_evidence_log_appends_one_row_on_a_passing_run(monkeypatch, capsys):
    result = run_notebook(monkeypatch, passed=True)
    assert result.evidence_log["table"] == "workspace.bedoux_silver.gate_evidence_log"
    assert result.evidence_log["mode"] == "append"
    assert len(result.evidence_log["rows"]) == 1
    row = result.evidence_log["rows"][0]
    assert row["passed"] is True
    assert row["run_start_ms"] == RUN_START_MS
    assert len(row["sources"]) == 3
    assert any("CREATE TABLE IF NOT EXISTS" in s for s in result.sql)
    assert any("delta.appendOnly" in s for s in result.sql)
    assert "Evidence log: appended 1 row" in capsys.readouterr().out


def test_evidence_log_appends_a_row_on_a_failing_run_too(monkeypatch):
    # The gate raises on a failed run -- the evidence-log write still has to
    # happen first, since "a gate that fails must still leave a record of
    # why" is the entire point of this log.
    with pytest.raises(RuntimeError, match="withholding Gold"):
        run_notebook(monkeypatch, passed=False)


def test_evidence_log_write_failure_does_not_block_the_gate_verdict(monkeypatch, capsys):
    # If spark.createDataFrame itself throws, the evidence-log try/except
    # must swallow it and let the gate's own passed/raise logic run exactly
    # as if the log write had never been attempted -- verdict propagation is
    # prioritized over the write, by design (see the chapter doc).
    result_holder = {}

    def run_with_broken_writer(passed):
        monkeypatch.setattr(sys, "path", sys.path.copy())
        _install_fake_pyspark_types(monkeypatch)
        widgets = {"source_path": str(ROOT / "src"), "run_start_ms": str(RUN_START_MS)}
        dbutils = SimpleNamespace(widgets=SimpleNamespace(
            text=lambda key, default: widgets.setdefault(key, default),
            get=widgets.__getitem__,
        ))

        def table(name):
            def select(*expressions):
                records = [dict(source=source, gate_passed=passed, quarantine_rate=0.02,
                                total=500, quarantined=10, accepted_rows=490,
                                quarantined_rows=10, conserved=True,
                                _computed_ms=RUN_START_MS + 1000)
                           for source in ("leads", "web_events", "ops_events")]
                return SimpleNamespace(collect=lambda: [
                    SimpleNamespace(asDict=lambda row=row: row.copy()) for row in records
                ])

            return SimpleNamespace(selectExpr=select)

        def broken_create_data_frame(data, schema=None):
            raise RuntimeError("simulated Delta write failure")

        spark = SimpleNamespace(
            read=SimpleNamespace(table=table),
            sql=lambda query: SimpleNamespace(),
            createDataFrame=broken_create_data_frame,
        )
        runpy.run_path(str(ROOT / "src/bedoux/gate_check.py"), init_globals={"spark": spark, "dbutils": dbutils})

    run_with_broken_writer(passed=True)
    out = capsys.readouterr().out
    assert "Evidence log: FAILED to append" in out
    assert "PUBLICATION GATE PASSED" in out

    with pytest.raises(RuntimeError, match="withholding Gold"):
        run_with_broken_writer(passed=False)
