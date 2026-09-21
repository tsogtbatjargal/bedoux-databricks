import dlt
from pyspark.sql.functions import (
    array,
    array_remove,
    col,
    count,
    current_timestamp,
    explode,
    lit,
    row_number,
    size,
    sum as _sum,
    trim,
    when,
)
from pyspark.sql.window import Window

# Silver Layer: clean, conformed copy of Bronze. Reads Bronze in batch (not
# streaming) because Bronze itself is a full, deterministic recompute each run,
# not a genuine incremental source -- see docs/contracts-bedoux.md.
#
# Chapter 02: leads/web_events/ops_events no longer just drop rows that fail a
# rule. Each has a "_flagged" view computing every row's reason codes (empty
# list = accepted) via native Spark expressions that mirror src/bedoux/quality.py's
# pure, unit-tested classify_* functions -- that module is the tested spec
# these expressions must match. It isn't imported here, same reason gold.py
# doesn't import transforms.py: this pipeline's DLT files run without
# `bundle.sourcePath` on sys.path (only bronze's pipeline configures that), and
# two literals don't justify wiring it up. Two tables read each "_flagged"
# view: "_clean" (accepted) and "_quarantine" (rejected, with reasons,
# persistent -- nothing vanishes silently). quality_metrics and gate_status
# turn quarantine counts into the publication-gate decision gold.py reads.

# Mirrors quality.QUARANTINE_RATE_THRESHOLD / quality.VALID_STAGES.
QUARANTINE_RATE_THRESHOLD = 0.10
VALID_STAGES = {"new", "qualified", "won", "lost"}

# =============================================================================
# clients_clean / campaigns_clean: small deterministic dimensions.
# Deliberately plain materialized tables, not Auto CDC -- see contracts doc for
# why CDC isn't the right tool here. Unchanged in chapter 02: dedup ties on
# clients_raw/campaigns_raw are a known, separately-tracked issue (see
# docs/sentinel/chapters/02-quality-gate.md), not part of this chapter's scope.
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
# leads: dedup by _row_id (Bronze's deterministic batch-order identity, not
# the tied _ingest_ts) then classify. Reasons mirror quality.classify_lead.
# =============================================================================


@dlt.view(name="leads_flagged")
def leads_flagged():
    leads = spark.read.table("workspace.bedoux_bronze.leads_raw")
    known_campaigns = (
        spark.read.table("workspace.bedoux_bronze.campaigns_raw")
        .select(col("campaign_id").alias("_known_campaign_id"))
        .distinct()
    )
    dedup_window = Window.partitionBy("lead_id").orderBy(col("_row_id").asc())

    return (
        leads.withColumn("stage", trim(col("stage")))
        .withColumn("email_domain", trim(col("email_domain")))
        .join(known_campaigns, leads.campaign_id == known_campaigns._known_campaign_id, "left")
        .withColumn("_dup_rank", row_number().over(dedup_window))
        .withColumn(
            "_reasons",
            array_remove(
                array(
                    when(col("campaign_id").isNull(), lit("null_campaign_id")),
                    when(
                        col("campaign_id").isNotNull() & col("_known_campaign_id").isNull(),
                        lit("unknown_campaign_id"),
                    ),
                    when(~col("stage").isin(*VALID_STAGES), lit("invalid_stage")),
                    when(col("_dup_rank") > 1, lit("duplicate_lead_id")),
                ),
                None,
            ),
        )
    )


@dlt.table(
    name="leads_clean",
    comment="Accepted leads: no dedup/classification rule failed",
)
def leads_clean():
    return (
        dlt.read("leads_flagged")
        .filter(size(col("_reasons")) == 0)
        .select("lead_id", "campaign_id", "stage", "created_ts", "email_domain", "_ingest_ts")
    )


@dlt.table(
    name="leads_quarantine",
    comment="Leads rejected by a quality rule, with reason codes. Persistent -- nothing is silently dropped.",
)
def leads_quarantine():
    return (
        dlt.read("leads_flagged")
        .filter(size(col("_reasons")) > 0)
        .select(
            "lead_id", "campaign_id", "stage", "created_ts", "email_domain",
            "_ingest_ts", col("_reasons").alias("reasons"),
        )
        .withColumn("_quarantined_ts", current_timestamp())
    )


# =============================================================================
# web_events: same shape as leads (campaign_id existence + a validity rule +
# dedup on event_id), reasons mirror quality.classify_web_event.
# =============================================================================


@dlt.view(name="web_events_flagged")
def web_events_flagged():
    events = spark.read.table("workspace.bedoux_bronze.web_events_raw")
    known_campaigns = (
        spark.read.table("workspace.bedoux_bronze.campaigns_raw")
        .select(col("campaign_id").alias("_known_campaign_id"))
        .distinct()
    )
    dedup_window = Window.partitionBy("event_id").orderBy(col("_row_id").asc())

    return (
        events.join(known_campaigns, events.campaign_id == known_campaigns._known_campaign_id, "left")
        .withColumn("_dup_rank", row_number().over(dedup_window))
        .withColumn(
            "_reasons",
            array_remove(
                array(
                    when(col("campaign_id").isNull(), lit("null_campaign_id")),
                    when(
                        col("campaign_id").isNotNull() & col("_known_campaign_id").isNull(),
                        lit("unknown_campaign_id"),
                    ),
                    when(col("session_duration_seconds") < 0, lit("invalid_duration")),
                    when(col("_dup_rank") > 1, lit("duplicate_event_id")),
                ),
                None,
            ),
        )
    )


