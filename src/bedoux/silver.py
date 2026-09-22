import dlt
from pyspark.sql.functions import (
    array,
    array_compact,
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

# Reason codes, extracted as constants rather than inline string literals at
# each lit(...) call site, mirroring quality.py's classify_lead/
# classify_web_event/classify_ops_event/reconcile literals exactly:
#   REASON_NULL_CAMPAIGN_ID     <-> quality.classify_lead/classify_web_event: "null_campaign_id"
#   REASON_UNKNOWN_CAMPAIGN_ID  <-> quality.classify_lead/classify_web_event: "unknown_campaign_id"
#   REASON_INVALID_STAGE        <-> quality.classify_lead:                    "invalid_stage"
#   REASON_INVALID_DURATION     <-> quality.classify_web_event:               "invalid_duration"
#   REASON_INVALID_LATENCY      <-> quality.classify_ops_event:               "invalid_latency"
#   REASON_ACCEPTED             <-> quality.py's reconcile: accepted rows carry no reason;
#                                    "accepted" only exists here, as quality_metrics' label
#                                    for the diagnostic per-reason breakdown.
#   _duplicate_reason(key)      <-> quality.reconcile: f"duplicate_{key}"
# A typo in one of these constants would silently diverge from the tested
# spec with no live-pipeline test to catch it -- tests/test_quality.py greps
# this file's source for these constants (silver.py can't be imported
# without a live `dlt` runtime) and checks them against quality.py's reason
# vocabulary, so a typo or a renamed/removed reason fails that test instead.
REASON_NULL_CAMPAIGN_ID = "null_campaign_id"
REASON_UNKNOWN_CAMPAIGN_ID = "unknown_campaign_id"
REASON_INVALID_STAGE = "invalid_stage"
REASON_INVALID_DURATION = "invalid_duration"
REASON_INVALID_LATENCY = "invalid_latency"
REASON_ACCEPTED = "accepted"


def _duplicate_reason(key_column_name):
    return f"duplicate_{key_column_name}"

# =============================================================================
# clients_clean / campaigns_clean: small deterministic dimensions.
# Deliberately plain materialized tables, not Auto CDC -- see contracts doc for
# why CDC isn't the right tool here. Unchanged in chapter 02: dedup ties on
# clients_raw/campaigns_raw are a known, separately-tracked issue (see
# docs/sentinel/known-gaps.md), not part of this chapter's scope.
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
@dlt.expect_or_fail("reasons_not_null", "_reasons IS NOT NULL")
def leads_flagged():
    leads = spark.read.table("workspace.bedoux_bronze.leads_raw")
    # Validated against campaigns_clean (the eligible, publishable Silver
    # dimension), not campaigns_raw. A campaign that campaigns_clean itself
    # rejects (its own expect_or_drop rules: client_id IS NOT NULL,
    # budget >= 0) must not count as "known" here -- Gold's gold_client_funnel
    # inner-joins leads to campaigns_clean, so a lead referencing a
    # Bronze-only campaign would otherwise pass Silver as accepted, conserve,
    # pass the gate, then silently vanish from Gold with no record. See the
    # chapter doc's review-findings section.
    known_campaigns = (
        dlt.read("campaigns_clean")
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
            # array_compact, not array_remove(..., None): array_remove is
            # null-intolerant -- a NULL *element* argument makes the whole
            # result NULL instead of stripping NULLs, so every when(...)
            # that evaluates False (NULL, no .otherwise()) poisoned the
            # entire array on every row. See the chapter's incident writeup.
            array_compact(
                array(
                    when(col("campaign_id").isNull(), lit(REASON_NULL_CAMPAIGN_ID)),
                    when(
                        col("campaign_id").isNotNull() & col("_known_campaign_id").isNull(),
                        lit(REASON_UNKNOWN_CAMPAIGN_ID),
                    ),
                    # NULL-safe: `~col("stage").isin(...)` is NULL (not True) for a NULL
                    # stage, so a null-stage row would otherwise pass through accepted --
                    # a regression from the pre-chapter-02 expect_or_drop, which did drop
                    # it. isNull() first forces the NULL case to quarantine explicitly.
                    when(col("stage").isNull() | (~col("stage").isin(*VALID_STAGES)), lit(REASON_INVALID_STAGE)),
                    when(col("_dup_rank") > 1, lit(_duplicate_reason("lead_id"))),
                ),
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
@dlt.expect_or_fail("reasons_not_null", "_reasons IS NOT NULL")
def web_events_flagged():
    events = spark.read.table("workspace.bedoux_bronze.web_events_raw")
    # Validated against campaigns_clean, not campaigns_raw -- see
    # leads_flagged above for why.
    known_campaigns = (
        dlt.read("campaigns_clean")
        .select(col("campaign_id").alias("_known_campaign_id"))
        .distinct()
    )
    dedup_window = Window.partitionBy("event_id").orderBy(col("_row_id").asc())

    return (
        events.join(known_campaigns, events.campaign_id == known_campaigns._known_campaign_id, "left")
        .withColumn("_dup_rank", row_number().over(dedup_window))
        .withColumn(
            "_reasons",
            # array_compact, not array_remove(..., None) -- see leads_flagged above.
            array_compact(
                array(
                    when(col("campaign_id").isNull(), lit(REASON_NULL_CAMPAIGN_ID)),
                    when(
                        col("campaign_id").isNotNull() & col("_known_campaign_id").isNull(),
                        lit(REASON_UNKNOWN_CAMPAIGN_ID),
                    ),
                    # NULL-safe: plain `< 0` is NULL (not True) for a NULL duration, so a
                    # null-duration row would otherwise pass through accepted. Matches the
                    # ops_events_flagged pattern below, which already gets this right.
                    when(
                        col("session_duration_seconds").isNull() | (col("session_duration_seconds") < 0),
                        lit(REASON_INVALID_DURATION),
                    ),
                    when(col("_dup_rank") > 1, lit(_duplicate_reason("event_id"))),
                ),
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
@dlt.expect_or_fail("reasons_not_null", "_reasons IS NOT NULL")
def ops_events_flagged():
    events = spark.read.table("workspace.bedoux_bronze.ops_events_raw")
    dedup_window = Window.partitionBy("ops_event_id").orderBy(col("_row_id").asc())

    # array_compact, not array_remove(..., None) -- see leads_flagged above.
    return events.withColumn("_dup_rank", row_number().over(dedup_window)).withColumn(
        "_reasons",
        array_compact(
            array(
                when(
                    col("latency_seconds").isNull() | (col("latency_seconds") < 0),
                    lit(REASON_INVALID_LATENCY),
                ),
                when(col("_dup_rank") > 1, lit(_duplicate_reason("ops_event_id"))),
            ),
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
#
# quality_metrics explodes _reasons for a per-reason breakdown, so a row with
# two reasons contributes two rows there -- useful for diagnosing *why* a run
# was quarantined, but not row-conserving. gate_status must NOT be derived
# from quality_metrics's exploded counts for exactly that reason (a
# multi-reason row would inflate both the numerator and the denominator of
# the rate). gate_status instead counts rows once each, straight from the
# "_flagged" views (quality.reconcile's conservation property, reapplied
# here): total = count(*), quarantined = count(size(_reasons) > 0).
#
# INCIDENT (see docs/sentinel/chapters/02-quality-gate.md): a live baseline
# run showed why counting "total"/"quarantined" from the _flagged views is
# not enough on its own. array_remove(..., None)'s null-intolerance made
# _reasons NULL on every row, so this same view-based counting path reported
# total=500, quarantined=0, gate_passed=true for leads -- a clean-looking
# pass -- while leads_clean and leads_quarantine, built from that identical
# NULL _reasons, were both actually empty. The view-based total agreed with
# itself and was still wrong, because nothing checked it against what the
# *_clean/*_quarantine tables (the tables Gold and the quarantine record
# actually depend on) really persisted. gate_status now also reads those
# persisted tables directly and adds a `conserved` boolean
# (accepted_rows + quarantined_rows == total) that catches exactly this: a
# split that doesn't add back up to the input, regardless of why.
# =============================================================================


def _outcome_rows(source_name, view_name):
    df = dlt.read(view_name)
    accepted = df.withColumn("source", lit(source_name)).withColumn(
        "reason", explode(when(size(col("_reasons")) == 0, array(lit(REASON_ACCEPTED))).otherwise(col("_reasons")))
    )
    return accepted.select("source", "reason")


def _row_counts(source_name, view_name):
    """One row per input row (not exploded): source + whether it was
    quarantined. The row-conserving basis for gate_status's rate."""
    df = dlt.read(view_name)
    return df.withColumn("source", lit(source_name)).withColumn(
        "_quarantined", (size(col("_reasons")) > 0).cast("int")
    ).select("source", "_quarantined")


def _persisted_counts(source_name, clean_table, quarantine_table):
    """Row counts read from the *persisted* clean/quarantine tables, not the
    _flagged view -- the ground truth gate_status's conservation check must
    agree with. Declarative DataFrame aggregation (like everywhere else in
    this pipeline), not a driver-side .count() action, so this stays legal
    inside a dataset function."""
    accepted = (
        dlt.read(clean_table)
        .agg(count("*").alias("accepted_rows"))
        .withColumn("source", lit(source_name))
    )
    quarantined = (
        dlt.read(quarantine_table)
        .agg(count("*").alias("quarantined_rows"))
        .withColumn("source", lit(source_name))
    )
    return accepted.join(quarantined, "source")


@dlt.table(
    name="quality_metrics",
    comment=(
        "Per-run row counts by source and outcome (accepted, or a specific "
        "quarantine reason), exploded so a multi-reason row appears once per "
        "reason. Diagnostic breakdown only -- gate_status does NOT read this "
        "table, since a multi-reason row would inflate its rate."
    ),
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
        f"rate is at or below the {QUARANTINE_RATE_THRESHOLD:.0%} threshold, "
        "AND whether accepted_rows + quarantined_rows (read from the "
        "persisted *_clean/*_quarantine tables) equals total (read from the "
        "_flagged view) -- `conserved`. quality.evaluate_gate withholds "
        "unless both gate_passed and conserved are true and total > 0. "
        "bedoux_gate_task withholds the entire Gold pipeline when any "
        "required source lacks fresh, passing, conserved evidence."
    ),
)
def gate_status():
    row_counts = (
        _row_counts("leads", "leads_flagged")
        .unionByName(_row_counts("web_events", "web_events_flagged"))
        .unionByName(_row_counts("ops_events", "ops_events_flagged"))
    )
    counts = row_counts.groupBy("source").agg(
        count("*").alias("total"),
        _sum("_quarantined").alias("quarantined"),
    )
    persisted = (
        _persisted_counts("leads", "leads_clean", "leads_quarantine")
        .unionByName(_persisted_counts("web_events", "web_events_clean", "web_events_quarantine"))
        .unionByName(_persisted_counts("ops_events", "ops_events_clean", "ops_events_quarantine"))
    )
    return (
        counts.join(persisted, "source", "left")
        .withColumn(
            "quarantine_rate",
            when(col("total") > 0, col("quarantined") / col("total")).otherwise(lit(0.0)),
        )
        .withColumn("gate_passed", col("quarantine_rate") <= lit(QUARANTINE_RATE_THRESHOLD))
        .withColumn(
            "conserved",
            (col("accepted_rows") + col("quarantined_rows")) == col("total"),
        )
        # Freshness only, not a run ID. The gate rejects evidence older than
        # the job start; this assumes a serialized job with no other writers.
        .withColumn("_computed_ts", current_timestamp())
    )
