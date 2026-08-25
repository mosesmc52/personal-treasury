from decimal import Decimal

from personal_treasury.allocation import calculate_allocation
from personal_treasury.allocation_config import load_allocation_config
from personal_treasury.allocation_report import render_allocation_report
from tests.test_allocation_config import config


def test_report_contains_destinations_targets_and_safety_text(tmp_path):
    policy = load_allocation_config(config(tmp_path))
    result = calculate_allocation(policy, {"checking": 8000, "emergency": 19500}, 3000)
    report = render_allocation_report(result)
    assert "Emergency" in report
    assert "Target:" in report
    assert "Alpaca" in report
    assert "Unallocated:" in report
    assert "NO MONEY HAS BEEN MOVED." in report
