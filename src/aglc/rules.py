"""Responsible-gaming rules: the tested reference spec for gold_rg_player_flags.

Pure Python, no Spark. gold.py reimplements the same logic as Spark expressions
(same reasoning as src/bedoux/transforms.py), and these functions stay the
authoritative definition. Thresholds are illustrative, not clinical guidance;
see docs/contracts-aglc.md.

Inputs are Silver-clean rows (already validated).
"""

from collections import defaultdict
from statistics import median

CHASING_MIN_DAYS = 3
CHASING_MIN_DEPOSITS = 2
SPIKE_MIN_DAYS = 5
SPIKE_FACTOR = 3.0
LONG_SESSION_MINUTES = 240


def _day(ts):
    return ts[:10]


def player_daily(sessions, wagers, deposits):
    """Aggregate to player × day: the grain of gold_gaming_player_daily."""
    out = defaultdict(lambda: {
        "total_stake": 0.0, "total_payout": 0.0, "deposit_total": 0.0,
        "deposit_count": 0, "session_minutes": 0,
    })
    for w in wagers:
        d = out[(w["player_id"], _day(w["wager_ts"]))]
        d["total_stake"] += w["stake"]
        d["total_payout"] += w["payout"]
    for dep in deposits:
        d = out[(dep["player_id"], _day(dep["deposit_ts"]))]
        d["deposit_total"] += dep["amount"]
        d["deposit_count"] += 1
    for s in sessions:
        out[(s["player_id"], _day(s["start_ts"]))]["session_minutes"] += s["duration_minutes"]
    rows = []
    for (pid, day), d in sorted(out.items()):
        rows.append({
            "player_id": pid,
            "activity_date": day,
            "total_stake": round(d["total_stake"], 2),
            "total_payout": round(d["total_payout"], 2),
            "net_loss": round(d["total_stake"] - d["total_payout"], 2),
            "deposit_total": round(d["deposit_total"], 2),
            "deposit_count": d["deposit_count"],
            "session_minutes": d["session_minutes"],
        })
    return rows


def chasing_losses(days):
    hits = [d for d in days if d["net_loss"] > 0 and d["deposit_count"] >= CHASING_MIN_DEPOSITS]
    return len(hits) >= CHASING_MIN_DAYS


def deposit_spike(days):
    totals = [d["deposit_total"] for d in days if d["deposit_count"] > 0]
    if len(totals) < SPIKE_MIN_DAYS:
        return False
    return max(totals) > SPIKE_FACTOR * median(totals)


def long_session(player_sessions):
    return any(s["duration_minutes"] >= LONG_SESSION_MINUTES for s in player_sessions)


def risk_level(flags):
    if flags["flag_self_exclusion_breach"]:
        return "high"
    other = sum(flags[k] for k in ("flag_chasing_losses", "flag_deposit_spike", "flag_long_session"))
    return "high" if other >= 2 else "medium" if other == 1 else "low"


EXPLANATIONS = {
    "flag_chasing_losses": f"{CHASING_MIN_DAYS}+ losing days with repeated deposits",
    "flag_deposit_spike": f"a deposit day over {SPIKE_FACTOR:g}x the player's usual",
    "flag_long_session": f"a session of {LONG_SESSION_MINUTES}+ minutes",
    "flag_self_exclusion_breach": "wagered while self-excluded",
}


def player_flags(players, sessions, wagers, deposits):
    """One row per player: the grain of gold_rg_player_flags."""
    daily = defaultdict(list)
    for d in player_daily(sessions, wagers, deposits):
        daily[d["player_id"]].append(d)
    by_player_sessions = defaultdict(list)
    for s in sessions:
        by_player_sessions[s["player_id"]].append(s)
    wagered = {w["player_id"] for w in wagers}

    rows = []
    for p in sorted(players, key=lambda p: p["player_id"]):
        pid = p["player_id"]
        flags = {
            "flag_chasing_losses": chasing_losses(daily[pid]),
            "flag_deposit_spike": deposit_spike(daily[pid]),
            "flag_long_session": long_session(by_player_sessions[pid]),
            "flag_self_exclusion_breach": bool(p["self_excluded"]) and pid in wagered,
        }
        rows.append({
            "player_id": pid,
            **flags,
            "risk_level": risk_level(flags),
            "explanation": "; ".join(EXPLANATIONS[k] for k, v in flags.items() if v) or "no rule triggered",
        })
    return rows
