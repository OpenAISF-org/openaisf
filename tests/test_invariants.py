import pytest

from openaisf.errors import ValidationError
from openaisf.loader import check_invariants


def _control(**overrides):
    base = {
        "id": "D07-C01",
        "title": "A sufficiently long control title",
        "domain": "D07",
        "level": "core",
        "normative": "A normative statement of adequate length for the schema.",
        "rfc2119": "MUST",
        "roles": ["deployer"],
        "lifecycle": ["operate"],
        "tiers": {"T3": "required"},
        "verification": {"method": "attested"},
        "crosswalk": {},
    }
    base.update(overrides)
    return base


def test_emitted_control_must_declare_evidence():
    control = _control(verification={"method": "emitted", "planes": ["data"]})
    with pytest.raises(ValidationError, match="declare at least one evidence"):
        check_invariants([control])


def test_emitted_control_evidence_planes_must_cover_declared_planes():
    control = _control(
        verification={"method": "emitted", "planes": ["control", "data"]},
        evidence=[{"schema": "openaisf.evidence.x.v1", "plane": "control"}],
    )
    with pytest.raises(ValidationError, match="no evidence source for plane 'data'"):
        check_invariants([control])


def test_required_tier_must_have_freshness_when_emitted():
    control = _control(
        verification={"method": "emitted", "planes": ["data"], "freshness": {}},
        evidence=[{"schema": "openaisf.evidence.x.v1", "plane": "data"}],
    )
    with pytest.raises(ValidationError, match="freshness window for tier T3"):
        check_invariants([control])


def test_valid_control_passes():
    control = _control(
        verification={
            "method": "emitted",
            "planes": ["data"],
            "freshness": {"T3": "P7D"},
        },
        evidence=[{"schema": "openaisf.evidence.x.v1", "plane": "data"}],
    )
    check_invariants([control])
