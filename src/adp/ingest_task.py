# Databricks notebook source
# Track 4 ingestion task (docs/contracts-adp.md).
#
# Runs one simulated source day through the unit-tested pure-Python engine
# (src/adp/ingest.py) and persists the result to Unity Catalog:
#
#   adp_meta.engine_state   one JSON row per run: watermarks, schemas, merged targets
#   adp_meta.ingest_runs    append-only audit records
#   adp_meta.quarantine     rejected rows with raw payloads
#   adp_bronze.<bronze_name> current merged state of each dataset
#
# Bronze tables are overwritten from the engine's merged state. That is fine at
# this synthetic scale (hundreds of rows) and keeps one merge implementation;
# a production source would use Delta MERGE instead (known gap in the contract).
# Re-running a day is safe: the engine's merge and watermark rules make it a no-op.

# COMMAND ----------

import json
import sys

for name, default in [("source_path", ""), ("config_path", ""), ("catalog", "workspace"),
                      ("seed", "7"), ("day", "1"), ("defect", "none"), ("defect_day", "3")]:
    dbutils.widgets.text(name, default)  # noqa: F821
arg = {n: dbutils.widgets.get(n) for n in  # noqa: F821
       ("source_path", "config_path", "catalog", "seed", "day", "defect", "defect_day")}
if not arg["source_path"] or not arg["config_path"]:
    raise ValueError("source_path and config_path are required")
sys.path.append(arg["source_path"])

from adp import generator, ingest, metadata, pipeline  # noqa: E402
from aglc import governance  # noqa: E402  (identifier quoting, reused from Track 3)

catalog = governance.ident(arg["catalog"])
specs = metadata.load_specs(arg["config_path"])
day = int(arg["day"])
scenario = generator.Scenario(seed=int(arg["seed"]),
                              defect=None if arg["defect"] == "none" else arg["defect"],
                              defect_day=int(arg["defect_day"]))

# COMMAND ----------

for schema in ("adp_meta", "adp_bronze"):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")  # noqa: F821
spark.sql(f"CREATE TABLE IF NOT EXISTS {catalog}.adp_meta.engine_state "  # noqa: F821
          "(saved_ts TIMESTAMP, label STRING, state STRING)")
spark.sql(f"CREATE TABLE IF NOT EXISTS {catalog}.adp_meta.ingest_runs "  # noqa: F821
          "(saved_ts TIMESTAMP, run_id STRING, dataset_id STRING, status STRING, record STRING)")
spark.sql(f"CREATE TABLE IF NOT EXISTS {catalog}.adp_meta.quarantine "  # noqa: F821
          "(saved_ts TIMESTAMP, run_id STRING, dataset_id STRING, raw STRING, problems STRING)")

latest = spark.sql(  # noqa: F821
    f"SELECT state FROM {catalog}.adp_meta.engine_state ORDER BY saved_ts DESC LIMIT 1").collect()
store = ingest.MetadataStore.from_json(latest[0]["state"], specs) if latest else ingest.MetadataStore()
runs_before = len(store.runs)

records = pipeline.run_day(scenario, specs, store, day)
print(json.dumps([{k: r[k] for k in ("run_id", "status", "failure_code", "rows_new",
                                      "inserted", "updated", "quarantined")} for r in records], indent=1))

# COMMAND ----------

new_runs = store.runs[runs_before:]
spark.createDataFrame(  # noqa: F821
    [(r["run_id"], r["dataset_id"], r["status"], json.dumps(r, default=str)) for r in new_runs],
    "run_id STRING, dataset_id STRING, status STRING, record STRING",
).selectExpr("current_timestamp() AS saved_ts", "*").write.mode("append").saveAsTable(
    f"{catalog}.adp_meta.ingest_runs")

new_ids = {r["run_id"] for r in new_runs}
q_rows = [(q["run_id"], ds, json.dumps(q["raw"]), json.dumps(q["problems"]))
          for ds, qs in store.quarantine.items() for q in qs if q["run_id"] in new_ids]
if q_rows:
    spark.createDataFrame(q_rows, "run_id STRING, dataset_id STRING, raw STRING, problems STRING")\
        .selectExpr("current_timestamp() AS saved_ts", "*").write.mode("append")\
        .saveAsTable(f"{catalog}.adp_meta.quarantine")  # noqa: F821

SPARK_TYPES = {"int": "BIGINT", "decimal": "DECIMAL(18,2)", "date": "DATE", "timestamp": "TIMESTAMP",
               "bool": "BOOLEAN", "enum": "STRING", "string": "STRING"}
for ds, spec in specs.items():
    rows = list(store.tables.get(ds, {}).values())
    ddl = ", ".join(f"{c.name} {SPARK_TYPES[c.type]}" for c in spec.columns.values())
    df = spark.createDataFrame([tuple(r[c] for c in spec.columns) for r in rows], ddl)  # noqa: F821
    df.write.mode("overwrite").option("overwriteSchema", "true")\
        .saveAsTable(f"{catalog}.adp_bronze.{governance.ident(spec.bronze_name)}")

spark.sql(  # noqa: F821
    f"INSERT INTO {catalog}.adp_meta.engine_state SELECT current_timestamp(), :label, :state",
    args={"label": f"day{day}", "state": store.to_json()},
)

failed = [r["run_id"] for r in records if r["status"] == ingest.FAILED]
if failed:
    # The audit rows above are already written; the red run is the alert.
    raise RuntimeError(f"Ingestion failed for {failed}; watermarks were not advanced.")
