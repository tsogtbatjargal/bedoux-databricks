import dlt
from pyspark.sql.functions import current_timestamp, lit

# Bronze Layer: Raw, append-only landing zone
# Faithful copy of source data with audit columns

@dlt.table(
    name="customer_raw",
    comment="Raw customer data from samples.tpch.customer"
)
def customer_raw():
    return (
        spark.readStream.table("samples.tpch.customer")
        .select(
            "*",
            current_timestamp().alias("_ingest_ts"),
            lit("samples.tpch.customer").alias("_source_table")
        )
    )

@dlt.table(
    name="orders_raw",
    comment="Raw orders data from samples.tpch.orders"
)
def orders_raw():
    return (
        spark.readStream.table("samples.tpch.orders")
        .select(
            "*",
            current_timestamp().alias("_ingest_ts"),
            lit("samples.tpch.orders").alias("_source_table")
        )
    )

@dlt.table(
    name="lineitem_raw",
    comment="Raw lineitem data from samples.tpch.lineitem"
)
def lineitem_raw():
    return (
        spark.readStream.table("samples.tpch.lineitem")
        .select(
            "*",
            current_timestamp().alias("_ingest_ts"),
            lit("samples.tpch.lineitem").alias("_source_table")
        )
    )

@dlt.table(
    name="part_raw",
    comment="Raw part data from samples.tpch.part"
)
def part_raw():
    return (
        spark.readStream.table("samples.tpch.part")
        .select(
            "*",
            current_timestamp().alias("_ingest_ts"),
            lit("samples.tpch.part").alias("_source_table")
        )
    )

@dlt.table(
    name="supplier_raw",
    comment="Raw supplier data from samples.tpch.supplier"
)
def supplier_raw():
    return (
        spark.readStream.table("samples.tpch.supplier")
        .select(
            "*",
            current_timestamp().alias("_ingest_ts"),
            lit("samples.tpch.supplier").alias("_source_table")
        )
    )

@dlt.table(
    name="partsupp_raw",
    comment="Raw partsupp data from samples.tpch.partsupp"
)
def partsupp_raw():
    return (
        spark.readStream.table("samples.tpch.partsupp")
        .select(
            "*",
            current_timestamp().alias("_ingest_ts"),
            lit("samples.tpch.partsupp").alias("_source_table")
        )
    )

@dlt.table(
    name="nation_raw",
    comment="Raw nation data from samples.tpch.nation"
)
def nation_raw():
    return (
        spark.readStream.table("samples.tpch.nation")
        .select(
            "*",
            current_timestamp().alias("_ingest_ts"),
            lit("samples.tpch.nation").alias("_source_table")
        )
    )

@dlt.table(
    name="region_raw",
    comment="Raw region data from samples.tpch.region"
)
def region_raw():
    return (
        spark.readStream.table("samples.tpch.region")
        .select(
            "*",
            current_timestamp().alias("_ingest_ts"),
            lit("samples.tpch.region").alias("_source_table")
        )
    )