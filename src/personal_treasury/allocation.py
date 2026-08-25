"""Pure allocation recommendation engine. This module never moves money."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .allocation_config import AccountAllocationRule, AllocationConfig


def _decimal(value, field):
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field} must be a number") from exc


@dataclass(frozen=True)
class AllocationRecommendation:
    account_key: str
    account_name: str
    rule_type: str
    priority: int
    current_balance: Decimal
    allocation: Decimal
    projected_balance: Decimal
    reason: str
    percentage: Decimal | None = None
    target: Decimal | None = None


@dataclass(frozen=True)
class AllocationResult:
    available_cash: Decimal
    allocated_amount: Decimal
    unallocated_amount: Decimal
    recommendations: tuple[AllocationRecommendation, ...]
    warnings: tuple[str, ...] = ()


def _round(value, quantum):
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def _zero_recommendation(rule, balance, reason="No allocation recommended"):
    return AllocationRecommendation(rule.key, rule.name, rule.type, rule.priority, balance, Decimal("0"), balance, reason, rule.percentage, rule.target)


def _bounded_round(value, upper_bound, quantum):
    """Round without recommending more than either the cash or deficit."""
    rounded = _round(value, quantum)
    if rounded <= upper_bound:
        return rounded
    return (upper_bound // quantum) * quantum


def calculate_allocation(config: AllocationConfig, balances, available_cash):
    if not isinstance(config, AllocationConfig):
        raise TypeError("config must be an AllocationConfig")
    available = _decimal(available_cash, "available_cash")
    if available < 0:
        raise ValueError("available_cash cannot be negative")
    balances = {key: _decimal(value, f"balances.{key}") for key, value in balances.items()}
    if any(value < 0 for value in balances.values()):
        raise ValueError("account balances cannot be negative")
    settings = config.settings
    allocatable = min(available, settings.maximum_total_allocation) if settings.maximum_total_allocation is not None else available
    remaining = allocatable
    recommendations = {}
    warnings = []

    for rule in sorted(config.accounts, key=lambda item: (item.priority, item.key)):
        balance = balances.get(rule.key, Decimal("0"))
        if rule.type == "ignore":
            recommendations[rule.key] = _zero_recommendation(rule, balance, "Ignored by allocation policy")

    priorities = sorted({rule.priority for rule in config.accounts})
    for priority in priorities:
        fixed = [rule for rule in config.accounts if rule.priority == priority and rule.type in {"minimum", "target"}]
        for rule in sorted(fixed, key=lambda item: item.key):
            balance = balances.get(rule.key, Decimal("0"))
            deficit = max(rule.target - balance, Decimal("0"))
            raw = min(deficit, remaining)
            allocation = _bounded_round(raw, min(deficit, remaining), settings.round_to)
            if allocation and allocation < settings.minimum_allocation:
                allocation = Decimal("0")
                reason = "Required allocation is below minimum_allocation"
            elif allocation:
                reason = f"Restore {rule.type} balance to {rule.target}"
            else:
                reason = "Balance already satisfies target" if deficit == 0 else "No cash remains"
            recommendations[rule.key] = AllocationRecommendation(rule.key, rule.name, rule.type, rule.priority, balance, allocation, balance + allocation, reason, rule.percentage, rule.target)
            remaining -= allocation

        percentage_rules = sorted((rule for rule in config.accounts if rule.priority == priority and rule.type == "percentage"), key=lambda item: item.key)
        if not percentage_rules or remaining <= 0:
            for rule in percentage_rules:
                balance = balances.get(rule.key, Decimal("0"))
                recommendations[rule.key] = _zero_recommendation(rule, balance, "No cash remains")
            continue
        pool = remaining
        proposed = {}
        blocked = False
        for rule in percentage_rules:
            balance = balances.get(rule.key, Decimal("0"))
            raw = pool * rule.percentage
            allocation = _round(raw, settings.round_to)
            if allocation > pool:
                allocation = (pool // settings.round_to) * settings.round_to
            if rule.maximum_allocation_per_run is not None and allocation > rule.maximum_allocation_per_run:
                allocation = rule.maximum_allocation_per_run
                blocked = True
                reason = f"Capped by maximum_allocation_per_run ({rule.maximum_allocation_per_run})"
            elif allocation and allocation < settings.minimum_allocation:
                allocation = Decimal("0")
                blocked = True
                reason = "Below minimum_allocation"
            else:
                reason = f"{rule.percentage * 100}% of surplus at priority {priority}"
            proposed[rule.key] = (rule, balance, allocation, reason)
        if not blocked:
            residual = pool - sum(item[2] for item in proposed.values())
            if residual:
                largest = max(percentage_rules, key=lambda item: (item.percentage, item.key))
                rule, balance, allocation, reason = proposed[largest.key]
                adjusted = allocation + residual
                if adjusted >= 0:
                    proposed[largest.key] = (rule, balance, adjusted, reason)
        for rule in percentage_rules:
            rule, balance, allocation, reason = proposed[rule.key]
            recommendations[rule.key] = AllocationRecommendation(rule.key, rule.name, rule.type, rule.priority, balance, allocation, balance + allocation, reason, rule.percentage, rule.target)
            remaining -= allocation
        if blocked:
            warnings.append(f"Priority {priority} percentage allocations were not redistributed after a cap or minimum threshold")

    for rule in config.accounts:
        if rule.key not in recommendations:
            recommendations[rule.key] = _zero_recommendation(rule, balances.get(rule.key, Decimal("0")), "No allocation recommended")
    allocated = sum((item.allocation for item in recommendations.values()), Decimal("0"))
    unallocated = available - allocated
    if settings.maximum_total_allocation is not None and available > settings.maximum_total_allocation:
        warnings.append(f"Allocation capped at maximum_total_allocation ({settings.maximum_total_allocation})")
    return AllocationResult(available, allocated, unallocated, tuple(recommendations[rule.key] for rule in config.accounts), tuple(warnings))
