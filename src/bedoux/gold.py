import dlt
from pyspark.sql.functions import col, sum as _sum, count, when, date_trunc, to_date, avg, lit

# Gold Layer: business-ready tables, one per business question.
# Reads workspace.bedoux_silver ONLY.
#
# The three metrics below (conversion_rate, cost_per_lead, ops_success_rate)
# are native Spark column expressions, not UDFs wrapping transforms.py.
# transforms.py's pure functions are the tested reference spec for these
# formulas (see tests/test_transforms.py) -- they aren't imported here because
# a UDF's closure gets shipped to executors via cloudpickle, which requires
# the `bedoux` package to be distributed to every executor (a wheel/addPyFile
# build step disproportionate to three one-line formulas). Native column
# expressions are also the idiomatic, faster choice over Python UDFs for
# arithmetic this simple.
#
# Chapter 02 publication gate: each table below computes its normal result,
# then checks workspace.bedoux_silver.gate_status for the source(s) it
# depends on. If any of those sources failed the quarantine-rate threshold
# this run, the table returns its own previously published content unchanged
# instead of the freshly computed one -- Genie/BI keeps serving the last
# trustworthy refresh rather than a materially degraded one. On a table's
# first-ever run there is nothing previous to fall back to, so a failing gate
# publishes the fresh result anyway (there is nothing to withhold yet). This
# design is implemented and unit-verified at the decision-logic level
# (test_quality.py); it has not been exercised against a live DLT pipeline --
# no workspace credentials are available in this environment (see
# docs/sentinel/chapters/02-quality-gate.md).


def _gate_passed(sources):
    """True if every listed source's quarantine rate is within threshold."""
    gate = spark.read.table("workspace.bedoux_silver.gate_status").filter(
        col("source").isin(*sources)
    )
    return gate.filter(~col("gate_passed")).limit(1).count() == 0


def _publish_or_withhold(full_table_name, sources, fresh):
    if _gate_passed(sources):
        return fresh
    if spark.catalog.tableExists(full_table_name):
        return spark.read.table(full_table_name)
    return fresh  # first run: nothing previously published to withhold


@dlt.table(
    name="gold_campaign_performance",
    comment="Campaign performance. Grain: one row per campaign. Budget, leads, conversion rate, cost-per-lead.",
)
def gold_campaign_performance():
    campaigns = spark.read.table("workspace.bedoux_silver.campaigns_clean")
    leads = spark.read.table("workspace.bedoux_silver.leads_clean")

    lead_agg = leads.groupBy("campaign_id").agg(
        count("*").alias("lead_count"),
        _sum(when(col("stage") == "won", 1).otherwise(0)).alias("won_count"),
    )

    fresh = (
        campaigns.join(lead_agg, "campaign_id", "left")
        .fillna({"lead_count": 0, "won_count": 0})
        .withColumn(
            "conversion_rate",
            when(col("lead_count") > 0, col("won_count") / col("lead_count")).otherwise(lit(0.0)),
        )
        .withColumn(
            "cost_per_lead",
            when(col("lead_count") > 0, col("budget") / col("lead_count")).otherwise(lit(None)),
        )
        .select(
            "campaign_id", "client_id", "channel", "budget", "status",
            "lead_count", "won_count", "conversion_rate", "cost_per_lead",
        )
        .orderBy("campaign_id")
    )
    return _publish_or_withhold("workspace.bedoux_gold.gold_campaign_performance", ["leads"], fresh)


@dlt.table(
    name="gold_client_funnel",
    comment="Funnel stage counts by client and month. Grain: one row per client per month.",
)
def gold_client_funnel():
    campaigns = spark.read.table("workspace.bedoux_silver.campaigns_clean").select(
        "campaign_id", "client_id"
    )
    leads = spark.read.table("workspace.bedoux_silver.leads_clean")

    joined = leads.join(campaigns, "campaign_id", "inner").withColumn(
        "month_date", date_trunc("month", col("created_ts"))
    )

    fresh = (
        joined.groupBy("client_id", "month_date")
        .agg(
            _sum(when(col("stage") == "new", 1).otherwise(0)).alias("new_count"),
            _sum(when(col("stage") == "qualified", 1).otherwise(0)).alias("qualified_count"),
            _sum(when(col("stage") == "won", 1).otherwise(0)).alias("won_count"),
            _sum(when(col("stage") == "lost", 1).otherwise(0)).alias("lost_count"),
            count("*").alias("total_leads"),
        )
        .orderBy("client_id", "month_date")
    )
    return _publish_or_withhold("workspace.bedoux_gold.gold_client_funnel", ["leads"], fresh)


@dlt.table(
    name="gold_ogi_ops_health",
    comment="ogi operational health. Grain: one row per day. Success rate, message volume, avg latency.",
)
def gold_ogi_ops_health():
    ops = spark.read.table("workspace.bedoux_silver.ops_events_clean")

    daily = (
        ops.withColumn("event_date", to_date(col("event_ts")))
        .groupBy("event_date")
        .agg(
            count("*").alias("total_events"),
            _sum(when(col("success"), 1).otherwise(0)).alias("success_count"),
            avg("latency_seconds").alias("avg_latency_seconds"),
            _sum(when(col("event_type") == "telegram_message", 1).otherwise(0)).alias("telegram_messages"),
            _sum(when(col("event_type") == "daily_plan_run", 1).otherwise(0)).alias("daily_plan_runs"),
        )
    )

    fresh = (
        daily.withColumn(
            "success_rate",
            when(col("total_events") > 0, col("success_count") / col("total_events")).otherwise(lit(0.0)),
        )
        .select(
            "event_date", "total_events", "success_count", "success_rate",
            "avg_latency_seconds", "telegram_messages", "daily_plan_runs",
        )
        .orderBy("event_date")
    )
    return _publish_or_withhold("workspace.bedoux_gold.gold_ogi_ops_health", ["ops_events"], fresh)
