from datetime import date
from personal_treasury.report import generate_monthly_report, generate_weekly_report
from tests.fixtures.transactions import tx


def test_completed_week_and_missing_comparison():
    report = generate_weekly_report([tx("a", "Shop", 10, day="2026-08-12")], date(2026, 8, 23))
    assert "August 10 - August 16, 2026" in report
    assert "Previous period comparison unavailable" in report


def test_month_and_savings_rate():
    report = generate_monthly_report([tx("a", "Payroll", -1000, day="2026-07-05"), tx("b", "Shop", 250, day="2026-07-06")], date(2026, 8, 23))
    assert "July 2026" in report and "Cash-flow savings rate: 75.0%" in report

