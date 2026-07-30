import dlt
from pyspark.sql.functions import col, sum, count, countDistinct, min, max, avg, when, rank, date_trunc, ntile, coalesce, lit
from pyspark.sql.window import Window

# Gold Layer: Business-ready analytical tables
# One table per business question
# Reads from workspace.silver ONLY
# Revenue defined consistently as sum(l_extendedprice * (1 - l_discount))

# =============================================================================
# Table 1: Monthly Revenue by Region
# =============================================================================

@dlt.table(
    name="gold_monthly_revenue_by_region",
    comment="Monthly revenue by region. Grain: one row per region per month. Revenue = sum(l_extendedprice * (1 - l_discount))."
)
def gold_monthly_revenue_by_region():
    return (
        spark.read.table("workspace.silver.lineitem_clean")
        .filter(col("l_orderkey").isNotNull())
        .join(
            spark.read.table("workspace.silver.orders_clean").filter(col("o_orderkey").isNotNull() & col("o_orderdate").isNotNull()),
            col("l_orderkey") == col("o_orderkey"),
            "inner"
        )
        .join(
            spark.read.table("workspace.silver.customer_clean").filter(col("c_custkey").isNotNull()),
            col("o_custkey") == col("c_custkey"),
            "inner"
        )
        .join(
            spark.read.table("workspace.silver.nation_clean").filter(col("n_nationkey").isNotNull()),
            col("c_nationkey") == col("n_nationkey"),
            "inner"
        )
        .join(
            spark.read.table("workspace.silver.region_clean").filter(col("r_regionkey").isNotNull()),
            col("n_regionkey") == col("r_regionkey"),
            "inner"
        )
        .withColumn("revenue", col("l_extendedprice") * (1 - coalesce(col("l_discount"), lit(0))))
        .withColumn("month_date", date_trunc("month", col("o_orderdate")))
        .groupBy(
            col("r_name").alias("region_name"),
            col("month_date")
        )
        .agg(
            sum(col("revenue")).alias("revenue")
        )
        .orderBy("region_name", "month_date")
    )

# =============================================================================
# Table 2: Customer Lifetime Value
# =============================================================================

@dlt.table(
    name="gold_customer_lifetime_value",
    comment="Customer lifetime value. Grain: one row per customer. Includes total orders, total revenue, avg order value, first/last order date, value segment."
)
def gold_customer_lifetime_value():
    # Calculate customer metrics
    customer_metrics = (
        spark.read.table("workspace.silver.customer_clean")
        .filter(col("c_custkey").isNotNull())
        .join(
            spark.read.table("workspace.silver.orders_clean").filter(col("o_orderkey").isNotNull() & col("o_custkey").isNotNull()),
            col("c_custkey") == col("o_custkey"),
            "inner"
        )
        .join(
            spark.read.table("workspace.silver.lineitem_clean").filter(col("l_orderkey").isNotNull()),
            col("o_orderkey") == col("l_orderkey"),
            "inner"
        )
        .withColumn("revenue", col("l_extendedprice") * (1 - coalesce(col("l_discount"), lit(0))))
        .groupBy(
            col("c_custkey").alias("customer_key"),
            col("c_name").alias("customer_name")
        )
        .agg(
            countDistinct(col("o_orderkey")).alias("total_orders"),
            sum(col("revenue")).alias("total_revenue"),
            min(col("o_orderdate")).alias("first_order_date"),
            max(col("o_orderdate")).alias("last_order_date")
        )
        .withColumn("avg_order_value", col("total_revenue") / col("total_orders"))
    )
    
    # Add value segment using percentile-based approach
    window_spec = Window.orderBy(col("total_revenue"))
    
    return (
        customer_metrics
        .withColumn("revenue_percentile", ntile(5).over(window_spec))
        .withColumn(
            "value_segment",
            when(col("revenue_percentile") == 1, "Low")
            .when(col("revenue_percentile").isin(2, 3, 4), "Medium")
            .when(col("revenue_percentile") == 5, "High")
            .otherwise("Unknown")
        )
        .select(
            "customer_key",
            "customer_name",
            "total_orders",
            "total_revenue",
            "avg_order_value",
            "first_order_date",
            "last_order_date",
            "value_segment"
        )
        .orderBy(col("total_revenue").desc())
    )

# =============================================================================
# Table 3: Top Products
# =============================================================================

@dlt.table(
    name="gold_top_products",
    comment="Product performance metrics. Grain: one row per product. Includes total revenue, quantity, order count, revenue rank."
)
def gold_top_products():
    # Calculate product metrics
    product_metrics = (
        spark.read.table("workspace.silver.part_clean")
        .filter(col("p_partkey").isNotNull())
        .join(
            spark.read.table("workspace.silver.lineitem_clean").filter(col("l_partkey").isNotNull()),
            col("p_partkey") == col("l_partkey"),
            "inner"
        )
        .withColumn("revenue", col("l_extendedprice") * (1 - coalesce(col("l_discount"), lit(0))))
        .groupBy(
            col("p_partkey").alias("product_key"),
            col("p_name").alias("product_name")
        )
        .agg(
            sum(col("revenue")).alias("total_revenue"),
            sum(col("l_quantity")).alias("total_quantity"),
            countDistinct(col("l_orderkey")).alias("order_count")
        )
    )
    
    # Add revenue rank
    window_spec = Window.orderBy(col("total_revenue").desc())
    
    return (
        product_metrics
        .withColumn("revenue_rank", rank().over(window_spec))
        .select(
            "product_key",
            "product_name",
            "total_revenue",
            "total_quantity",
            "order_count",
            "revenue_rank"
        )
        .orderBy("revenue_rank")
    )