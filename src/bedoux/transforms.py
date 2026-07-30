"""Pure business-logic functions for the Gold layer.

Kept separate from gold.py and free of any Spark/DLT import so they're unit
testable in plain pytest (no cluster, no workspace). gold.py wraps these as UDFs
and applies them to the small, already-aggregated Gold-grain DataFrames.
"""


def conversion_rate(won_count: int, total_count: int) -> float:
    """Share of leads that reached the 'won' funnel stage."""
    if total_count == 0:
        return 0.0
    return won_count / total_count


def cost_per_lead(budget: float, lead_count: int):
    """Campaign budget divided by leads generated.

    Returns None (not 0.0) when there are no leads — a $0 cost-per-lead would
    misleadingly imply free acquisition rather than "no data."
    """
    if lead_count == 0:
        return None
    return budget / lead_count


def ops_success_rate(success_count: int, total_count: int) -> float:
    """Share of ogi ops events (daily-plan runs, Telegram messages) that succeeded."""
    if total_count == 0:
        return 0.0
    return success_count / total_count
