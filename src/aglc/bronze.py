import sys

import dlt
from pyspark.sql.functions import current_timestamp, lit

# Track 3 Bronze (docs/contracts-aglc.md): raw landing from the seeded synthetic
# generator. Materialized, idempotent recompute, same reasoning as Track 2's Bronze.
# The shared src/ root and the catalog come in through pipeline configuration.

sys.path.append(spark.conf.get("bundle.sourcePath"))  # noqa: F821
from aglc import generator  # noqa: E402

SCHEMAS = generator.RAW_SCHEMAS


def _gaming():
    players = generator.generate_players()
    return players, generator.generate_gaming_activity([p["player_id"] for p in players])


def _land(entity, rows, source):
    # Explicit schemas: nullable keys in the invalid rows defeat type inference.
    rows = [{**r, "_row_id": i} for i, r in enumerate(rows)]
    return (
        spark.createDataFrame(rows, schema=SCHEMAS[entity] + ", _row_id LONG")  # noqa: F821
        .withColumn("_ingest_ts", current_timestamp())
        .withColumn("_source_table", lit(f"aglc_synthetic.{source}"))
    )


@dlt.table(name="gaming_players_raw", comment="Synthetic players. email and date_of_birth are PII (synthetic).")
def gaming_players_raw():
    return _land("players", _gaming()[0], "players")


@dlt.table(name="gaming_sessions_raw", comment="Synthetic play sessions (includes deliberate invalid rows)")
def gaming_sessions_raw():
    return _land("sessions", _gaming()[1][0], "sessions")


@dlt.table(name="gaming_wagers_raw", comment="Synthetic wagers (includes deliberate invalid rows)")
def gaming_wagers_raw():
    return _land("wagers", _gaming()[1][1], "wagers")


@dlt.table(name="gaming_deposits_raw", comment="Synthetic deposits (includes deliberate invalid rows)")
def gaming_deposits_raw():
    return _land("deposits", _gaming()[1][2], "deposits")


@dlt.table(name="retail_licensees_raw", comment="Synthetic liquor and cannabis licensees")
def retail_licensees_raw():
    return _land("licensees", generator.generate_licensees(), "licensees")


@dlt.table(name="retail_orders_raw", comment="Synthetic wholesale order lines (includes deliberate invalid rows)")
def retail_orders_raw():
    return _land("orders", generator.generate_orders(generator.generate_licensees()), "orders")
