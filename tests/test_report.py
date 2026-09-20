from datetime import date
from personal_treasury.report import generate_monthly_report, generate_weekly_report
from tests.fixtures.transactions import tx


def test_rolling_week_and_missing_comparison():
    report = generate_weekly_report(
        [
            tx("a", "Earlier shop", 280, day="2026-07-27"),
            tx("b", "Current shop", 70, day="2026-08-20"),
        ],
        date(2026, 8, 23),
    )
    assert "August 17 - August 23, 2026" in report
    assert "Previous period comparison unavailable" in report
    assert "4-week average spending/day: $12.50" in report
    assert "Trend: -20.0%" in report
    assert "Average spending/day:  $10.00" in report
    assert report.index("4-week average spending/day") < report.index(
        "Average spending/day"
    )
    assert "CASH FLOW BY PLAID ACCOUNT" in report
    assert report.index("TOTAL CASH FLOW") < report.index("CASH FLOW BY PLAID ACCOUNT")


def test_current_month_and_savings_rate():
    report = generate_monthly_report(
        [
            tx("a", "June shop", 300, day="2026-06-05"),
            tx("b", "July shop", 600, day="2026-07-05"),
            tx("c", "Payroll", -1000, day="2026-08-05"),
            tx("d", "August shop", 250, day="2026-08-06"),
        ],
        date(2026, 8, 23),
    )
    assert "August 2026" in report and "Cash-flow savings rate: 75.0%" in report
    assert "3-month average spending/month: $383.33" in report
    assert "Trend: -34.8%" in report


def test_spending_trend_is_unavailable_when_rolling_average_is_zero():
    weekly = generate_weekly_report([], date(2026, 8, 23))
    monthly = generate_monthly_report([], date(2026, 8, 23))

    assert "Trend: n/a" in weekly
    assert "Trend: n/a" in monthly
