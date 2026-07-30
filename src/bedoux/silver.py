import dlt
from pyspark.sql.functions import col, trim, row_number
from pyspark.sql.window import Window

# Silver Layer: clean, conformed copy of Bronze. Reads Bronze in batch (not
# streaming) because Bronze itself is a full, deterministic recompute each run,
# not a genuine incremental source -- see docs/contracts-bedoux.md.

# =============================================================================
# clients_clean / campaigns_clean: small deterministic dimensions.
# Deliberately plain materialized tables, not Auto CDC -- see contracts doc for
# why CDC isn't the right tool here.
# =============================================================================


@dlt.table(
    name="clients_clean",
    comment="Clean client accounts, deduplicated on client_id",
)
def clients_clean():
    df = spark.read.table("workspace.bedoux_bronze.clients_raw")
    window = Window.partitionBy("client_id").orderBy(col("_ingest_ts").desc())
    return (
        df.withColumn("client_name", trim(col("client_name")))
        .withColumn("_rn", row_number().over(window))
        .filter(col("_rn") == 1)
        .drop("_rn")
        .select("client_id", "client_name", "tier", "signup_date", "_ingest_ts")
    )


@dlt.table(
    name="campaigns_clean",
    comment="Clean marketing campaigns, deduplicated on campaign_id",
)
@dlt.expect_or_drop("valid_client_id", "client_id IS NOT NULL")
@dlt.expect_or_drop("valid_budget", "budget >= 0")
def campaigns_clean():
    df = spark.read.table("workspace.bedoux_bronze.campaigns_raw")
    window = Window.partitionBy("campaign_id").orderBy(col("_ingest_ts").desc())
    return (
        df.withColumn("_rn", row_number().over(window))
        .filter(col("_rn") == 1)
        .drop("_rn")
        .select(
            "campaign_id", "client_id", "channel", "budget", "status",
            "start_date", "end_date", "_ingest_ts",
        )
    )


# =============================================================================
# leads_clean / web_events_clean / ops_events_clean: detail-grain facts with
# data quality expectations. This is where the deliberately-invalid ~2% of rows
# from the generator actually get dropped.
# =============================================================================


@dlt.table(
    name="leads_clean",
    comment="Clean leads with data quality expectations",
)
@dlt.expect_or_drop("valid_campaign_id", "campaign_id IS NOT NULL")
@dlt.expect_or_drop("valid_stage", "stage IN ('new', 'qualified', 'won', 'lost')")
def leads_clean():
    return (
        spark.read.table("workspace.bedoux_bronze.leads_raw")
        .select(
            col("lead_id"),
            col("campaign_id"),
            trim(col("stage")).alias("stage"),
            col("created_ts"),
            trim(col("email_domain")).alias("email_domain"),
        )
    )


@dlt.table(
    name="web_events_clean",
    comment="Clean website events with data quality expectations",
)
@dlt.expect_or_drop("valid_campaign_id", "campaign_id IS NOT NULL")
@dlt.expect_or_drop("valid_duration", "session_duration_seconds >= 0")
def web_events_clean():
    return (
        spark.read.table("workspace.bedoux_bronze.web_events_raw")
        .select("event_id", "campaign_id", "session_duration_seconds", "page_views", "event_ts")
    )


@dlt.table(
    name="ops_events_clean",
    comment="Clean ogi ops events with data quality expectations",
)
@dlt.expect_or_drop("valid_latency", "latency_seconds IS NOT NULL AND latency_seconds >= 0")
def ops_events_clean():
    return (
        spark.read.table("workspace.bedoux_bronze.ops_events_raw")
        .select("ops_event_id", "event_type", "success", "latency_seconds", "event_ts")
    )
