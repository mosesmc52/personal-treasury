import logging
from datetime import date

from .plaid_client import create_plaid_client
from .plaid_state import atomic_write_json, load_cache, load_state

logger = logging.getLogger(__name__)


def _value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def normalize_transaction(transaction):
    pfc = _value(transaction, "personal_finance_category") or {}
    return {
        "transaction_id": _value(transaction, "transaction_id"),
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


def sync_transactions(api=None, access_token=None, state_path="data/plaid_state.json", cache_path="data/transactions.json"):
    logger.info("Starting Plaid sync")
    if api is None:
        api, access_token = create_plaid_client()
    state, original_cache = load_state(state_path), load_cache(cache_path)
    cache = dict(original_cache)
    cursor = state.get("cursor")
    added = modified = removed = 0
    try:
        while True:
            response = _sync_response(api, access_token, cursor)
            for item in _value(response, "added", []) or []:
                cache[_value(item, "transaction_id")] = normalize_transaction(item); added += 1
            for item in _value(response, "modified", []) or []:
                cache[_value(item, "transaction_id")] = normalize_transaction(item); modified += 1
            for item in _value(response, "removed", []) or []:
                transaction_id = _value(item, "transaction_id")
                cache.pop(transaction_id, None); removed += 1
            cursor = _value(response, "next_cursor", cursor)
            if not _value(response, "has_more", False):
                break
        atomic_write_json(cache_path, cache)
        atomic_write_json(state_path, {"cursor": cursor or ""})
    except Exception as exc:
        raise RuntimeError(f"Plaid transaction sync failed: {exc}") from exc
    logger.info("Added %d transactions, modified %d, removed %d; saved %d total", added, modified, removed, len(cache))
    return list(cache.values())


def load_transactions(path="data/transactions.json"):
    return list(load_cache(path).values())

