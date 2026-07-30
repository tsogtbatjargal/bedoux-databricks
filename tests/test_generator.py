from src.bedoux import generator


def test_generate_clients_count_and_schema():
    rows = generator.generate_clients(n=10)
    assert len(rows) == 10
    assert {"client_id", "client_name", "tier", "signup_date"} <= rows[0].keys()
    assert len({r["client_id"] for r in rows}) == 10  # unique keys


def test_generate_clients_is_deterministic():
    a = generator.generate_clients(n=10, seed=42)
    b = generator.generate_clients(n=10, seed=42)
    assert a == b


def test_generate_campaigns_reference_valid_clients():
    client_ids = [c["client_id"] for c in generator.generate_clients(n=5)]
    campaigns = generator.generate_campaigns(client_ids, n_per_client=3)
    assert len(campaigns) == 15
    assert all(c["client_id"] in client_ids for c in campaigns)
    assert len({c["campaign_id"] for c in campaigns}) == 15  # unique keys


def test_generate_leads_has_deliberate_invalid_rows():
    campaign_ids = list(range(1, 31))
    leads = generator.generate_leads(campaign_ids, n=1000, invalid_rate=0.02)
    assert len(leads) == 1000
    invalid = [l for l in leads if l["campaign_id"] is None]
    valid = [l for l in leads if l["campaign_id"] is not None]
    # roughly 2% invalid, but assert bounds rather than an exact count (still seeded/deterministic)
    assert 0 < len(invalid) < 60
    assert all(l["campaign_id"] in campaign_ids for l in valid)


def test_generate_web_events_has_deliberate_invalid_rows():
    events = generator.generate_web_events([1, 2, 3], n=1000, invalid_rate=0.02)
    invalid = [e for e in events if e["session_duration_seconds"] < 0]
    assert 0 < len(invalid) < 60
    assert all(e["session_duration_seconds"] >= 0 for e in events if e not in invalid)


def test_generate_ops_events_has_deliberate_invalid_rows():
    events = generator.generate_ops_events(n=365, invalid_rate=0.02)
    assert len(events) == 365
    invalid = [e for e in events if e["latency_seconds"] is None]
    assert 0 < len(invalid) < 40
