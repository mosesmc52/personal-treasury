import argparse
import json
import logging
from calendar import monthrange
from datetime import date, timedelta

from .email_sender import send_report
from .allocation import calculate_allocation
from .allocation_config import load_allocation_config
from .allocation_report import render_allocation_report, save_allocation_report
from .report import _monthly_period, _weekly_period, generate_monthly_report, generate_weekly_report, save_report
from .transactions import sync_transactions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

WEEKDAYS = {name.lower(): number for number, name in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"))}


def _email(subject, content):
    try:
        send_report(subject, content)
    except Exception as exc:
        logging.error("Email delivery failed: %s", exc)
        return 1
    return 0


def _run_weekly(transactions, as_of):
    content = generate_weekly_report(transactions, as_of)
    _, period_end = _weekly_period(as_of)
    period_start = period_end - timedelta(days=6)
    subject = f"Personal Treasury — Weekly Report — {period_start:%b %-d}–{period_end:%-d}"
    print(content)
    save_report(content, "weekly", period_end)
    return _email(subject, content)


def _run_monthly(transactions, as_of, email=False):
    content = generate_monthly_report(transactions, as_of)
    period_start, period_end = _monthly_period(as_of)
    subject = f"Personal Treasury — {period_start:%B %Y} Report"
    print(content)
    save_report(content, "monthly", period_end)
    if email:
        return _email(subject, content)
    print("Monthly email skipped: pass --email to send it.")
    return 0


def _run_allocation(config_path, state_path, as_of, email=False):
    config = load_allocation_config(config_path)
    with open(state_path) as state_file:
        state = json.load(state_file)
    if not isinstance(state, dict) or "available_cash" not in state or not isinstance(state.get("balances"), dict):
        raise ValueError("Allocation state must contain available_cash and a balances mapping")
    result = calculate_allocation(config, state["balances"], state["available_cash"])
    content = render_allocation_report(result)
    print(content)
    path = save_allocation_report(content, as_of)
    logging.info("Allocation report saved to %s", path)
    if email:
        return _email(f"Personal Treasury — Allocation Recommendation — {as_of:%b %-d, %Y}", content)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Personal Treasury scheduled financial reports")
    parser.add_argument("command", choices=("sync", "daily", "weekly", "monthly", "allocate"))
    parser.add_argument("--as-of", type=date.fromisoformat, help="Use this date instead of today (YYYY-MM-DD)")
    parser.add_argument("--weekly-day", default="sunday", choices=tuple(WEEKDAYS), help="Daily mode report day (default: sunday)")
    parser.add_argument("--email", action="store_true", help="Send the generated report by email")
    parser.add_argument("--config", default="config/allocation.yaml", help="Allocation policy YAML path")
    parser.add_argument("--state", default="data/allocation_state.json", help="Allocation financial-state JSON path")
    args = parser.parse_args(argv)
    as_of = args.as_of or date.today()
    try:
        if args.command == "allocate":
            return _run_allocation(args.config, args.state, as_of, email=args.email)
        transactions = sync_transactions()
        if args.command == "sync":
            print(f"Synchronized {len(transactions)} transactions.")
            return 0
        if args.command == "weekly":
            return _run_weekly(transactions, as_of)
        if args.command == "monthly":
            return _run_monthly(transactions, as_of, email=args.email)

        # Daily mode is intended for cron or another once-a-day scheduler.
        status = 0
        if as_of.weekday() == WEEKDAYS[args.weekly_day]:
            status = _run_weekly(transactions, as_of)
        else:
            logging.info("Weekly report skipped: today is not %s.", args.weekly_day)

        last_day = monthrange(as_of.year, as_of.month)[1]
        if as_of.day == last_day:
            monthly_status = _run_monthly(transactions, as_of, email=args.email)
            status = status or monthly_status
        else:
            logging.info("Monthly report skipped: today is not the last day of the month.")
        return status
    except Exception as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
