import sys

import dlt
from pyspark.sql import functions as F

# Track 3 Gold (docs/contracts-aglc.md). Reads aglc_silver only.
#
# The responsible-gaming logic is reimplemented here as Spark expressions.
# src/aglc/rules.py is the tested reference spec (tests/test_aglc.py); thresholds
# are imported from it so the numbers can't drift. Same reasoning as Track 2's
# transforms.py for not wrapping the Python functions in UDFs.
#
# gold_retail_sales_daily declares a Unity Catalog row filter by domain. The filter
# function is created by aglc_governance_functions_task before this pipeline runs;
# a pipeline-managed table can't be ALTERed to add it later (src/aglc/governance.py).

sys.path.append(spark.conf.get("bundle.sourcePath"))  # noqa: F821
from aglc import governance, rules  # noqa: E402

CATALOG = governance.ident(spark.conf.get("aglc.catalog"))  # noqa: F821
ENFORCE = governance.as_bool(spark.conf.get("aglc.enforce_governance", "true"))  # noqa: F821
SILVER = f"{CATALOG}.aglc_silver"


def _silver(name):
    return spark.read.table(f"{SILVER}.{name}")  # noqa: F821


def _player_daily():
    w = (_silver("gaming_wagers_clean")
         .groupBy("player_id", F.to_date("wager_ts").alias("activity_date"))
         .agg(F.sum("stake").alias("total_stake"), F.sum("payout").alias("total_payout")))
    d = (_silver("gaming_deposits_clean")
         .groupBy("player_id", F.to_date("deposit_ts").alias("activity_date"))
         .agg(F.sum("amount").alias("deposit_total"), F.count("*").alias("deposit_count")))
    s = (_silver("gaming_sessions_clean")
         .groupBy("player_id", F.to_date("start_ts").alias("activity_date"))
         .agg(F.sum("duration_minutes").alias("session_minutes")))
    return (
        w.join(d, ["player_id", "activity_date"], "full")
        .join(s, ["player_id", "activity_date"], "full")
        .fillna({"total_stake": 0.0, "total_payout": 0.0, "deposit_total": 0.0,
                 "deposit_count": 0, "session_minutes": 0})
        .withColumn("total_stake", F.round("total_stake", 2))
        .withColumn("total_payout", F.round("total_payout", 2))
        .withColumn("net_loss", F.round(F.col("total_stake") - F.col("total_payout"), 2))
        .withColumn("deposit_total", F.round("deposit_total", 2))
    )


@dlt.table(name="gold_gaming_player_daily",
           comment="Player activity. Grain: player x day. No PII.")
def gold_gaming_player_daily():
    return _player_daily()


@dlt.table(name="gold_rg_player_flags",
           comment="Responsible-gaming flags. Grain: one row per player. Rules: src/aglc/rules.py.")
def gold_rg_player_flags():
    daily = _player_daily()
    per_player = daily.groupBy("player_id").agg(
        F.sum(F.when((F.col("net_loss") > 0) & (F.col("deposit_count") >= rules.CHASING_MIN_DEPOSITS), 1)
              .otherwise(0)).alias("chasing_days"),
        F.sum(F.when(F.col("deposit_count") > 0, 1).otherwise(0)).alias("deposit_days"),
        F.max(F.when(F.col("deposit_count") > 0, F.col("deposit_total"))).alias("max_deposit"),
        # Exact median (percentile_cont semantics), matching statistics.median in rules.py.
        F.expr("percentile(CASE WHEN deposit_count > 0 THEN deposit_total END, 0.5)").alias("median_deposit"),
    )
    longest = _silver("gaming_sessions_clean").groupBy("player_id").agg(
        F.max("duration_minutes").alias("longest_session"))
    wagered = _silver("gaming_wagers_clean").select("player_id").distinct().withColumn("has_wager", F.lit(True))

    flags = (
        _silver("gaming_players_clean").select("player_id", "self_excluded")
        .join(per_player, "player_id", "left")
        .join(longest, "player_id", "left")
        .join(wagered, "player_id", "left")
        .select(
            "player_id",
            (F.coalesce(F.col("chasing_days"), F.lit(0)) >= rules.CHASING_MIN_DAYS).alias("flag_chasing_losses"),
            ((F.coalesce(F.col("deposit_days"), F.lit(0)) >= rules.SPIKE_MIN_DAYS)
             & (F.col("max_deposit") > rules.SPIKE_FACTOR * F.col("median_deposit"))).alias("flag_deposit_spike"),
            (F.coalesce(F.col("longest_session"), F.lit(0)) >= rules.LONG_SESSION_MINUTES).alias("flag_long_session"),
            (F.col("self_excluded") & F.coalesce(F.col("has_wager"), F.lit(False))).alias("flag_self_exclusion_breach"),
        )
        .fillna(False, subset=["flag_deposit_spike"])
    )
    other = sum(F.col(c).cast("int") for c in ("flag_chasing_losses", "flag_deposit_spike", "flag_long_session"))
    explanation = F.concat_ws("; ", *[
        F.when(F.col(k), F.lit(v)) for k, v in rules.EXPLANATIONS.items()
    ])
    return (
        flags
        .withColumn("risk_level",
                    F.when(F.col("flag_self_exclusion_breach") | (other >= 2), "high")
                     .when(other == 1, "medium").otherwise("low"))
        .withColumn("explanation",
                    F.when(explanation == "", F.lit("no rule triggered")).otherwise(explanation))
    )


@dlt.table(name="gold_retail_sales_daily",
           comment="Liquor and cannabis wholesale. Grain: domain x region x category x day. Row-filtered by domain.",
           row_filter=governance.retail_row_filter(CATALOG, enforce=ENFORCE))
def gold_retail_sales_daily():
    lic = _silver("retail_licensees_clean").select("licensee_id", "region")
    return (
        _silver("retail_orders_clean").join(lic, "licensee_id")
        .groupBy("domain", "region", "product_category", "order_date")
        .agg(F.count("*").alias("order_count"),
             F.sum("quantity").alias("units"),
             F.round(F.sum("amount"), 2).alias("revenue"))
    )
