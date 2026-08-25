from decimal import Decimal

import pytest

from personal_treasury.allocation_config import load_allocation_config


VALID = """
version: 1
settings:
  minimum_allocation: 10
  round_to: 1
accounts:
  checking:
    type: minimum
    target: 4000
    priority: 10
  emergency:
    type: target
    target: 20000
    priority: 20
  alpaca:
    type: percentage
    percentage: 0.7
    priority: 30
  savings:
    type: percentage
    percentage: 0.3
    priority: 30
"""


def config(tmp_path, text=VALID):
    path = tmp_path / "allocation.yaml"
    path.write_text(text)
    return path


def test_valid_yaml_loads_as_decimal_models(tmp_path):
    loaded = load_allocation_config(config(tmp_path))
    assert loaded.by_key["alpaca"].percentage == Decimal("0.7")
    assert loaded.settings.round_to == 1


@pytest.mark.parametrize("fragment", [
    "type: unknown",
    "type: minimum",
    "type: target",
    "type: percentage",
    "type: percentage\n    percentage: 1.1",
    "type: percentage\n    percentage: -0.1",
    "type: minimum\n    target: -1",
])
def test_invalid_rules_fail(tmp_path, fragment):
    text = "version: 1\naccounts:\n  bad:\n    " + fragment.replace("\n", "\n    ") + "\n"
    with pytest.raises(ValueError): load_allocation_config(config(tmp_path, text))


def test_percentage_group_must_total_one(tmp_path):
    text = VALID.replace("percentage: 0.3", "percentage: 0.2")
    with pytest.raises(ValueError, match="priority 30"):
        load_allocation_config(config(tmp_path, text))


def test_duplicate_external_ids_fail(tmp_path):
    text = VALID.replace("type: minimum", "type: minimum\n    plaid_account_id: same", 1).replace("type: target", "type: target\n    external_account_id: same", 1)
    with pytest.raises(ValueError, match="duplicate"):
        load_allocation_config(config(tmp_path, text))
