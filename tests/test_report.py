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
    assert "Spending this week:" in report and "$70.00" in report
    assert "Spending last week:" in report and "unavailable" in report
    assert "Average spending/day this week:" in report
    assert "4-week average spending/day:" in report
    assert "Difference vs 4-week average:" in report and "-20.0%" in report
    assert report.index("Average spending/day this week") < report.index(
        "4-week average spending/day"
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
    assert "Spending this month:" in report
    assert "Spending last month:" in report
    assert "Change vs last month:" in report and "-$350.00" in report
    assert "Percent change vs last month:" in report and "-58.3%" in report
    assert "Average spending/day this month:" in report
    assert "3-month average spending/month:" in report and "$383.33" in report
    assert "Difference vs 3-month average:" in report and "-34.8%" in report


def test_spending_comparison_is_unavailable_when_rolling_average_is_zero():
    weekly = generate_weekly_report([], date(2026, 8, 23))
    monthly = generate_monthly_report([], date(2026, 8, 23))

    assert any(
        line.startswith("Difference vs 4-week average:") and line.endswith("n/a")
        for line in weekly.splitlines()
    )
    assert any(
        line.startswith("Difference vs 3-month average:") and line.endswith("n/a")
        for line in monthly.splitlines()
    )


def test_report_sections_use_the_overview_value_column():
    report = generate_monthly_report(
        [
            tx(
                "purchase",
                "Corner Store",
                25,
                day="2026-08-06",
                item_key="checking",
            )
        ],
        date(2026, 8, 31),
    )
    lines = report.splitlines()
    value_column = next(
        line.index("$") for line in lines if line.startswith("Spending this month:")
    )
    aligned_lines = [
        line
        for line in lines
        if line.startswith(
            (
                "Inflows:",
                "Outflows:",
                "Net cash flow:",
                "  Inflows:",
                "  Outflows:",
                "  Net cash flow:",
                "Shopping",
                "Corner Store",
            )
        )
    ]

    assert aligned_lines
    assert all(
        line.find("$", value_column) in (value_column, value_column + 1)
        for line in aligned_lines
    )
