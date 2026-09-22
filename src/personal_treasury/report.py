import logging
from datetime import date, timedelta
from pathlib import Path

from .spending import get_spending_summary

logger = logging.getLogger(__name__)


def _weekly_period(as_of):
    as_of = as_of or date.today()
    # Rolling seven-day window ending on the report date.
    return as_of - timedelta(days=6), as_of


def _monthly_period(as_of):
    as_of = as_of or date.today()
    # Current calendar month through the report date. The scheduler invokes
    # this on month-end, producing the complete month.
    return as_of.replace(day=1), as_of


def _month_start_months_ago(value, months):
    month_index = value.year * 12 + value.month - 1 - months
    return date(month_index // 12, month_index % 12 + 1, 1)


def _money(value):
    return f"${value:,.2f}"


def _pct(value):
    return "n/a" if value is None else f"{value * 100:+.1f}%"


def _signed_money(value):
    sign = "+" if value >= 0 else "-"
    return f"{sign}{_money(abs(value))}"


def _overview_line(label, value):
    return f"{label + ':':<39}{value}"


def _section_line(label, value):
    return f"{label:<39}{value}"


def _render(
    title,
    summary,
    previous,
    period_label,
    period_name,
    spending_comparison_lines=(),
):
    lines = [
        "PERSONAL TREASURY",
        title,
        "",
        f"Period: {period_label}",
        "",
        "OVERVIEW",
        _overview_line(
            f"Spending this {period_name}", _money(summary["total_spending"])
        ),
    ]
    if previous:
        change = summary["total_spending"] - previous["total_spending"]
        lines += [
            _overview_line(
                f"Spending last {period_name}", _money(previous["total_spending"])
            ),
            _overview_line(f"Change vs last {period_name}", _signed_money(change)),
            _overview_line(
                f"Percent change vs last {period_name}",
                _pct(
                    change / previous["total_spending"]
                    if previous["total_spending"]
                    else None
                ),
            ),
        ]
    else:
        lines += [
            _overview_line(f"Spending last {period_name}", "unavailable"),
        ]
    lines += [
        _overview_line("Income", _money(summary["total_income"])),
        _overview_line("Net cash flow", _money(summary["net_cash_flow"])),
        _overview_line("Transactions", summary["transaction_count"]),
        _overview_line(
            f"Average spending/day this {period_name}",
            _money(summary["average_daily_spending"]),
        ),
        *spending_comparison_lines,
        "",
        "TOTAL CASH FLOW",
        _overview_line("Inflows", _money(summary["total_inflows"])),
        _overview_line("Outflows", f"-{_money(summary['total_outflows'])}"),
        _overview_line(
            "Net cash flow", _money(summary["total_account_net_cash_flow"])
        ),
        "",
        "CASH FLOW BY PLAID ACCOUNT",
    ]
    for account, flow in sorted(summary["cash_flow_by_account"].items()):
        lines += [
            account,
            _overview_line("  Inflows", _money(flow["inflows"])),
            _overview_line("  Outflows", f"-{_money(flow['outflows'])}"),
            _overview_line("  Net cash flow", _money(flow["net_cash_flow"])),
        ]
    lines += ["", "SPENDING BY CATEGORY"]
    lines += [
        _section_line(key, _money(value))
        for key, value in sorted(
            summary["spending_by_category"].items(), key=lambda x: x[1], reverse=True
        )
    ] or [_section_line("Other", _money(0))]
    lines += ["", "TOP MERCHANTS"]
    lines += [
        _section_line(key, _money(value))
        for key, value in sorted(
            summary["spending_by_merchant"].items(), key=lambda x: x[1], reverse=True
        )[:5]
    ] or [_section_line("None", _money(0))]
    if summary["savings_rate"] is not None:
        lines += ["", f"Cash-flow savings rate: {summary['savings_rate'] * 100:.1f}%"]
    return "\n".join(lines) + "\n"


def generate_weekly_report(transactions, as_of_date=None):
    start, end = _weekly_period(as_of_date)
    prev_start, prev_end = start - timedelta(days=7), start - timedelta(days=1)
    summary = get_spending_summary(transactions, start, end)
    previous = get_spending_summary(transactions, prev_start, prev_end)
    if previous["transaction_count"] == 0:
        previous = None
    four_week_start = end - timedelta(days=27)
    four_week_summary = get_spending_summary(transactions, four_week_start, end)
    four_week_average = four_week_summary["total_spending"] / 28
    weekly_trend = (
        (summary["average_daily_spending"] - four_week_average) / four_week_average
        if four_week_average
        else None
    )
    return _render(
        "WEEKLY SPENDING REPORT",
        summary,
        previous,
        f"{start.strftime('%B %-d')} - {end.strftime('%B %-d, %Y')}",
        "week",
        (
            _overview_line(
                "4-week average spending/day", _money(four_week_average)
            ),
            _overview_line(
                "Difference vs 4-week average", _pct(weekly_trend)
            ),
        ),
    )


def generate_monthly_report(transactions, as_of_date=None):
    start, end = _monthly_period(as_of_date)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    summary = get_spending_summary(transactions, start, end)
    previous = get_spending_summary(transactions, prev_start, prev_end)
    if previous["transaction_count"] == 0:
        previous = None
    three_month_start = _month_start_months_ago(start, 2)
    three_month_summary = get_spending_summary(transactions, three_month_start, end)
    three_month_average = three_month_summary["total_spending"] / 3
    monthly_trend = (
        (summary["total_spending"] - three_month_average) / three_month_average
        if three_month_average
        else None
    )
    text = _render(
        "MONTHLY FINANCIAL REPORT",
        summary,
        previous,
        start.strftime("%B %Y"),
        "month",
        (
            _overview_line(
                "3-month average spending/month", _money(three_month_average)
            ),
            _overview_line(
                "Difference vs 3-month average", _pct(monthly_trend)
            ),
        ),
    )
    return text


def save_report(content, kind, period_end, reports_dir="data/reports"):
    directory = Path(reports_dir)
    directory.mkdir(parents=True, exist_ok=True)
    suffix = (
        period_end.strftime("%Y-%m-%d")
        if kind == "weekly"
        else period_end.strftime("%Y-%m")
    )
    path = directory / f"{kind}-{suffix}.txt"
    path.write_text(content)
    logger.info("Report saved to %s", path)
    return path
