def tx(i, name, amount, day="2026-08-12", category="GENERAL_MERCHANDISE", merchant_name=None, **extra):
    return {"transaction_id": i, "account_id": "acct", "date": day, "name": name, "merchant_name": merchant_name or name, "amount": amount, "pending": False, "category_primary": category, **extra}


def transactions():
    return [
        tx("grocery", "Whole Foods", 50, category="FOOD_AND_DRINK"),
        tx("restaurant", "Restaurant", 30, category="FOOD_AND_DRINK"),
        tx("amazon", "Amazon", 20), tx("uber", "Uber", 15, category="TRANSPORTATION"),
        tx("payroll", "Payroll direct deposit", -2000),
        tx("transfer", "Checking transfer to savings", 500),
        tx("card-payment", "Credit card payment", 2000),
        tx("card-purchase", "Target", 40),
        tx("refund", "Amazon refund", -10),
        tx("pending", "Pending store", 100, pending=True),
    ]
