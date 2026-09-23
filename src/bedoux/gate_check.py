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
from datetime import datetime, timezone

dbutils.widgets.text("source_path", "")  # noqa: F821
dbutils.widgets.text("run_start_ms", "")  # noqa: F821

source_path = dbutils.widgets.get("source_path")  # noqa: F821
run_start_ms = dbutils.widgets.get("run_start_ms")  # noqa: F821

if not source_path:
    raise ValueError(
        "source_path widget is empty; bedoux_gate_task must pass "
        "${workspace.file_path}/src so this task can import bedoux.quality"
    )

sys.path.append(source_path)
from bedoux import evidence_log, quality  # noqa: E402

# COMMAND ----------

GATE_TABLE = "workspace.bedoux_silver.gate_status"

# Missing, malformed, or unresolved parameters must stop before reading evidence.
min_computed_ts = quality.utc_from_epoch_ms(run_start_ms)

# Convert timestamps to epoch milliseconds IN Spark, before Python collection.
# Collecting TimestampType directly can yield naive driver-local datetimes.
# This is a freshness check, not a batch ID or protection against other writers.
evidence = spark.read.table(GATE_TABLE).selectExpr(  # noqa: F821
    "source", "gate_passed", "quarantine_rate", "total", "quarantined",
    "accepted_rows", "quarantined_rows", "conserved",
    "unix_millis(_computed_ts) AS _computed_ms",
)
rows = []
for record in evidence.collect():
    row = record.asDict()
    computed_ms = row.pop("_computed_ms")
    row["_computed_ts"] = (
        None if computed_ms is None else quality.utc_from_epoch_ms(computed_ms)
    )
    rows.append(row)

print(f"Read {len(rows)} row(s) from {GATE_TABLE}")
for row in sorted(rows, key=lambda r: str(r.get("source"))):
    print(
        f"  source={row.get('source')!r} "
        f"gate_passed={row.get('gate_passed')!r} "
        f"quarantine_rate={row.get('quarantine_rate')!r} "
        f"total={row.get('total')!r} quarantined={row.get('quarantined')!r} "
        f"accepted_rows={row.get('accepted_rows')!r} "
        f"quarantined_rows={row.get('quarantined_rows')!r} "
        f"conserved={row.get('conserved')!r} "
        f"_computed_ts={row.get('_computed_ts')!r}"
    )
print(f"Required sources: {list(quality.REQUIRED_SOURCES)}")
print(f"Run boundary (min _computed_ts): {min_computed_ts!r}")

# COMMAND ----------

passed, problems = quality.evaluate_gate(rows, min_computed_ts=min_computed_ts)

# COMMAND ----------

# Append-only evidence log (chapter 03 design; see
# docs/sentinel/chapters/03-protect-evidence.md's "Append-only evidence log"
# sections). Writes one row each time this notebook runs, pass or fail -- so
# at least one row per job run, and a task retry writes a duplicate sharing
# the same run_start_ms (see docs/contracts-bedoux.md, gate_evidence_log). A
# log that only records failures can't show the healthy case was healthy.
#
# The whole block is wrapped in one try/except: verdict propagation is
# prioritized over the write, on purpose. If appending this row throws, the
# gate's own passed/raise logic below must still run unchanged -- a logging
# bug must never withhold a healthy Gold refresh, and must never swallow a
# genuine gate failure either. The cost of that choice is that a broken
# writer can run silently beyond the printed warning below; that tradeoff is
# accepted, not unnoticed (see the chapter doc).
try:
    from pyspark.sql.types import (
        ArrayType, BooleanType, DoubleType, LongType, StringType,
        StructField, StructType, TimestampType,
    )

    _source_entry_schema = StructType([
        StructField("source", StringType()),
        StructField("gate_passed", BooleanType()),
        StructField("conserved", BooleanType()),
        StructField("total", LongType()),
        StructField("quarantined", LongType()),
        StructField("accepted_rows", LongType()),
        StructField("quarantined_rows", LongType()),
        StructField("quarantine_rate", DoubleType()),
        StructField("computed_ts", TimestampType()),
    ])
    _evidence_log_schema = StructType([
        StructField("run_start_ms", LongType(), nullable=False),
        StructField("run_start_ts", TimestampType(), nullable=False),
        StructField("written_ts", TimestampType(), nullable=False),
        StructField("passed", BooleanType(), nullable=False),
        StructField("problems", ArrayType(StringType())),
        StructField("sources", ArrayType(_source_entry_schema)),
    ])

    _written_ts = datetime.now(timezone.utc)
    _record = evidence_log.build_evidence_record(
        rows, passed, problems, int(run_start_ms), _written_ts
    )
    _packet = evidence_log.gate_and_redact(_record)

    spark.sql(  # noqa: F821
        f"CREATE TABLE IF NOT EXISTS {evidence_log.EVIDENCE_LOG_TABLE} ("
        "run_start_ms BIGINT, run_start_ts TIMESTAMP, written_ts TIMESTAMP, "
        "passed BOOLEAN, problems ARRAY<STRING>, sources ARRAY<STRUCT<"
        "source: STRING, gate_passed: BOOLEAN, conserved: BOOLEAN, "
        "total: BIGINT, quarantined: BIGINT, accepted_rows: BIGINT, "
        "quarantined_rows: BIGINT, quarantine_rate: DOUBLE, "
        "computed_ts: TIMESTAMP>>) USING DELTA "
        "TBLPROPERTIES ('delta.appendOnly' = 'true')"
    )
    spark.createDataFrame(  # noqa: F821
        [_packet], schema=_evidence_log_schema
    ).write.mode("append").saveAsTable(evidence_log.EVIDENCE_LOG_TABLE)
    print(
        f"Evidence log: appended 1 row to {evidence_log.EVIDENCE_LOG_TABLE} "
        f"(passed={_packet['passed']!r})"
    )
except Exception as exc:  # noqa: BLE001 -- must never block the gate verdict below
    print(f"Evidence log: FAILED to append a row to {evidence_log.EVIDENCE_LOG_TABLE}: {exc!r}")
    print("Continuing -- the evidence log must never withhold the gate's own verdict.")

# COMMAND ----------

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
