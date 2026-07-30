import dlt
from pyspark.sql.functions import col, trim

# Silver Layer: Clean, conformed copy of Bronze
# Detail grain, no business logic or KPIs
# Data quality validated

# =============================================================================
# Auto CDC Tables (customer, orders)
# Tables that track state changes - use Auto CDC for incremental updates
# =============================================================================

# Source view for customer_clean with cleaned data
@dlt.view(
    name="customer_clean_source"
)
def customer_clean_source():
    return (
        spark.readStream.table("workspace.bronze.customer_raw")
        .select(
            col("c_custkey"),
            trim(col("c_name")).alias("c_name"),
            trim(col("c_address")).alias("c_address"),
            col("c_nationkey"),
            trim(col("c_phone")).alias("c_phone"),
            col("c_acctbal"),
            trim(col("c_mktsegment")).alias("c_mktsegment"),
            trim(col("c_comment")).alias("c_comment"),
            col("_ingest_ts")
        )
    )

# Apply CDC to customer_clean
dlt.create_streaming_table(
    name="customer_clean",
    comment="Clean customer data with Auto CDC (SCD Type 1)"
)

dlt.apply_changes(
    target="customer_clean",
    source="customer_clean_source",
    keys=["c_custkey"],
    sequence_by="_ingest_ts",
    stored_as_scd_type=1
)

# Source view for orders_clean with cleaned data
@dlt.view(
    name="orders_clean_source"
)
def orders_clean_source():
    return (
        spark.readStream.table("workspace.bronze.orders_raw")
        .select(
            col("o_orderkey"),
            col("o_custkey"),
            trim(col("o_orderstatus")).alias("o_orderstatus"),
            col("o_totalprice"),
            col("o_orderdate"),
            trim(col("o_orderpriority")).alias("o_orderpriority"),
            trim(col("o_clerk")).alias("o_clerk"),
            col("o_shippriority"),
            trim(col("o_comment")).alias("o_comment"),
            col("_ingest_ts")
        )
    )

# Apply CDC to orders_clean
dlt.create_streaming_table(
    name="orders_clean",
    comment="Clean orders data with Auto CDC (SCD Type 1)"
)

dlt.apply_changes(
    target="orders_clean",
    source="orders_clean_source",
    keys=["o_orderkey"],
    sequence_by="_ingest_ts",
    stored_as_scd_type=1
)

# =============================================================================
# Streaming Tables with Expectations (lineitem, part, supplier, partsupp, nation, region)
# Reference and detail tables - use data quality expectations
# =============================================================================

@dlt.table(
    name="lineitem_clean",
    comment="Clean lineitem data with data quality expectations"
)
@dlt.expect_or_drop("valid_orderkey", "l_orderkey IS NOT NULL")
@dlt.expect_or_drop("valid_linenumber", "l_linenumber IS NOT NULL")
@dlt.expect_or_drop("valid_quantity", "l_quantity > 0")
@dlt.expect_or_drop("valid_discount", "l_discount BETWEEN 0 AND 1")
@dlt.expect_or_drop("valid_extendedprice", "l_extendedprice >= 0")
@dlt.expect_or_drop("valid_tax", "l_tax >= 0")
def lineitem_clean():
    return (
        spark.readStream.table("workspace.bronze.lineitem_raw")
        .select(
            col("l_orderkey"),
            col("l_partkey"),
            col("l_suppkey"),
            col("l_linenumber"),
            col("l_quantity"),
            col("l_extendedprice"),
            col("l_discount"),
            col("l_tax"),
            trim(col("l_returnflag")).alias("l_returnflag"),
            trim(col("l_linestatus")).alias("l_linestatus"),
            col("l_shipdate"),
            col("l_commitdate"),
            col("l_receiptdate"),
            trim(col("l_shipinstruct")).alias("l_shipinstruct"),
            trim(col("l_shipmode")).alias("l_shipmode"),
            trim(col("l_comment")).alias("l_comment")
        )
    )

@dlt.table(
    name="part_clean",
    comment="Clean part data with data quality expectations"
)
@dlt.expect_or_drop("valid_partkey", "p_partkey IS NOT NULL")
@dlt.expect_or_drop("valid_retailprice", "p_retailprice >= 0")
def part_clean():
    return (
        spark.readStream.table("workspace.bronze.part_raw")
        .select(
            col("p_partkey"),
            trim(col("p_name")).alias("p_name"),
            trim(col("p_mfgr")).alias("p_mfgr"),
            trim(col("p_brand")).alias("p_brand"),
            trim(col("p_type")).alias("p_type"),
            col("p_size"),
            trim(col("p_container")).alias("p_container"),
            col("p_retailprice"),
            trim(col("p_comment")).alias("p_comment")
        )
    )

@dlt.table(
    name="supplier_clean",
    comment="Clean supplier data with data quality expectations"
)
@dlt.expect_or_drop("valid_suppkey", "s_suppkey IS NOT NULL")
def supplier_clean():
    return (
        spark.readStream.table("workspace.bronze.supplier_raw")
        .select(
            col("s_suppkey"),
            trim(col("s_name")).alias("s_name"),
            trim(col("s_address")).alias("s_address"),
            col("s_nationkey"),
            trim(col("s_phone")).alias("s_phone"),
            col("s_acctbal"),
            trim(col("s_comment")).alias("s_comment")
        )
    )

@dlt.table(
    name="partsupp_clean",
    comment="Clean partsupp data with data quality expectations"
)
@dlt.expect_or_drop("valid_partkey", "ps_partkey IS NOT NULL")
@dlt.expect_or_drop("valid_suppkey", "ps_suppkey IS NOT NULL")
@dlt.expect_or_drop("valid_availqty", "ps_availqty >= 0")
@dlt.expect_or_drop("valid_supplycost", "ps_supplycost >= 0")
def partsupp_clean():
    return (
        spark.readStream.table("workspace.bronze.partsupp_raw")
        .select(
            col("ps_partkey"),
            col("ps_suppkey"),
            col("ps_availqty"),
            col("ps_supplycost"),
            trim(col("ps_comment")).alias("ps_comment")
        )
    )

@dlt.table(
    name="nation_clean",
    comment="Clean nation data with data quality expectations"
)
@dlt.expect_or_drop("valid_nationkey", "n_nationkey IS NOT NULL")
def nation_clean():
    return (
        spark.readStream.table("workspace.bronze.nation_raw")
        .select(
            col("n_nationkey"),
            trim(col("n_name")).alias("n_name"),
            col("n_regionkey"),
            trim(col("n_comment")).alias("n_comment")
        )
    )

@dlt.table(
    name="region_clean",
    comment="Clean region data with data quality expectations"
)
@dlt.expect_or_drop("valid_regionkey", "r_regionkey IS NOT NULL")
def region_clean():
    return (
        spark.readStream.table("workspace.bronze.region_raw")
        .select(
            col("r_regionkey"),
            trim(col("r_name")).alias("r_name"),
            trim(col("r_comment")).alias("r_comment")
        )
    )