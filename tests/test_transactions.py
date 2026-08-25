from personal_treasury.transactions import normalize_transaction


def test_normalizes_plaid_category():
    value = normalize_transaction({"transaction_id":"x", "amount":1, "date":"2026-01-01", "personal_finance_category":{"primary":"FOOD_AND_DRINK", "detailed":"FOOD_AND_DRINK_GROCERIES"}})
    assert value["category_primary"] == "FOOD_AND_DRINK" and value["category_detailed"] == "FOOD_AND_DRINK_GROCERIES"

