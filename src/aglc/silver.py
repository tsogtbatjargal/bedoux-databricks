import sys

import dlt
from pyspark.sql.functions import col, to_date, to_timestamp

# Track 3 Silver (docs/contracts-aglc.md): typed and validated. Expectations come
# from src/aglc/expectations.py, the same definitions the legacy report and unit
# tests use, so "valid" means one thing on both sides of the reconciliation.
# PII stays in gaming_players_clean, where Unity Catalog column masks apply
# (src/aglc/governance.py). No Gold table carries email or date_of_birth.

sys.path.append(spark.conf.get("bundle.sourcePath"))  # noqa: F821
from aglc import governance  # noqa: E402
from aglc.expectations import sql_rules  # noqa: E402

CATALOG = governance.ident(spark.conf.get("aglc.catalog"))  # noqa: F821
ENFORCE = governance.as_bool(spark.conf.get("aglc.enforce_governance", "true"))  # noqa: F821
BRONZE = f"{CATALOG}.aglc_bronze"


def _raw(name):
    return spark.read.table(f"{BRONZE}.{name}").drop("_row_id")  # noqa: F821


@dlt.table(
    name="gaming_players_clean",
    comment="Players. email and date_of_birth are masked by Unity Catalog unless you're in aglc_compliance.",
    schema=governance.players_schema(CATALOG, enforce=ENFORCE),
)
@dlt.expect_all_or_drop(sql_rules("players"))
def gaming_players_clean():
    return _raw("gaming_players_raw").withColumn("signup_date", to_date("signup_date"))


@dlt.table(name="gaming_sessions_clean", comment="Play sessions, validated")
@dlt.expect_all_or_drop(sql_rules("sessions"))
def gaming_sessions_clean():
    return _raw("gaming_sessions_raw").withColumn("start_ts", to_timestamp("start_ts"))


@dlt.table(name="gaming_wagers_clean", comment="Wagers, validated")
@dlt.expect_all_or_drop(sql_rules("wagers"))
def gaming_wagers_clean():
    return _raw("gaming_wagers_raw").withColumn("wager_ts", to_timestamp("wager_ts"))


@dlt.table(name="gaming_deposits_clean", comment="Deposits, validated")
@dlt.expect_all_or_drop(sql_rules("deposits"))
def gaming_deposits_clean():
    return _raw("gaming_deposits_raw").withColumn("deposit_ts", to_timestamp("deposit_ts"))


@dlt.table(name="retail_licensees_clean", comment="Licensees, validated")
@dlt.expect_all_or_drop(sql_rules("licensees"))
def retail_licensees_clean():
    return _raw("retail_licensees_raw")


@dlt.table(name="retail_orders_clean", comment="Wholesale order lines, validated")
@dlt.expect_all_or_drop(sql_rules("orders"))
def retail_orders_clean():
    return _raw("retail_orders_raw").withColumn("order_date", to_date(col("order_date")))
