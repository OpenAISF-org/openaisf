import pytest

from openaisf.applicability import (
    AUTONOMY_LADDER,
    SystemContext,
    applies_to,
)
from openaisf.errors import ValidationError


def ctx(**overrides) -> SystemContext:
    base = dict(
        system_id="urn:openaisf:system:test",
        roles=["deployer"],
        system_class=["llm"],
        autonomy="none",
        data_class=["internal"],
        eu_risk=["minimal"],
    )
    base.update(overrides)
    return SystemContext(**base)


def control(**overrides) -> dict:
    base = {
        "id": "D07-C01",
        "roles": ["deployer"],
        "tiers": {"T2": "required", "T3": "required"},
    }
    base.update(overrides)
    return base


# --- scope predicates -------------------------------------------------------


def test_control_without_applies_when_applies_to_everything():
    assert applies_to(control(), ctx(), "T2") is True


def test_system_class_must_intersect():
    agentic_only = control(applies_when={"system_class": ["agentic"]})
    assert applies_to(agentic_only, ctx(system_class=["llm"]), "T2") is False
    assert applies_to(agentic_only, ctx(system_class=["llm", "agentic"]), "T2") is True


def test_autonomy_ladder_is_ordered():
    assert AUTONOMY_LADDER.index("none") < AUTONOMY_LADDER.index("tool_use")
    assert AUTONOMY_LADDER.index("planning") < AUTONOMY_LADDER.index("multi_agent")


def test_autonomy_threshold_expression():
    tool_using = control(applies_when={"autonomy": [">= tool_use"]})
    assert applies_to(tool_using, ctx(autonomy="none"), "T2") is False
    assert applies_to(tool_using, ctx(autonomy="tool_use"), "T2") is True
    assert applies_to(tool_using, ctx(autonomy="multi_agent"), "T2") is True


def test_autonomy_strict_and_equality_expressions():
    strict = control(applies_when={"autonomy": ["> planning"]})
    assert applies_to(strict, ctx(autonomy="planning"), "T2") is False
    assert applies_to(strict, ctx(autonomy="self_directed"), "T2") is True

    exact = control(applies_when={"autonomy": ["== multi_agent"]})
    assert applies_to(exact, ctx(autonomy="self_directed"), "T2") is False
    assert applies_to(exact, ctx(autonomy="multi_agent"), "T2") is True


def test_keys_are_anded_and_values_are_ored():
    both = control(
        applies_when={
            "system_class": ["agentic", "llm"],
            "data_class": ["personal", "health"],
        }
    )
    # matches system_class but not data_class
    assert applies_to(both, ctx(system_class=["llm"], data_class=["internal"]), "T2") is False
    # matches both
    assert applies_to(both, ctx(system_class=["llm"], data_class=["health"]), "T2") is True


def test_unknown_autonomy_value_is_an_error():
    bad = control(applies_when={"autonomy": [">= teleportation"]})
    with pytest.raises(ValidationError, match="unknown autonomy level"):
        applies_to(bad, ctx(), "T2")


# --- role and tier gates ----------------------------------------------------


def test_role_must_intersect():
    provider_only = control(roles=["provider"])
    assert applies_to(provider_only, ctx(roles=["deployer"]), "T2") is False
    assert applies_to(provider_only, ctx(roles=["deployer", "provider"]), "T2") is True


def test_tier_not_listed_means_out_of_scope():
    t3_plus = control(tiers={"T3": "required", "T4": "required"})
    assert applies_to(t3_plus, ctx(), "T2") is False
    assert applies_to(t3_plus, ctx(), "T3") is True


def test_explicit_not_applicable_at_tier_is_out_of_scope():
    c = control(tiers={"T2": "not_applicable", "T3": "required"})
    assert applies_to(c, ctx(), "T2") is False


def test_recommended_still_counts_as_in_scope():
    c = control(tiers={"T1": "recommended"})
    assert applies_to(c, ctx(), "T1") is True
