# Databricks notebook source
# Track 3: write the simulated legacy report (aglc_legacy.legacy_retail_sales_daily).
#
# Stands in for the export of an old SSIS-loaded, SSRS-rendered report. Computed
# in plain Python by src/aglc/legacy.py, independent of the lakehouse pipelines,
# so the reconciliation compares two implementations. `inject_discrepancy`
# (none | revenue | missing_row) proves the reconciliation catches a real diff.

# COMMAND ----------

import sys

dbutils.widgets.text("source_path", "")  # noqa: F821
dbutils.widgets.text("catalog", "workspace")  # noqa: F821
dbutils.widgets.text("inject_discrepancy", "none")  # noqa: F821

source_path = dbutils.widgets.get("source_path")  # noqa: F821
if not source_path:
    raise ValueError("source_path widget is empty; pass ${workspace.file_path}/src")
sys.path.append(source_path)
from aglc import generator, governance, legacy  # noqa: E402

catalog = governance.ident(dbutils.widgets.get("catalog"))  # noqa: F821
inject = dbutils.widgets.get("inject_discrepancy")  # noqa: F821

# COMMAND ----------

licensees = generator.generate_licensees()
rows = legacy.retail_sales_daily(generator.generate_orders(licensees), licensees, inject_discrepancy=inject)

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.aglc_legacy")  # noqa: F821
(
    spark.createDataFrame(  # noqa: F821
        rows,
        schema="domain STRING, region STRING, product_category STRING, order_date STRING, "
               "order_count LONG, units LONG, revenue DOUBLE",
    )
    .write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.aglc_legacy.legacy_retail_sales_daily")
)
print(f"legacy_retail_sales_daily: {len(rows)} rows (inject_discrepancy={inject})")
