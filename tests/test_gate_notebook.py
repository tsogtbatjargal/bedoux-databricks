"""Execute the actual gate notebook with API stubs, not Spark or Databricks.

Checks parameter wiring, conversion, and error propagation. Does not establish
SQL execution, serverless compatibility, or that the scheduler skips Gold.
"""

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUN_START_MS = 1_779_000_000_000


def run_notebook(monkeypatch, run_start=str(RUN_START_MS), passed=True, computed_ms=RUN_START_MS + 1000):
    monkeypatch.setattr(sys, "path", sys.path.copy())
    widgets = {"source_path": str(ROOT / "src"), "run_start_ms": run_start}
    dbutils = SimpleNamespace(widgets=SimpleNamespace(
        text=lambda key, default: widgets.setdefault(key, default),
        get=widgets.__getitem__,
    ))
    reads = []

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

    spark = SimpleNamespace(read=SimpleNamespace(table=table))
    runpy.run_path(str(ROOT / "src/bedoux/gate_check.py"), init_globals={"spark": spark, "dbutils": dbutils})
    return reads


def test_notebook_passes_valid_evidence(monkeypatch, capsys):
    assert run_notebook(monkeypatch) == ["workspace.bedoux_silver.gate_status"]
    assert "PUBLICATION GATE PASSED" in capsys.readouterr().out


@pytest.mark.parametrize("value", ["", "{{job.start_time.timestamp_ms}}", "not-a-time"])
def test_notebook_rejects_missing_or_unresolved_run_context(monkeypatch, value):
    with pytest.raises(ValueError):
        run_notebook(monkeypatch, run_start=value)


@pytest.mark.parametrize("passed, computed", [(False, RUN_START_MS + 1000), (True, None), (True, RUN_START_MS - 1)])
def test_notebook_raises_on_failed_null_or_stale_evidence(monkeypatch, passed, computed):
    with pytest.raises(RuntimeError, match="withholding Gold"):
        run_notebook(monkeypatch, passed=passed, computed_ms=computed)
