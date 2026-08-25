from tests.fixtures.transactions import transactions
from personal_treasury.spending import get_spending_summary, is_income, is_spending


def test_classification_and_aggregates():
    ts = transactions(); summary = get_spending_summary(ts, "2026-08-01", "2026-08-31")
    assert summary["total_spending"] == 145
    assert summary["total_income"] == 2000
    assert summary["spending_by_category"]["Food & Drink"] == 80
    assert summary["spending_by_merchant"]["Amazon"] == 10
    assert summary["largest_expenses"][0]["amount"] == 50
    assert not is_spending(ts[4]) and not is_spending(ts[5]) and not is_spending(ts[-1])
    assert is_income(ts[4]) is False and is_income(ts[3])

