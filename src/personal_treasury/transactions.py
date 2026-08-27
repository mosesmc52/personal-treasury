import logging
import os
from decimal import Decimal, InvalidOperation
from datetime import date

from .plaid_client import create_plaid_client
from .plaid_state import atomic_write_json, load_cache, load_state

logger = logging.getLogger(__name__)


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def normalize_transaction(transaction, item_key=None, account_name=None):
    pfc = _value(transaction, "personal_finance_category") or {}
    return {
        "transaction_id": _value(transaction, "transaction_id"),
        "item_key": item_key,
        "account_name": account_name,
        "account_id": _value(transaction, "account_id"),
        "date": str(_value(transaction, "date")) if _value(transaction, "date") else None,
        "authorized_date": str(_value(transaction, "authorized_date")) if _value(transaction, "authorized_date") else None,
        "name": _value(transaction, "name", ""),
        "merchant_name": _value(transaction, "merchant_name"),
        "amount": float(_value(transaction, "amount", 0)),
        "pending": bool(_value(transaction, "pending", False)),
        "payment_channel": _value(transaction, "payment_channel"),
        "category_primary": _value(transaction, "category_primary") or _value(pfc, "primary"),
        "category_detailed": _value(transaction, "category_detailed") or _value(pfc, "detailed"),
        "iso_currency_code": _value(transaction, "iso_currency_code"),
    }


def _sync_response(api, access_token, cursor):
    from plaid.model.transactions_sync_request import TransactionsSyncRequest
    return api.transactions_sync(TransactionsSyncRequest(access_token=access_token, cursor=cursor) if cursor else TransactionsSyncRequest(access_token=access_token))


def _account_names(api, access_token):
    """Return account display names without exposing account identifiers in reports."""
    try:
        from plaid.model.accounts_get_request import AccountsGetRequest
        response = api.accounts_get(AccountsGetRequest(access_token=access_token))
        return {_value(account, "account_id"): _value(account, "name") or _value(account, "official_name") for account in (_value(response, "accounts", []) or [])}
    except Exception:
        # Account names improve presentation but should not prevent transaction sync.
        logger.warning("Could not retrieve account names for one Plaid Item")
        return {}


def sync_transactions(api=None, access_tokens=None, state_path="data/plaid_state.json", cache_path="data/transactions.json"):
    logger.info("Starting Plaid sync")
    if api is None:
        api, access_tokens = create_plaid_client()
    if not isinstance(access_tokens, dict) or not access_tokens:
        raise ValueError("At least one Plaid access token is required")
    state, original_cache = load_state(state_path), load_cache(cache_path)
    cache = dict(original_cache)
    cursors = state.get("cursors", {})
    if not isinstance(cursors, dict):
        raise ValueError("Plaid state cursors must be a mapping")
    new_cursors = dict(cursors)
    total_added = total_modified = total_removed = 0
    try:
        for item_key, access_token in access_tokens.items():
            cursor = cursors.get(item_key)
            account_names = _account_names(api, access_token)
            # Backfill names on transactions cached before account-name lookup
            # was added. Keep the Plaid account ID only as internal metadata.
            for cached in cache.values():
                if cached.get("item_key") == item_key:
                    name = account_names.get(cached.get("account_id"))
                    if name:
                        cached["account_name"] = name
            while True:
                response = _sync_response(api, access_token, cursor)
                for item in _value(response, "added", []) or []:
                    cache[_value(item, "transaction_id")] = normalize_transaction(item, item_key, account_names.get(_value(item, "account_id"))); total_added += 1
                for item in _value(response, "modified", []) or []:
                    cache[_value(item, "transaction_id")] = normalize_transaction(item, item_key, account_names.get(_value(item, "account_id"))); total_modified += 1
                for item in _value(response, "removed", []) or []:
                    transaction_id = _value(item, "transaction_id")
                    cache.pop(transaction_id, None); total_removed += 1
                cursor = _value(response, "next_cursor", cursor)
                if not _value(response, "has_more", False):
                    break
            new_cursors[item_key] = cursor or ""
        atomic_write_json(cache_path, cache)
        atomic_write_json(state_path, {"cursors": new_cursors})
    except Exception as exc:
        raise RuntimeError(f"Plaid transaction sync failed: {exc}") from exc
    logger.info("Added %d transactions, modified %d, removed %d; saved %d total across %d Plaid Items", total_added, total_modified, total_removed, len(cache), len(access_tokens))
    return list(cache.values())


def load_transactions(path="data/transactions.json"):
    return list(load_cache(path).values())


def fetch_account_balances(api, access_tokens):
    """Fetch read-only current balances, grouped by the named Plaid Item."""
    balances = {}
    from plaid.model.accounts_get_request import AccountsGetRequest

    for item_key, access_token in access_tokens.items():
        response = api.accounts_get(AccountsGetRequest(access_token=access_token))
        total = 0.0
        for account in _value(response, "accounts", []) or []:
            account_balances = _value(account, "balances", {}) or {}
            current = _value(account_balances, "current", 0) or 0
            total += float(current)
        balances[item_key] = total
    return balances


def update_allocation_state(state_path="data/allocation_state.json", income=0):
    """Refresh Plaid balances while preserving explicit available_cash and other balances."""
    api, access_tokens = create_plaid_client()
    current_state = {}
    try:
        current_state = __import__("json").loads(__import__("pathlib").Path(state_path).read_text())
    except FileNotFoundError:
        pass
    try:
        income_amount = Decimal(str(income))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("income must be a valid number") from exc
    if income_amount < 0:
        raise ValueError("income cannot be negative")
    available_cash = Decimal(str(current_state.get("available_cash", 0))) + income_amount
    state = {
        "available_cash": float(available_cash),
        "balances": dict(current_state.get("balances", {})),
    }
    state["balances"].update(fetch_account_balances(api, access_tokens))
    alpaca_balance = fetch_alpaca_portfolio_value()
    if alpaca_balance is not None:
        state["balances"]["alpaca"] = alpaca_balance
    atomic_write_json(state_path, state)
    logger.info("Updated allocation state with balances for %d Plaid Items", len(access_tokens))
    return state


def fetch_alpaca_portfolio_value():
    """Return Alpaca's current portfolio value using its read-only account API."""
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")
    if not api_key or not secret_key:
        logger.info("Alpaca balance refresh skipped: credentials are not configured")
        return None

    try:
        from alpaca.trading.client import TradingClient

        paper = os.getenv("ALPACA_PAPER", "true").lower() in {"1", "true", "yes"}
        account = TradingClient(api_key, secret_key, paper=paper).get_account()
        portfolio_value = _value(account, "portfolio_value")
        if portfolio_value is None:
            raise ValueError("Alpaca account response did not include portfolio_value")
        value = float(portfolio_value)
        logger.info("Refreshed Alpaca portfolio value")
        return value
    except Exception as exc:
        raise RuntimeError(f"Could not refresh Alpaca portfolio value: {exc}") from exc
