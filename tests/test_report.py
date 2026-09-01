from datetime import date
from personal_treasury.report import generate_monthly_report, generate_weekly_report
from tests.fixtures.transactions import tx


def test_rolling_week_and_missing_comparison():
    report = generate_weekly_report([tx("a", "Shop", 10, day="2026-08-12")], date(2026, 8, 23))
    assert "August 17 - August 23, 2026" in report
    assert "Previous period comparison unavailable" in report
    assert "CASH FLOW BY PLAID ACCOUNT" in report
    assert report.index("TOTAL CASH FLOW") < report.index("CASH FLOW BY PLAID ACCOUNT")


def test_current_month_and_savings_rate():
    report = generate_monthly_report([tx("a", "Payroll", -1000, day="2026-08-05"), tx("b", "Shop", 250, day="2026-08-06")], date(2026, 8, 23))
    assert "August 2026" in report and "Cash-flow savings rate: 75.0%" in report
