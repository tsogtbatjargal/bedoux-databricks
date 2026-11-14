# Databricks notebook source
# Track 3 cutover gate: reconcile gold_retail_sales_daily against the legacy report.
#
# Collects both tables to the driver (a few thousand synthetic rows) and runs the
# unit-tested src/aglc/reconcile.py. Every run is appended to
# aglc_legacy.reconcile_runs. A failed reconciliation raises, so the job run goes
# red: "cutover not allowed".
#
# Runs as the job identity (an engineer), which the domain row filter lets see
# every domain. Run as an analyst, the filter would hide rows and the gate would
# correctly fail.

# COMMAND ----------

import json
import sys

dbutils.widgets.text("source_path", "")  # noqa: F821
dbutils.widgets.text("catalog", "workspace")  # noqa: F821

source_path = dbutils.widgets.get("source_path")  # noqa: F821
if not source_path:
    raise ValueError("source_path widget is empty; pass ${workspace.file_path}/src")
sys.path.append(source_path)
from aglc import governance, reconcile  # noqa: E402

catalog = governance.ident(dbutils.widgets.get("catalog"))  # noqa: F821

# COMMAND ----------


def _rows(table):
    df = spark.read.table(table).selectExpr(  # noqa: F821
        "domain", "region", "product_category", "CAST(order_date AS STRING) AS order_date",
        "order_count", "units", "CAST(revenue AS DOUBLE) AS revenue",
    )
    return [r.asDict() for r in df.collect()]


report = reconcile.reconcile(
    _rows(f"{catalog}.aglc_gold.gold_retail_sales_daily"),
    _rows(f"{catalog}.aglc_legacy.legacy_retail_sales_daily"),
)
print(json.dumps(report, indent=2, default=str))

spark.sql(  # noqa: F821
    f"CREATE TABLE IF NOT EXISTS {catalog}.aglc_legacy.reconcile_runs "
    "(run_ts TIMESTAMP, passed BOOLEAN, report STRING)"
)
spark.sql(  # noqa: F821
    f"INSERT INTO {catalog}.aglc_legacy.reconcile_runs SELECT current_timestamp(), :passed, :report",
    args={"passed": report["passed"], "report": json.dumps(report, default=str)},
)

if not report["passed"]:
    raise RuntimeError(
        f"Reconciliation failed: {report['only_in_new']} only in new, "
        f"{report['only_in_legacy']} only in legacy, {report['value_mismatches']} value mismatches. "
        "Cutover not allowed."
    )