@dlt.table(
    name="web_events_clean",
    comment="Accepted website events: no dedup/classification rule failed",
)
def web_events_clean():
    return (
        dlt.read("web_events_flagged")
        .filter(size(col("_reasons")) == 0)
        .select("event_id", "campaign_id", "session_duration_seconds", "page_views", "event_ts", "_ingest_ts")
    )


@dlt.table(
    name="web_events_quarantine",
    comment="Website events rejected by a quality rule, with reason codes. Persistent -- nothing is silently dropped.",
)
def web_events_quarantine():
    return (
        dlt.read("web_events_flagged")
        .filter(size(col("_reasons")) > 0)
        .select(
            "event_id", "campaign_id", "session_duration_seconds", "page_views",
            "event_ts", "_ingest_ts", col("_reasons").alias("reasons"),
        )
        .withColumn("_quarantined_ts", current_timestamp())
    )


# =============================================================================
# ops_events: no campaign FK. Latency validity + dedup on ops_event_id,
# reasons mirror quality.classify_ops_event.
# =============================================================================


@dlt.view(name="ops_events_flagged")
def ops_events_flagged():
    events = spark.read.table("workspace.bedoux_bronze.ops_events_raw")
    dedup_window = Window.partitionBy("ops_event_id").orderBy(col("_row_id").asc())

    return events.withColumn("_dup_rank", row_number().over(dedup_window)).withColumn(
        "_reasons",
        array_remove(
            array(
                when(col("latency_seconds").isNull() | (col("latency_seconds") < 0), lit("invalid_latency")),
                when(col("_dup_rank") > 1, lit("duplicate_ops_event_id")),
            ),
            None,
        ),
    )


@dlt.table(
    name="ops_events_clean",
    comment="Accepted ogi ops events: no dedup/classification rule failed",
)
def ops_events_clean():
    return (
        dlt.read("ops_events_flagged")
        .filter(size(col("_reasons")) == 0)
        .select("ops_event_id", "event_type", "success", "latency_seconds", "event_ts", "_ingest_ts")
    )


@dlt.table(
    name="ops_events_quarantine",
    comment="ogi ops events rejected by a quality rule, with reason codes. Persistent -- nothing is silently dropped.",
)
def ops_events_quarantine():
    return (
        dlt.read("ops_events_flagged")
        .filter(size(col("_reasons")) > 0)
        .select(
            "ops_event_id", "event_type", "success", "latency_seconds",
            "event_ts", "_ingest_ts", col("_reasons").alias("reasons"),
        )
        .withColumn("_quarantined_ts", current_timestamp())
    )


# =============================================================================
# quality_metrics / gate_status: turn the three "_flagged" views into the
# publication-gate decision gold.py reads. Pure DataFrame aggregation -- no
# driver-side counting -- so it stays a normal declarative DLT flow.
# =============================================================================


def _outcome_rows(source_name, view_name):
    df = dlt.read(view_name)
    accepted = df.withColumn("source", lit(source_name)).withColumn(
        "reason", explode(when(size(col("_reasons")) == 0, array(lit("accepted"))).otherwise(col("_reasons")))
    )
    return accepted.select("source", "reason")


@dlt.table(
    name="quality_metrics",
    comment="Per-run row counts by source and outcome (accepted, or a specific quarantine reason). Backs the publication gate.",
)
def quality_metrics():
    rows = (
        _outcome_rows("leads", "leads_flagged")
        .unionByName(_outcome_rows("web_events", "web_events_flagged"))
        .unionByName(_outcome_rows("ops_events", "ops_events_flagged"))
    )
    return (
        rows.groupBy("source", "reason")
        .agg(count("*").alias("row_count"))
        .withColumn("_computed_ts", current_timestamp())
    )


@dlt.table(
    name="gate_status",
    comment=(
        "Publication gate decision per source: whether this run's quarantine "
        f"rate is at or below the {QUARANTINE_RATE_THRESHOLD:.0%} threshold. "
        "gold.py withholds a table's refresh (keeping previously published "
        "content) for any source whose gate_passed is false."
    ),
)
def gate_status():
    metrics = dlt.read("quality_metrics")
    totals = metrics.groupBy("source").agg(_sum("row_count").alias("total"))
    quarantined = (
        metrics.filter(col("reason") != "accepted")
        .groupBy("source")
        .agg(_sum("row_count").alias("quarantined"))
    )
    return (
        totals.join(quarantined, "source", "left")
        .fillna({"quarantined": 0})
        .withColumn(
            "quarantine_rate",
            when(col("total") > 0, col("quarantined") / col("total")).otherwise(lit(0.0)),
        )
        .withColumn("gate_passed", col("quarantine_rate") <= lit(QUARANTINE_RATE_THRESHOLD))
    )
