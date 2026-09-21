# Databricks notebook source
# Publication gate for bedoux_analytics_job (chapter 02).
#
# Runs as bedoux_gate_task, between bedoux_silver_task and bedoux_gold_task.
# Reads the gate_status table the Silver pipeline just wrote, applies
# quality.evaluate_gate, and raises on failure so the Gold task never starts.
#
# Why here and not inside a Gold dataset function: a DLT dataset function is
# declarative. Driver-side actions (.count(), .collect()) and reading the table
# currently being defined are not supported there. This task is ordinary job
# code, so the imperative check is legal -- and failing it stops the refresh
# outright, which is what "withhold publication" has to mean on a first-ever
# run where there is no previous version to fall back to.
#
# Failure here is intentional and expected during an incident: the job run goes
# red, Gold keeps its last published content, and the reason is in this task's
# log and in the quarantine tables.

# COMMAND ----------

import sys

dbutils.widgets.text("source_path", "")  # noqa: F821
dbutils.widgets.text("run_start_iso", "")  # noqa: F821

source_path = dbutils.widgets.get("source_path")  # noqa: F821
run_start_iso = dbutils.widgets.get("run_start_iso")  # noqa: F821

if not source_path:
    raise ValueError(
        "source_path widget is empty; bedoux_gate_task must pass "
        "${workspace.file_path}/src so this task can import bedoux.quality"
    )

sys.path.append(source_path)
from bedoux import quality  # noqa: E402

# COMMAND ----------

GATE_TABLE = "workspace.bedoux_silver.gate_status"

# Any gate_status row computed before this run started describes an earlier
# batch and cannot authorize publishing this one. Empty means no run binding
# is enforced, which should only happen outside the job.
min_computed_ts = None
if run_start_iso:
    from datetime import datetime

    min_computed_ts = datetime.fromisoformat(run_start_iso)

rows = [row.asDict() for row in spark.read.table(GATE_TABLE).collect()]  # noqa: F821

print(f"Read {len(rows)} row(s) from {GATE_TABLE}")
for row in sorted(rows, key=lambda r: str(r.get("source"))):
    print(
        f"  source={row.get('source')!r} "
        f"gate_passed={row.get('gate_passed')!r} "
        f"quarantine_rate={row.get('quarantine_rate')!r} "
        f"total={row.get('total')!r} quarantined={row.get('quarantined')!r} "
        f"_computed_ts={row.get('_computed_ts')!r}"
    )
print(f"Required sources: {list(quality.REQUIRED_SOURCES)}")
print(f"Run boundary (min _computed_ts): {min_computed_ts!r}")

# COMMAND ----------

passed, problems = quality.evaluate_gate(rows, min_computed_ts=min_computed_ts)

if passed:
    print("PUBLICATION GATE PASSED - every required source reported a fresh, explicit pass.")
    print("bedoux_gold_task may refresh Gold.")
else:
    detail = "\n".join(f"  - {p}" for p in problems)
    print("PUBLICATION GATE FAILED:")
    print(detail)
    print(
        "Withholding the Gold refresh. Previously published Gold tables keep "
        "their last trustworthy content; if this is a first-ever run, no Gold "
        "table is created, so rejected data is not published. Inspect "
        "workspace.bedoux_silver.<source>_quarantine for the rejected rows."
    )
    raise RuntimeError(
        "Publication gate failed; withholding Gold refresh:\n" + detail
    )
