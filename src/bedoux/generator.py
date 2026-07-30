"""Deterministic synthetic data for the Bedoux Ops & Marketing Analytics track.

All data here is fictional (see docs/contracts-bedoux.md). No external calls, no
`pip install` dependency at pipeline runtime — plain stdlib `random` with fixed
seeds, so results are reproducible across pipeline runs and in unit tests.

A small, fixed percentage of rows in leads/web_events/ops_events are deliberately
invalid (a null key, a negative duration, a missing latency) so the Silver-layer
DLT expectations have something real to drop.
"""

import random
from datetime import datetime, timedelta

SEED = 42
INVALID_RATE = 0.02

CLIENT_NAMES = [
    "Northwind Outfitters", "Maple & Co", "Aurora Fitness", "Cobalt Roasters",
    "Trailhead Realty", "Lumen Dental", "Birchwood Legal", "Solstice Yoga",
    "Ferro Hardware", "Willow Creek Bakery",
]
TIERS = ["starter", "growth", "enterprise"]
CHANNELS = ["paid_social", "search", "email", "referral", "content"]
CAMPAIGN_STATUSES = ["planned", "active", "completed", "paused"]
FUNNEL_STAGES = ["new", "qualified", "won", "lost"]
EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "company.com"]
OPS_EVENT_TYPES = ["daily_plan_run", "telegram_message"]


def generate_clients(n=10, seed=SEED):
    rng = random.Random(seed)
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "client_id": i,
            "client_name": CLIENT_NAMES[(i - 1) % len(CLIENT_NAMES)],
            "tier": rng.choice(TIERS),
            "signup_date": (datetime(2025, 1, 1) + timedelta(days=rng.randint(0, 540))).date().isoformat(),
        })
    return rows


def generate_campaigns(client_ids, n_per_client=3, seed=SEED):
    rng = random.Random(seed + 1)
    rows = []
    campaign_id = 1
    for client_id in client_ids:
        for _ in range(n_per_client):
            start = datetime(2025, 6, 1) + timedelta(days=rng.randint(0, 300))
            rows.append({
                "campaign_id": campaign_id,
                "client_id": client_id,
                "channel": rng.choice(CHANNELS),
                "budget": round(rng.uniform(200, 5000), 2),
                "status": rng.choice(CAMPAIGN_STATUSES),
                "start_date": start.date().isoformat(),
                "end_date": (start + timedelta(days=rng.randint(14, 90))).date().isoformat(),
            })
            campaign_id += 1
    return rows


def generate_leads(campaign_ids, n=500, invalid_rate=INVALID_RATE, seed=SEED):
    rng = random.Random(seed + 2)
    rows = []
    for i in range(1, n + 1):
        invalid = rng.random() < invalid_rate
        rows.append({
            "lead_id": i,
            "campaign_id": None if invalid else rng.choice(campaign_ids),
            "stage": rng.choice(FUNNEL_STAGES),
            "created_ts": (
                datetime(2025, 6, 1) + timedelta(days=rng.randint(0, 400), minutes=rng.randint(0, 1440))
            ).isoformat(),
            "email_domain": rng.choice(EMAIL_DOMAINS),
        })
    return rows


def generate_web_events(campaign_ids, n=2000, invalid_rate=INVALID_RATE, seed=SEED):
    rng = random.Random(seed + 3)
    rows = []
    for i in range(1, n + 1):
        invalid = rng.random() < invalid_rate
        rows.append({
            "event_id": i,
            "campaign_id": rng.choice(campaign_ids),
            "session_duration_seconds": -1 if invalid else rng.randint(1, 900),
            "page_views": rng.randint(1, 12),
            "event_ts": (datetime(2025, 6, 1) + timedelta(days=rng.randint(0, 400))).isoformat(),
        })
    return rows


def generate_ops_events(n=365, invalid_rate=INVALID_RATE, seed=SEED):
    rng = random.Random(seed + 4)
    rows = []
    for i in range(1, n + 1):
        invalid = rng.random() < invalid_rate
        rows.append({
            "ops_event_id": i,
            "event_type": rng.choice(OPS_EVENT_TYPES),
            "success": rng.random() > 0.05,
            "latency_seconds": None if invalid else round(rng.uniform(0.2, 12.0), 2),
            "event_ts": (
                datetime(2025, 1, 1) + timedelta(days=i // 2, hours=rng.randint(0, 23))
            ).isoformat(),
        })
    return rows
