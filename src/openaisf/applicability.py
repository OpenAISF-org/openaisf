"""Decide whether a control applies to a system.

The reader never decides relevance. A control declares its own scope predicate
and this module resolves it against the facts of the system. That is what keeps
a several-hundred-control catalog from becoming the bureaucracy it exists to
replace: an exhaustive catalog can still produce a short list.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from openaisf.errors import ValidationError

#: Autonomy is a ladder, not a set. Each rung inherits the obligations below it.
AUTONOMY_LADDER: tuple[str, ...] = (
    "none",
    "tool_use",
    "planning",
    "self_directed",
    "multi_agent",
)

#: Scope keys that are resolved by set intersection.
SET_KEYS = ("system_class", "data_class", "eu_risk")

IN_SCOPE_OBLIGATIONS = frozenset({"required", "recommended"})

_EXPR = re.compile(r"^\s*(>=|>|==)?\s*([a-z_]+)\s*$")


@dataclass(frozen=True)
class SystemContext:
    """The scoping facts about one system under evaluation."""

    system_id: str
    roles: tuple[str, ...] = ()
    system_class: tuple[str, ...] = ()
    autonomy: str = "none"
    data_class: tuple[str, ...] = ()
    eu_risk: tuple[str, ...] = ()
    labels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Accept lists from YAML without forcing callers to convert.
        for name in ("roles", "system_class", "data_class", "eu_risk"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        if self.autonomy not in AUTONOMY_LADDER:
            raise ValidationError(
                f"{self.system_id}: unknown autonomy level '{self.autonomy}'; "
                f"expected one of {', '.join(AUTONOMY_LADDER)}"
            )


def _autonomy_matches(expression: str, actual: str) -> bool:
    match = _EXPR.match(expression)
    if not match:
        raise ValidationError(f"malformed autonomy expression: {expression!r}")
    operator, level = match.group(1) or "==", match.group(2)

    if level not in AUTONOMY_LADDER:
        raise ValidationError(
            f"unknown autonomy level '{level}' in expression {expression!r}"
        )

    actual_rank = AUTONOMY_LADDER.index(actual)
    threshold = AUTONOMY_LADDER.index(level)

    if operator == ">=":
        return actual_rank >= threshold
    if operator == ">":
        return actual_rank > threshold
    return actual_rank == threshold


def in_scope_at_tier(control: dict, tier: str) -> bool:
    """A control is in scope at a tier only if that tier names an obligation."""
    return control.get("tiers", {}).get(tier) in IN_SCOPE_OBLIGATIONS


def obligation_at_tier(control: dict, tier: str) -> str | None:
    obligation = control.get("tiers", {}).get(tier)
    return obligation if obligation in IN_SCOPE_OBLIGATIONS else None


def applies_to(control: dict, context: SystemContext, tier: str) -> bool:
    """Resolve a control's scope predicate against one system.

    Three gates, all of which must pass:

      1. Tier      — the control names an obligation at this tier.
      2. Role      — the control is owed by at least one role the system holds.
      3. Predicate — every declared applies_when key matches, where a key
                     matches if any of its values matches (AND across keys,
                     OR within a key).

    A control with no applies_when block passes gate 3 unconditionally.
    """
    if not in_scope_at_tier(control, tier):
        return False

    control_roles = set(control.get("roles", ()))
    if control_roles and not control_roles & set(context.roles):
        return False

    predicate = control.get("applies_when") or {}

    for key in SET_KEYS:
        wanted = predicate.get(key)
        if not wanted:
            continue
        if not set(wanted) & set(getattr(context, key)):
            return False

    autonomy_expressions = predicate.get("autonomy")
    if autonomy_expressions:
        if not any(
            _autonomy_matches(expression, context.autonomy)
            for expression in autonomy_expressions
        ):
            return False

    return True
