# Databricks notebook source
# Track 3: Unity Catalog governance, in two steps (src/aglc/governance.py).
#
#   step=functions  before the pipelines: mask and filter functions. Silver and
#                   Gold declare the masks and row filter in their own table
#                   definitions, so the functions must exist first.
#   step=grants     after the pipelines: schema and table grants to the groups.
#
# Re-running is safe: functions are CREATE OR REPLACE; grants are idempotent.
# Free Edition support for account groups is unverified, so grants are skipped
# unless apply_grants=true.

# COMMAND ----------

import sys

dbutils.widgets.text("source_path", "")  # noqa: F821
dbutils.widgets.text("catalog", "workspace")  # noqa: F821
dbutils.widgets.text("step", "")  # noqa: F821
dbutils.widgets.text("apply_grants", "false")  # noqa: F821

source_path = dbutils.widgets.get("source_path")  # noqa: F821
if not source_path:
    raise ValueError("source_path widget is empty; pass ${workspace.file_path}/src")
sys.path.append(source_path)
from aglc import governance  # noqa: E402

catalog = dbutils.widgets.get("catalog")  # noqa: F821
step = dbutils.widgets.get("step")  # noqa: F821

# COMMAND ----------

if step == "functions":
    stmts = governance.function_statements(catalog)
elif step == "grants":
    if not governance.as_bool(dbutils.widgets.get("apply_grants")):  # noqa: F821
        print("apply_grants=false: grants skipped (groups unverified on this workspace)")
        stmts = []
    else:
        stmts = governance.grant_statements(catalog)
else:
    raise ValueError(f"step must be 'functions' or 'grants', got {step!r}")

for stmt in stmts:
    print(f"applying: {stmt.splitlines()[0]}")
    spark.sql(stmt)  # noqa: F821
