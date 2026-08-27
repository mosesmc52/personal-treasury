"""Typed loading and validation for human-authored allocation policy."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml


RULE_TYPES = {"minimum", "target", "percentage", "ignore"}


def _decimal(value, field):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be a number") from exc


@dataclass(frozen=True)
class AllocationSettings:
    minimum_allocation: Decimal = Decimal("0")
    round_to: Decimal = Decimal("0.01")
    maximum_total_allocation: Decimal | None = None


@dataclass(frozen=True)
class AccountAllocationRule:
    key: str
    name: str
    type: str
    priority: int = 0
    target: Decimal | None = None
    percentage: Decimal | None = None
    plaid_account_id: str | None = None
    maximum_allocation_per_run: Decimal | None = None
    monthly_amount: Decimal | None = None


@dataclass(frozen=True)
class AllocationConfig:
    version: int
    settings: AllocationSettings
    accounts: tuple[AccountAllocationRule, ...]

    @property
    def by_key(self):
        return {rule.key: rule for rule in self.accounts}


def _validate_and_build_rule(key, values):
    if not isinstance(values, dict):
        raise ValueError(f"accounts.{key} must be a mapping")
    rule_type = values.get("type")
    if rule_type not in RULE_TYPES:
        raise ValueError(f"accounts.{key}.type must be one of: {', '.join(sorted(RULE_TYPES))}")
    name = str(values.get("name") or key.replace("_", " ").title())
    try:
        priority = int(values.get("priority", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"accounts.{key}.priority must be an integer") from exc
    target = _decimal(values["target"], f"accounts.{key}.target") if "target" in values else None
    percentage = _decimal(values["percentage"], f"accounts.{key}.percentage") if "percentage" in values else None
    maximum = _decimal(values["maximum_allocation_per_run"], f"accounts.{key}.maximum_allocation_per_run") if "maximum_allocation_per_run" in values else None
    monthly_amount = _decimal(values["monthly_amount"], f"accounts.{key}.monthly_amount") if "monthly_amount" in values else None
    if rule_type in {"minimum", "target"} and target is None:
        raise ValueError(f"accounts.{key}: {rule_type} rule requires target")
    if target is not None and target < 0:
        raise ValueError(f"accounts.{key}.target cannot be negative")
    if rule_type == "percentage" and percentage is None:
        raise ValueError(f"accounts.{key}: percentage rule requires percentage")
    if percentage is not None and not Decimal("0") <= percentage <= Decimal("1"):
        raise ValueError(f"accounts.{key}.percentage must be between 0 and 1")
    if maximum is not None and maximum < 0:
        raise ValueError(f"accounts.{key}.maximum_allocation_per_run cannot be negative")
    if monthly_amount is not None and monthly_amount < 0:
        raise ValueError(f"accounts.{key}.monthly_amount cannot be negative")
    external_id = values.get("plaid_account_id", values.get("external_account_id"))
    return AccountAllocationRule(key, name, rule_type, priority, target, percentage, external_id, maximum, monthly_amount)


def load_allocation_config(path="config/allocation.yaml"):
    path = Path(path)
    if not path.exists():
        raise ValueError(f"Allocation config not found: {path}")
    try:
        document = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid allocation YAML: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Allocation config must be a mapping")
    try:
        version = int(document.get("version", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("version must be an integer") from exc
    raw_settings = document.get("settings", {})
    if not isinstance(raw_settings, dict):
        raise ValueError("settings must be a mapping")
    minimum = _decimal(raw_settings.get("minimum_allocation", 0), "settings.minimum_allocation")
    round_to = _decimal(raw_settings.get("round_to", "0.01"), "settings.round_to")
    maximum_total = (_decimal(raw_settings["maximum_total_allocation"], "settings.maximum_total_allocation")
                     if "maximum_total_allocation" in raw_settings else None)
    if minimum < 0:
        raise ValueError("settings.minimum_allocation cannot be negative")
    if round_to <= 0:
        raise ValueError("settings.round_to must be greater than zero")
    if maximum_total is not None and maximum_total < 0:
        raise ValueError("settings.maximum_total_allocation cannot be negative")
    settings = AllocationSettings(minimum, round_to, maximum_total)
    raw_accounts = document.get("accounts")
    if not isinstance(raw_accounts, dict) or not raw_accounts:
        raise ValueError("accounts must be a non-empty mapping")
    rules = tuple(_validate_and_build_rule(key, values) for key, values in raw_accounts.items())
    identifiers = [rule.plaid_account_id for rule in rules if rule.plaid_account_id]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate plaid_account_id values are not allowed")
    for priority in sorted({rule.priority for rule in rules}):
        group = [rule for rule in rules if rule.priority == priority and rule.type == "percentage"]
        if group:
            total = sum((rule.percentage for rule in group), Decimal("0"))
            if abs(total - Decimal("1")) > Decimal("0.000001"):
                raise ValueError(f"percentage rules at priority {priority} must total 1.0; got {total}")
    return AllocationConfig(version, settings, rules)
