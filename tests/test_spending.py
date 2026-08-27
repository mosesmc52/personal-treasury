from tests.fixtures.transactions import transactions
from personal_treasury.spending import get_spending_summary, is_income, is_spending


def test_classification_and_aggregates():
    ts = transactions(); summary = get_spending_summary(ts, "2026-08-01", "2026-08-31")
    assert summary["total_spending"] == 145
    assert summary["total_income"] == 2000
    assert summary["spending_by_category"]["Food & Drink"] == 80
    assert summary["spending_by_merchant"]["Amazon"] == 10
    assert summary["cash_flow_by_account"]["Unknown account"]["inflows"] == 2010
    assert summary["cash_flow_by_account"]["Unknown account"]["outflows"] == 2655
    assert summary["cash_flow_by_account"]["Unknown account"]["net_cash_flow"] == -645


def test_accounts_are_reported_separately_by_name():
    ts = [
        {"account_id": "checking-id", "item_key": "nasafcu", "account_name": "Checking", "date": "2026-08-12", "amount": 100, "pending": False},
        {"account_id": "savings-id", "item_key": "ally", "account_name": "Savings", "date": "2026-08-12", "amount": -250, "pending": False},
    ]
    summary = get_spending_summary(ts, "2026-08-01", "2026-08-31")
    assert set(summary["cash_flow_by_account"]) == {"nasafcu", "ally"}
    assert summary["largest_expenses"][0]["amount"] == 50
    assert not is_spending(ts[4]) and not is_spending(ts[5]) and not is_spending(ts[-1])
    assert is_income(ts[4]) is False and is_income(ts[3])
