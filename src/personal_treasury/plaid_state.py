import json
import os
import tempfile
from pathlib import Path


def load_state(path="data/plaid_state.json"):
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def load_cache(path="data/transactions.json"):
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def atomic_write_json(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{p.name}.", dir=p.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(value, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(name, p)
    except Exception:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


def save_state(state, path="data/plaid_state.json"):
    atomic_write_json(path, state)


def save_cache(cache, path="data/transactions.json"):
    atomic_write_json(path, cache)
