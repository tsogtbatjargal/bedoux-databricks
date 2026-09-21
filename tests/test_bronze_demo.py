"""Exercise Bronze configuration wiring with stubs; no Spark/DLT execution."""

import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_bronze(monkeypatch, rate=None):
    monkeypatch.setattr(sys, "path", sys.path.copy())
    dlt = ModuleType("dlt")
    dlt.table = lambda **_kwargs: lambda fn: fn
    functions = ModuleType("pyspark.sql.functions")
    functions.current_timestamp = lambda: "synthetic-audit-time"
    functions.lit = lambda value: value
    for name, module in [("dlt", dlt), ("pyspark", ModuleType("pyspark")),
                         ("pyspark.sql", ModuleType("pyspark.sql")),
                         ("pyspark.sql.functions", functions)]:
        monkeypatch.setitem(sys.modules, name, module)
    settings = {"bundle.sourcePath": str(ROOT / "src")}
    if rate is not None:
        settings["bedoux.lead_invalid_rate"] = rate

    class Frame:
        def __init__(self, rows, schema):
            self.rows, self.schema = rows, schema

        def withColumn(self, *_args):
            return self

    spark = SimpleNamespace(conf=SimpleNamespace(get=settings.get), createDataFrame=Frame)
    return runpy.run_path(str(ROOT / "src/bedoux/bronze.py"), init_globals={"spark": spark})


@pytest.mark.parametrize("rate", ["0", "1"])
def test_lead_pipeline_reads_demo_setting_and_provides_schema(monkeypatch, rate):
    bronze = load_bronze(monkeypatch, rate)
    frame = bronze["leads_raw"]()
    assert "campaign_id LONG" in frame.schema
    assert sum(row["campaign_id"] is None for row in frame.rows) == int(rate) * 500
    assert [row["_row_id"] for row in frame.rows] == list(range(500))


def test_pipeline_default_equals_explicit_normal_fixture(monkeypatch):
    default_rows = load_bronze(monkeypatch)["leads_raw"]().rows
    assert default_rows == load_bronze(monkeypatch, "0.02")["leads_raw"]().rows


def test_pipeline_rejects_bad_setting_before_dataframe_creation(monkeypatch):
    with pytest.raises(ValueError):
        load_bronze(monkeypatch, "nan")["leads_raw"]()
