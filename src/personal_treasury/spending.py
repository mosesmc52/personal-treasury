from collections import defaultdict
from datetime import date, timedelta


def is_pending(t): return bool(t.get("pending", False))
def _text(t): return f"{t.get('name','')} {t.get('merchant_name','')}".lower()
def is_internal_transfer(t): return any(x in _text(t) for x in ("transfer", "zelle", "venmo")) and not is_refund(t)
def is_credit_card_payment(t): return "credit card" in _text(t) or "card payment" in _text(t) or "autopay" in _text(t)
def is_income(t):
    return t.get("amount", 0) < 0 and not is_internal_transfer(t) and not is_refund(t) and any(x in _text(t) for x in ("payroll", "salary", "direct deposit", "interest", "income"))
def is_refund(t): return t.get("amount", 0) < 0 and any(x in _text(t) for x in ("refund", "reversal", "credit"))
def is_spending(t):
    return not is_pending(t) and t.get("amount", 0) > 0 and not is_internal_transfer(t) and not is_credit_card_payment(t)


def merchant(t): return t.get("merchant_name") or t.get("name") or "Unknown"
def category(t):
    raw = t.get("category_primary") or t.get("category_detailed") or "Other"
    return {"FOOD_AND_DRINK": "Food & Drink", "TRANSPORTATION": "Transportation", "GENERAL_MERCHANDISE": "Shopping", "RENT_AND_UTILITIES": "Rent / Housing", "ENTERTAINMENT": "Entertainment", "TRAVEL": "Travel", "MEDICAL": "Medical", "PERSONAL_CARE": "Personal Care"}.get(raw, raw.replace("_", " ").title() if raw else "Other")


def get_spending_summary(transactions, start_date, end_date):
    start_date, end_date = str(start_date), str(end_date)
    spending, income = [], []
    for t in transactions:
        if not (t.get("date") and start_date <= t["date"] <= end_date): continue
        if is_income(t): income.append(t)
        if is_spending(t) or is_refund(t): spending.append(t)
    by_category, by_merchant = defaultdict(float), defaultdict(float)
    for t in spending:
        value = t["amount"]
        by_category[category(t)] += value
        by_merchant[merchant(t)] += value
    total_spending = sum(t["amount"] for t in spending)
    total_income = sum(-t["amount"] for t in income)
    largest = sorted((t for t in spending if t["amount"] > 0), key=lambda t: t["amount"], reverse=True)[:5]
    days = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
    return {"start_date": start_date, "end_date": end_date, "total_spending": total_spending, "total_income": total_income, "net_cash_flow": total_income-total_spending, "transaction_count": sum(1 for t in transactions if t.get("date") and start_date <= t["date"] <= end_date), "spending_transaction_count": len(spending), "spending_by_category": dict(by_category), "spending_by_merchant": dict(by_merchant), "largest_expenses": [{"date": t["date"], "merchant": merchant(t), "category": category(t), "amount": t["amount"]} for t in largest], "average_daily_spending": total_spending / days if days else 0, "savings_rate": (total_income-total_spending)/total_income if total_income > 0 else None}

