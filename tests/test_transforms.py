import pytest

from src.bedoux.transforms import conversion_rate, cost_per_lead, ops_success_rate


@pytest.mark.parametrize(
    "won,total,expected",
    [
        (5, 20, 0.25),
        (0, 20, 0.0),
        (20, 20, 1.0),
        (0, 0, 0.0),
    ],
)
def test_conversion_rate(won, total, expected):
    assert conversion_rate(won, total) == expected


@pytest.mark.parametrize(
    "budget,leads,expected",
    [
        (1000, 10, 100.0),
        (1000, 0, None),
        (0, 5, 0.0),
    ],
)
def test_cost_per_lead(budget, leads, expected):
    assert cost_per_lead(budget, leads) == expected


@pytest.mark.parametrize(
    "success,total,expected",
    [
        (9, 10, 0.9),
        (0, 10, 0.0),
        (10, 10, 1.0),
        (0, 0, 0.0),
    ],
)
def test_ops_success_rate(success, total, expected):
    assert ops_success_rate(success, total) == expected
