"""The no-bureaucracy acceptance criterion, made executable.

Architecture section 20 states it as a measurable release condition rather than
a hope: if a typical system resolves to more than about forty applicable
controls at T2, the applicability model has failed and needs tightening before
release.

An exhaustive catalog is only tolerable if the Statement of Applicability is
short. These tests are what stop the catalog growing without the scoping model
keeping pace.
"""

from pathlib import Path

from openaisf.applicability import SystemContext
from openaisf.loader import load_catalog
from openaisf.soa import resolve_soa

CATALOG = Path(__file__).resolve().parent.parent / "spec" / "catalog"

TYPICAL_T2_CEILING = 40
AGENTIC_T2_CEILING = 55


def _soa(tier: str, **ctx):
    base = dict(
        system_id="urn:openaisf:system:test",
        roles=["deployer"],
        system_class=["llm"],
        autonomy="none",
        data_class=["internal"],
        eu_risk=["minimal"],
    )
    base.update(ctx)
    return resolve_soa(load_catalog(CATALOG), SystemContext(**base), tier)


def test_typical_deployment_stays_under_the_stated_ceiling():
    """An internal, non-agentic, minimal-risk LLM application at T2."""
    soa = _soa("T2")
    assert soa.in_scope <= TYPICAL_T2_CEILING, (
        f"a typical T2 system resolves to {soa.in_scope} controls, above the "
        f"stated ceiling of {TYPICAL_T2_CEILING}. Tighten applies_when "
        f"predicates rather than raising this number."
    )


def test_agentic_deployment_with_personal_data_has_a_ceiling_too():
    """Higher risk legitimately means more controls, but not without bound."""
    soa = _soa(
        "T2",
        system_class=["llm", "agentic"],
        autonomy="tool_use",
        data_class=["internal", "personal"],
        eu_risk=["limited"],
    )
    assert soa.in_scope <= AGENTIC_T2_CEILING, (
        f"an agentic T2 system resolves to {soa.in_scope} controls, above "
        f"{AGENTIC_T2_CEILING}."
    )


def test_t1_is_genuinely_minutes_of_work():
    """T1 is the funnel. If it is not tiny, nobody ever reaches T2."""
    soa = _soa("T1")
    assert soa.in_scope <= 12, (
        f"T1 resolves to {soa.in_scope} controls. T1 must be achievable in "
        f"minutes or the free tier stops being a funnel."
    )


def test_scope_grows_monotonically_with_tier():
    sizes = [_soa(t).in_scope for t in ("T1", "T2", "T3", "T4")]
    assert sizes == sorted(sizes), f"tier scope is not monotonic: {sizes}"


def test_autonomy_and_data_class_actually_reduce_scope():
    """The applicability model earns its keep only if it removes controls."""
    minimal = _soa("T3")
    maximal = _soa(
        "T3",
        system_class=["llm", "agentic"],
        autonomy="multi_agent",
        data_class=["internal", "personal", "special_category"],
        eu_risk=["high"],
    )
    assert minimal.in_scope < maximal.in_scope
    assert minimal.counts["not_applicable"] > maximal.counts["not_applicable"]
