from datetime import date
from decimal import Decimal
from pathlib import Path

from .allocation import AllocationResult


def _money(value):
    return f"${value:,.2f}"


def render_allocation_report(result: AllocationResult):
    lines = ["PERSONAL TREASURY", "ALLOCATION RECOMMENDATION", "", "AVAILABLE CASH", "", _money(result.available_cash), "", "TARGET ALLOCATIONS"]
    for recommendation in result.recommendations:
        if recommendation.rule_type in {"minimum", "target"}:
            target = recommendation.target if recommendation.target is not None else recommendation.projected_balance
            lines += ["", recommendation.account_name, f"Current:             {_money(recommendation.current_balance)}", f"Target:              {_money(target)}", f"Recommended:         {_money(recommendation.allocation)}", f"Projected:           {_money(recommendation.projected_balance)}"]
    lines += ["", "SURPLUS ALLOCATION"]
    for recommendation in result.recommendations:
        if recommendation.rule_type == "percentage":
            lines += ["", recommendation.account_name, f"Rule:                 {recommendation.percentage * 100}%", f"Recommended:         {_money(recommendation.allocation)}", f"Projected:           {_money(recommendation.projected_balance)}"]
    lines += ["", "SUMMARY", f"Available cash:       {_money(result.available_cash)}", f"Allocated:            {_money(result.allocated_amount)}", f"Unallocated:          {_money(result.unallocated_amount)}"]
    if result.warnings:
        lines += ["", "WARNINGS"] + [f"- {warning}" for warning in result.warnings]
    lines += ["", "NO MONEY HAS BEEN MOVED.", "This report is an allocation recommendation only."]
    return "\n".join(lines) + "\n"


def save_allocation_report(content, as_of_date=None, reports_dir="data/reports"):
    as_of_date = as_of_date or date.today()
    directory = Path(reports_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"allocation-{as_of_date:%Y-%m-%d}.txt"
    path.write_text(content)
    return path
