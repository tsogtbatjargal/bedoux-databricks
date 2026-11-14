"""Run a day of ingestion and the deterministic monitor (Track 4).

The monitor turns audit records and reconciliation reports into incidents. It
is rules only: an incident exists because a check failed, never because a
model said so. The investigator (investigator.py) explains incidents; it
doesn't create them.
"""

from . import ingest, reconcile
from .metadata import DEFAULT_DIR, load_specs

ORDER = ("sales.orders", "sales.order_lines", "sales.payments")


def run_day(scenario, specs, store, day):
    snap = scenario.snapshot(day)
    return [ingest.run_ingestion(specs[ds], snap[ds], store, label=f"day{day}") for ds in ORDER]


def reconcile_day(scenario, specs, store, day):
    snap = scenario.snapshot(day)
    orders = ingest.live_rows(store, "sales.orders")
    lines = ingest.live_rows(store, "sales.order_lines")
    payments = ingest.live_rows(store, "sales.payments")
    return {
        "source_to_target": reconcile.source_to_target(
            specs["sales.payments"], snap["sales.payments"],
            list(store.tables.get("sales.payments", {}).values())),
        "payments_vs_orders": reconcile.payments_vs_orders(orders, lines, payments),
    }


def detect_incidents(records, recon, day):
    """Return incident dicts for one day. Each names its trigger and the
    run ids or check that fired, which is all the investigator starts with."""
    incidents = []
    for r in records:
        if r["status"] == ingest.FAILED:
            trigger = "ingestion_failed"
        elif r["status"] == ingest.SUCCEEDED_WITH_QUARANTINE:
            trigger = "rows_quarantined"
        elif r["rows_new"] == 0:
            trigger = "no_new_data"
        elif r["schema_diff"]["added"]:
            trigger = "schema_drift_additive"
        else:
            continue
        incidents.append({"incident_key": f"day{day}:{r['dataset_id']}:{trigger}",
                          "trigger": trigger, "dataset_id": r["dataset_id"],
                          "run_id": r["run_id"], "status": r["status"],
                          "failure_code": r["failure_code"]})
    if not recon["source_to_target"]["passed"]:
        incidents.append({"incident_key": f"day{day}:sales.payments:source_to_target",
                          "trigger": "source_to_target_mismatch", "dataset_id": "sales.payments",
                          "run_id": None, "status": "check_failed", "failure_code": None})
    if not recon["payments_vs_orders"]["passed"]:
        incidents.append({"incident_key": f"day{day}:sales.payments:payments_vs_orders",
                          "trigger": "payments_vs_orders_mismatch", "dataset_id": "sales.payments",
                          "run_id": None, "status": "check_failed", "failure_code": None})
    return incidents


def simulate(scenario, specs=None, through_day=3):
    """Run days 1..through_day. Returns (store, {day: (records, recon, incidents)})."""
    specs = specs or load_specs(DEFAULT_DIR)
    store = ingest.MetadataStore()
    days = {}
    for day in range(1, through_day + 1):
        records = run_day(scenario, specs, store, day)
        recon = reconcile_day(scenario, specs, store, day)
        days[day] = (records, recon, detect_incidents(records, recon, day))
    return store, days
