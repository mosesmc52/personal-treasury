import json
from pathlib import Path
import pytest
from personal_treasury.transactions import sync_transactions


class Response:
    def __init__(self, added=(), modified=(), removed=(), cursor="next", more=False):
        self.added, self.modified, self.removed, self.next_cursor, self.has_more = added, modified, removed, cursor, more


class Api:
    def __init__(self, responses): self.responses = iter(responses)
    def transactions_sync(self, request): return next(self.responses)


def item(i, amount=1): return {"transaction_id": i, "date": "2026-08-01", "name": i, "amount": amount, "pending": False}


def test_changes_and_atomic_failure(tmp_path):
    state, cache = tmp_path / "state.json", tmp_path / "cache.json"
    sync_transactions(Api([Response(added=[item("a")], cursor="one")]), {"bank_one": "token"}, state, cache)
    sync_transactions(Api([Response(modified=[item("a", 2)], removed=[{"transaction_id":"missing"}], cursor="two")]), {"bank_one": "token"}, state, cache)
    assert json.loads(state.read_text())["cursors"]["bank_one"] == "two" and json.loads(cache.read_text())["a"]["amount"] == 2
    before = cache.read_text()
    class Bad:
        def transactions_sync(self, request): raise RuntimeError("network")
    with pytest.raises(RuntimeError): sync_transactions(Bad(), {"bank_one": "token"}, state, cache)
    assert cache.read_text() == before and json.loads(state.read_text())["cursors"]["bank_one"] == "two"


def test_multiple_items_have_independent_cursors_and_are_merged(tmp_path):
    state, cache = tmp_path / "state.json", tmp_path / "cache.json"
    api = Api([Response(added=[item("chase-txn")], cursor="chase-cursor"), Response(added=[item("capital-one-txn")], cursor="capital-one-cursor")])
    transactions = sync_transactions(api, {"chase": "token-one", "capital_one": "token-two"}, state, cache)
    saved_state = json.loads(state.read_text())
    saved_cache = json.loads(cache.read_text())
    assert saved_state["cursors"] == {"chase": "chase-cursor", "capital_one": "capital-one-cursor"}
    assert {transaction["item_key"] for transaction in transactions} == {"chase", "capital_one"}
    assert set(saved_cache) == {"chase-txn", "capital-one-txn"}
