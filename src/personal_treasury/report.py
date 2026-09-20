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


def _render(title, summary, previous, period_label, spending_average_lines=()):
    lines = [
        "PERSONAL TREASURY",
        title,
        "",
        f"Period: {period_label}",
        "",
        "OVERVIEW",
        f"Total spending:        {_money(summary['total_spending'])}",
    ]
    if previous:
        change = summary["total_spending"] - previous["total_spending"]
        lines += [
            f"Previous period:       {_money(previous['total_spending'])}",
            f"Change:                {_money(change)}",
            f"Change:                {_pct(change / previous['total_spending'] if previous['total_spending'] else None)}",
        ]
    else:
        lines += ["Previous period comparison unavailable"]
    lines += [
        f"Income:                {_money(summary['total_income'])}",
        f"Net cash flow:         {_money(summary['net_cash_flow'])}",
        f"Transactions:          {summary['transaction_count']}",
        *spending_average_lines,
        f"Average spending/day:  {_money(summary['average_daily_spending'])}",
        "",
        "TOTAL CASH FLOW",
        f"Inflows:               {_money(summary['total_inflows'])}",
        f"Outflows:             -{_money(summary['total_outflows'])}",
        f"Net cash flow:          {_money(summary['total_account_net_cash_flow'])}",
        "",
        "CASH FLOW BY PLAID ACCOUNT",
    ]
    for account, flow in sorted(summary["cash_flow_by_account"].items()):
        lines += [
            account,
            f"  Inflows:             {_money(flow['inflows'])}",
            f"  Outflows:           -{_money(flow['outflows'])}",
            f"  Net cash flow:        {_money(flow['net_cash_flow'])}",
        ]
    lines += ["", "SPENDING BY CATEGORY"]
    lines += [
        f"{key:<22}{_money(value):>12}"
        for key, value in sorted(
            summary["spending_by_category"].items(), key=lambda x: x[1], reverse=True
        )
    ] or ["Other                   $0.00"]
    lines += ["", "TOP MERCHANTS"]
    lines += [
        f"{key:<22}{_money(value):>12}"
        for key, value in sorted(
            summary["spending_by_merchant"].items(), key=lambda x: x[1], reverse=True
        )[:5]
    ] or ["None                   $0.00"]
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
    return _render(
        "WEEKLY SPENDING REPORT",
        summary,
        previous,
        f"{start.strftime('%B %-d')} - {end.strftime('%B %-d, %Y')}",
        (
            "4-week average spending/day: "
            f"{_money(four_week_summary['total_spending'] / 28)}",
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
    text = _render(
        "MONTHLY FINANCIAL REPORT",
        summary,
        previous,
        start.strftime("%B %Y"),
        (
            "3-month average spending/month: "
            f"{_money(three_month_summary['total_spending'] / 3)}",
        ),
    )
    return text.replace("Total spending:", "Spending:             ", 1)


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
