import pytest

from openaisf.coverage import compute_coverage
from openaisf.errors import ValidationError

INVENTORIES = {
    "demo": {
        "regime": "demo",
        "name": "Demo Regime",
        "version": "1.0",
        "declared_total": 3,
        "requirements": [
            {"ref": "R1", "text_summary": "First demo requirement"},
            {"ref": "R2", "text_summary": "Second demo requirement"},
            {"ref": "R3", "text_summary": "Third demo requirement"},
        ],
    }
}


def _control(control_id, refs):
    return {
        "id": control_id,
        "domain": control_id[:3],
        "crosswalk": {"demo": refs} if refs else {},
    }


def test_covered_excluded_and_uncovered_are_partitioned():
    controls = [_control("D01-C01", ["R1"])]
    exclusions = {"demo": {"R2": "Prohibited practice, screened not implemented"}}

    regimes, statuses = compute_coverage(controls, INVENTORIES, exclusions)

    assert len(regimes) == 1
    demo = regimes[0]
    assert demo.total == 3
    assert demo.covered == 1
    assert demo.excluded == 1
    assert demo.uncovered == ("R3",)

    by_ref = {s.ref: s for s in statuses}
    assert by_ref["R1"].status == "covered"
    assert by_ref["R1"].controls == ("D01-C01",)
    assert by_ref["R2"].status == "excluded"
    assert by_ref["R2"].reason.startswith("Prohibited")
    assert by_ref["R3"].status == "uncovered"


def test_multiple_controls_covering_one_requirement_are_all_listed():
    controls = [_control("D01-C01", ["R1"]), _control("D05-C02", ["R1"])]
    _, statuses = compute_coverage(controls, INVENTORIES, {})
    by_ref = {s.ref: s for s in statuses}
    assert by_ref["R1"].controls == ("D01-C01", "D05-C02")


def test_crosswalk_reference_not_in_inventory_is_an_error():
    controls = [_control("D01-C01", ["R99"])]
    with pytest.raises(ValidationError, match="D01-C01 references demo:R99"):
        compute_coverage(controls, INVENTORIES, {})


def test_unknown_regime_in_crosswalk_is_an_error():
    controls = [{"id": "D01-C01", "domain": "D01", "crosswalk": {"nosuch": ["X"]}}]
    with pytest.raises(ValidationError, match="unknown regime 'nosuch'"):
        compute_coverage(controls, INVENTORIES, {})


def test_exclusion_and_coverage_of_same_requirement_is_an_error():
    controls = [_control("D01-C01", ["R1"])]
    exclusions = {"demo": {"R1": "Excluded"}}
    with pytest.raises(ValidationError, match="demo:R1 is both covered and excluded"):
        compute_coverage(controls, INVENTORIES, exclusions)
