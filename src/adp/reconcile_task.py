# Databricks notebook source
# Track 4 Gold + reconciliation task (docs/contracts-adp.md).
#
# Reads the engine state written by ingest_task.py, builds Gold daily_revenue,
# runs both deterministic reconciliations (src/adp/reconcile.py) and records
# monitor incidents. Investigation is not run here: the agent works outside the
# workspace against the audit tables, and only with read-only tools.

# COMMAND ----------

import json
import sys

for name, default in [("source_path", ""), ("config_path", ""), ("catalog", "workspace"),
                      ("seed", "7"), ("day", "1"), ("defect", "none"), ("defect_day", "3")]:
    dbutils.widgets.text(name, default)  # noqa: F821
arg = {n: dbutils.widgets.get(n) for n in  # noqa: F821
       ("source_path", "config_path", "catalog", "seed", "day", "defect", "defect_day")}
sys.path.append(arg["source_path"])

from adp import generator, ingest, metadata, pipeline, reconcile  # noqa: E402
from aglc import governance  # noqa: E402

catalog = governance.ident(arg["catalog"])
specs = metadata.load_specs(arg["config_path"])
day = int(arg["day"])
scenario = generator.Scenario(seed=int(arg["seed"]),
                              defect=None if arg["defect"] == "none" else arg["defect"],
                              defect_day=int(arg["defect_day"]))

latest = spark.sql(  # noqa: F821
    f"SELECT state FROM {catalog}.adp_meta.engine_state ORDER BY saved_ts DESC LIMIT 1").collect()
if not latest:
    raise RuntimeError("No engine state; run adp_ingest_task first.")
store = ingest.MetadataStore.from_json(latest[0]["state"], specs)

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.adp_gold")  # noqa: F821
gold = reconcile.daily_revenue(ingest.live_rows(store, "sales.orders"),
                               ingest.live_rows(store, "sales.order_lines"))
spark.createDataFrame(  # noqa: F821
    [(r["business_date"], r["order_count"], r["revenue"]) for r in gold],
    "business_date STRING, order_count BIGINT, revenue DECIMAL(18,2)",
).selectExpr("CAST(business_date AS DATE) AS business_date", "order_count", "revenue")\
    .write.mode("overwrite").saveAsTable(f"{catalog}.adp_gold.daily_revenue")

recon = pipeline.reconcile_day(scenario, specs, store, day)
day_runs = [r for r in store.runs if r["label"] == f"day{day}"][-len(specs):]
incidents = pipeline.detect_incidents(day_runs, recon, day)
print(json.dumps({"recon": recon, "incidents": incidents}, indent=1, default=str))

spark.sql(f"CREATE TABLE IF NOT EXISTS {catalog}.adp_meta.reconcile_runs "  # noqa: F821
          "(saved_ts TIMESTAMP, day INT, passed BOOLEAN, report STRING)")
spark.sql(f"CREATE TABLE IF NOT EXISTS {catalog}.adp_meta.incidents "  # noqa: F821
          "(saved_ts TIMESTAMP, incident_key STRING, trigger STRING, dataset_id STRING, incident STRING)")
passed = recon["source_to_target"]["passed"] and recon["payments_vs_orders"]["passed"]
spark.sql(  # noqa: F821
    f"INSERT INTO {catalog}.adp_meta.reconcile_runs SELECT current_timestamp(), :day, :passed, :report",
    args={"day": day, "passed": passed, "report": json.dumps(recon, default=str)},
)
if incidents:
    spark.createDataFrame(  # noqa: F821
        [(i["incident_key"], i["trigger"], i["dataset_id"], json.dumps(i)) for i in incidents],
        "incident_key STRING, trigger STRING, dataset_id STRING, incident STRING",
    ).selectExpr("current_timestamp() AS saved_ts", "*").write.mode("append")\
        .saveAsTable(f"{catalog}.adp_meta.incidents")
    raise RuntimeError(f"{len(incidents)} incident(s) opened: {[i['incident_key'] for i in incidents]}")
