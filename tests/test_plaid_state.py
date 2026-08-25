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
    sync_transactions(Api([Response(added=[item("a")], cursor="one")]), "token", state, cache)
    sync_transactions(Api([Response(modified=[item("a", 2)], removed=[{"transaction_id":"missing"}], cursor="two")]), "token", state, cache)
    assert json.loads(state.read_text())["cursor"] == "two" and json.loads(cache.read_text())["a"]["amount"] == 2
    before = cache.read_text()
    class Bad:
        def transactions_sync(self, request): raise RuntimeError("network")
    with pytest.raises(RuntimeError): sync_transactions(Bad(), "token", state, cache)
    assert cache.read_text() == before and json.loads(state.read_text())["cursor"] == "two"

