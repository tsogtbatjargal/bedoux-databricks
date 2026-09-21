import sys

import dlt
from pyspark.sql.functions import current_timestamp, lit

# Bronze Layer: materialized, idempotent recompute from the seeded synthetic
# generator. No real upstream stream to read incrementally -- see
# docs/contracts-bedoux.md for why this differs from Track 1's Bronze.
#
# DLT runs this file in a notebook-like cell with no `__file__`, so the shared
# src/ root is passed in via pipeline `configuration` (bundle.sourcePath,
# resolved from the bundle's ${workspace.file_path}) instead.

sys.path.append(spark.conf.get("bundle.sourcePath"))  # noqa: F821
from bedoux import generator  # noqa: E402

N_CLIENTS = 10
N_CAMPAIGNS_PER_CLIENT = 3
N_LEADS = 500
N_WEB_EVENTS = 2000
N_OPS_EVENTS = 365


def _with_row_id(rows):
    """Stamp each generated row with its position in this run's Python list,
    before it becomes a Spark DataFrame. `current_timestamp()` (`_ingest_ts`)
    is constant across every row of a single table computation, so it ties
    and can't order duplicates deterministically. `_row_id` is the batch
    identity chapter 02's dedup keys off of: Silver keeps the lowest `_row_id`
    for a given natural key and quarantines the rest as
    `duplicate_<key>` (see quality.py:dedup_by_key)."""
    return [{**row, "_row_id": i} for i, row in enumerate(rows)]


@dlt.table(
    name="clients_raw",
    comment="Raw synthetic client accounts from the Bedoux generator",
)
def clients_raw():
    rows = generator.generate_clients(n=N_CLIENTS)
    return (
        spark.createDataFrame(rows)
        .withColumn("_ingest_ts", current_timestamp())
        .withColumn("_source_table", lit("bedoux_synthetic.clients"))
    )


@dlt.table(
    name="campaigns_raw",
    comment="Raw synthetic marketing campaigns from the Bedoux generator",
)
def campaigns_raw():
    client_ids = [c["client_id"] for c in generator.generate_clients(n=N_CLIENTS)]
    rows = generator.generate_campaigns(client_ids, n_per_client=N_CAMPAIGNS_PER_CLIENT)
    return (
        spark.createDataFrame(rows)
        .withColumn("_ingest_ts", current_timestamp())
        .withColumn("_source_table", lit("bedoux_synthetic.campaigns"))
    )


@dlt.table(
    name="leads_raw",
    comment="Raw synthetic leads from the Bedoux generator (includes deliberate invalid rows)",
)
def leads_raw():
    client_ids = [c["client_id"] for c in generator.generate_clients(n=N_CLIENTS)]
    campaign_ids = [
        c["campaign_id"]
        for c in generator.generate_campaigns(client_ids, n_per_client=N_CAMPAIGNS_PER_CLIENT)
    ]
    invalid_rate = generator.parse_invalid_rate(
        spark.conf.get("bedoux.lead_invalid_rate", str(generator.INVALID_RATE))
    )
    rows = generator.generate_leads(campaign_ids, n=N_LEADS, invalid_rate=invalid_rate)
    return (
        # Explicit types also support the 100%-invalid fixture, where every
        # campaign_id is null and Spark cannot infer that column's type.
        spark.createDataFrame(
            _with_row_id(rows),
            schema="lead_id LONG, campaign_id LONG, stage STRING, created_ts STRING, email_domain STRING, _row_id LONG",
        )
        .withColumn("_ingest_ts", current_timestamp())
        .withColumn("_source_table", lit("bedoux_synthetic.leads"))
    )


@dlt.table(
    name="web_events_raw",
    comment="Raw synthetic website events from the Bedoux generator (includes deliberate invalid rows)",
)
def web_events_raw():
    client_ids = [c["client_id"] for c in generator.generate_clients(n=N_CLIENTS)]
    campaign_ids = [
        c["campaign_id"]
        for c in generator.generate_campaigns(client_ids, n_per_client=N_CAMPAIGNS_PER_CLIENT)
    ]
    rows = generator.generate_web_events(campaign_ids, n=N_WEB_EVENTS)
    return (
        spark.createDataFrame(_with_row_id(rows))
        .withColumn("_ingest_ts", current_timestamp())
        .withColumn("_source_table", lit("bedoux_synthetic.web_events"))
    )


@dlt.table(
    name="ops_events_raw",
    comment="Raw synthetic ogi operational events (daily-plan runs, Telegram messages) (includes deliberate invalid rows)",
)
def ops_events_raw():
    rows = generator.generate_ops_events(n=N_OPS_EVENTS)
    return (
        spark.createDataFrame(_with_row_id(rows))
        .withColumn("_ingest_ts", current_timestamp())
        .withColumn("_source_table", lit("bedoux_synthetic.ops_events"))
    )
