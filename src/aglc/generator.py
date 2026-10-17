"""Deterministic synthetic data for Track 3: Regulated Gaming & Retail Lakehouse.

All data here is fictional (see docs/contracts-aglc.md). Plain stdlib `random` with
fixed seeds, so pipeline runs and unit tests see identical rows.

Two kinds of deliberate defects:
- about INVALID_RATE of detail rows are invalid (null keys, non-positive stakes,
  negative durations) so Silver expectations have something real to drop;
- a fixed set of PLANTED players behave riskily so responsible-gaming flags fire.
"""

import random
from datetime import date, datetime, timedelta

SEED = 7
INVALID_RATE = 0.02
START = date(2026, 1, 5)
DAYS = 60

REGIONS = ["Calgary", "Edmonton", "North", "Central", "South"]
GAME_TYPES = ["slots", "table", "sports", "lottery"]
EMAIL_DOMAINS = ["example.com", "mail.test", "inbox.test"]
CATEGORIES = {
    "liquor": ["beer", "wine", "spirits", "coolers"],
    "cannabis": ["flower", "pre_rolls", "edibles", "vapes"],
}

# Bronze schemas, declared explicitly: nullable keys in invalid rows defeat Spark
# type inference. Kept here (no Spark import) so tests can check them.
RAW_SCHEMAS = {
    "players": "player_id LONG, email STRING, date_of_birth STRING, region STRING, "
               "signup_date STRING, self_excluded BOOLEAN",
    "sessions": "session_id LONG, player_id LONG, start_ts STRING, duration_minutes LONG",
    "wagers": "wager_id LONG, session_id LONG, player_id LONG, game_type STRING, "
              "stake DOUBLE, payout DOUBLE, wager_ts STRING",
    "deposits": "deposit_id LONG, player_id LONG, amount DOUBLE, deposit_ts STRING",
    "licensees": "licensee_id LONG, licensee_name STRING, domain STRING, region STRING",
    "orders": "order_id LONG, licensee_id LONG, domain STRING, product_category STRING, "
              "order_date STRING, quantity LONG, amount DOUBLE",
}

# Player IDs with planted behaviour. Ordinary players never trigger these patterns.
PLANTED = {
    "chasing_losses": [1, 2],
    "deposit_spike": [2, 3],
    "long_session": [4],
    "self_exclusion_breach": [5],
}


def _day(i):
    return START + timedelta(days=i)


def _ts(day, minute):
    return datetime.combine(day, datetime.min.time()) + timedelta(minutes=minute)


def generate_players(n=200, seed=SEED):
    rng = random.Random(seed)
    rows = []
    for pid in range(1, n + 1):
        birth = date(1950, 1, 1) + timedelta(days=rng.randint(0, 365 * 50))
        rows.append({
            "player_id": pid,
            "email": f"player{pid}@{rng.choice(EMAIL_DOMAINS)}",
            "date_of_birth": birth.isoformat(),
            "region": rng.choice(REGIONS),
            "signup_date": (START - timedelta(days=rng.randint(30, 900))).isoformat(),
            "self_excluded": pid in PLANTED["self_exclusion_breach"],
        })
    return rows


def generate_gaming_activity(player_ids, invalid_rate=INVALID_RATE, seed=SEED):
    """Return (sessions, wagers, deposits) for the given players over DAYS days.

    Ordinary players: occasional short sessions, one small deposit on a play day.
    Planted players get the pattern their PLANTED entry names, on top of that.
    """
    rng = random.Random(seed + 1)
    sessions, wagers, deposits = [], [], []
    sid = wid = did = 0

    def add_session(pid, day, minutes, n_wagers, stake_range, losing):
        nonlocal sid, wid
        sid += 1
        bad = rng.random() < invalid_rate
        sessions.append({
            "session_id": sid,
            "player_id": pid,
            "start_ts": _ts(day, rng.randint(600, 1200)).isoformat(),
            "duration_minutes": -5 if bad else minutes,
        })
        for _ in range(n_wagers):
            wid += 1
            stake = round(rng.uniform(*stake_range), 2)
            payout = 0.0 if losing else round(stake * rng.uniform(0, 1.6), 2)
            bad = rng.random() < invalid_rate
            wagers.append({
                "wager_id": wid,
                "session_id": sid,
                "player_id": None if bad else pid,
                "game_type": rng.choice(GAME_TYPES),
                "stake": 0.0 if (bad and rng.random() < 0.5) else stake,
                "payout": payout,
                "wager_ts": _ts(day, rng.randint(600, 1300)).isoformat(),
            })

    def add_deposit(pid, day, amount):
        nonlocal did
        did += 1
        bad = rng.random() < invalid_rate
        deposits.append({
            "deposit_id": did,
            "player_id": None if bad else pid,
            "amount": round(amount, 2),
            "deposit_ts": _ts(day, rng.randint(500, 1400)).isoformat(),
        })

    for pid in player_ids:
        for i in range(DAYS):
            day = _day(i)
            plays = rng.random() < 0.25
            if pid in PLANTED["chasing_losses"]:
                # Losing days followed by repeated top-ups, every sixth day. No ordinary
                # play, so small deposits don't make the top-ups look like a spike.
                if i % 6 == 0:
                    add_session(pid, day, 90, 6, (20, 60), losing=True)
                    add_deposit(pid, day, 100)
                    add_deposit(pid, day, 150)
                if not (pid in PLANTED["deposit_spike"] and i == DAYS - 3):
                    continue
            if pid in PLANTED["deposit_spike"] and i == DAYS - 3:
                add_session(pid, day, 60, 4, (10, 40), losing=False)
                add_deposit(pid, day, 2500)
                continue
            if pid in PLANTED["long_session"] and i == 10:
                add_session(pid, day, 300, 30, (2, 10), losing=False)
                continue
            if plays:
                add_session(pid, day, rng.randint(10, 120), rng.randint(1, 5), (1, 25), losing=False)
                add_deposit(pid, day, rng.uniform(20, 80))
    return sessions, wagers, deposits


def generate_licensees(n=40, seed=SEED):
    rng = random.Random(seed + 2)
    return [
        {
            "licensee_id": lid,
            "licensee_name": f"Licensee {lid:03d}",
            "domain": "liquor" if lid % 3 else "cannabis",
            "region": rng.choice(REGIONS),
        }
        for lid in range(1, n + 1)
    ]


def generate_orders(licensees, n=3000, invalid_rate=INVALID_RATE, seed=SEED):
    rng = random.Random(seed + 3)
    rows = []
    for oid in range(1, n + 1):
        lic = rng.choice(licensees)
        quantity = rng.randint(1, 40)
        unit_price = rng.uniform(8, 60)
        bad = rng.random() < invalid_rate
        rows.append({
            "order_id": oid,
            "licensee_id": None if bad else lic["licensee_id"],
            "domain": lic["domain"],
            "product_category": rng.choice(CATEGORIES[lic["domain"]]),
            "order_date": _day(rng.randint(0, DAYS - 1)).isoformat(),
            "quantity": quantity,
            "amount": -1.0 if (bad and rng.random() < 0.5) else round(quantity * unit_price, 2),
        })
    return rows
