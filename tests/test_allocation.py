from decimal import Decimal

import pytest

from personal_treasury.allocation import calculate_allocation
from personal_treasury.allocation_config import load_allocation_config
from tests.test_allocation_config import config


def result(tmp_path, balances, cash, text=None):
    loaded = load_allocation_config(config(tmp_path, text) if text else config(tmp_path))
    return calculate_allocation(loaded, balances, cash)


def amounts(value):
    return {item.account_key: item.allocation for item in value.recommendations}


def test_waterfall_and_percentage_surplus(tmp_path):
    value = result(tmp_path, {"checking": 8000, "emergency": 19500, "alpaca": 50000, "savings": 10000}, 3000)
    assert amounts(value) == {"checking": Decimal("0"), "emergency": Decimal("500"), "alpaca": Decimal("1750"), "savings": Decimal("750")}
    assert value.allocated_amount + value.unallocated_amount == value.available_cash


def test_insufficient_cash_respects_priority(tmp_path):
    value = result(tmp_path, {"checking": 3500, "emergency": 19000}, 800)
    assert amounts(value)["checking"] == 500
    assert amounts(value)["emergency"] == 300
    assert value.unallocated_amount == 0


def test_satisfied_target_ignore_and_zero_cash(tmp_path):
    text = """
version: 1
settings: {round_to: 1}
accounts:
  full: {type: target, target: 10, priority: 1}
  ignored: {type: ignore}
  destination: {type: percentage, percentage: 1, priority: 2}
"""
    value = result(tmp_path, {"full": 20}, 0, text)
    assert all(item.allocation == 0 for item in value.recommendations)
    assert amounts(value)["ignored"] == 0


def test_maximums_threshold_and_total_cap(tmp_path):
    text = """
version: 1
settings:
  minimum_allocation: 10
  round_to: 1
  maximum_total_allocation: 100
accounts:
  alpaca:
    type: percentage
    percentage: 1
    priority: 1
    maximum_allocation_per_run: 40
"""
    value = result(tmp_path, {"alpaca": 0}, 200, text)
    assert amounts(value)["alpaca"] == 40
    assert value.unallocated_amount == 160
    assert value.allocated_amount <= 100


def test_rounding_residual_reconciles(tmp_path):
    text = """
version: 1
settings: {round_to: 1}
accounts:
  a: {type: percentage, percentage: 0.33, priority: 1}
  b: {type: percentage, percentage: 0.33, priority: 1}
  c: {type: percentage, percentage: 0.34, priority: 1}
"""
    value = result(tmp_path, {}, 100, text)
    assert sum(amounts(value).values()) == Decimal("100")
    assert value.unallocated_amount == 0


def test_negative_cash_fails(tmp_path):
    with pytest.raises(ValueError, match="negative"):
        result(tmp_path, {}, -1)
