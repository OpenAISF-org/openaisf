import pytest

from openaisf.coverage import compute_provenance, normalise_crosswalk
from openaisf.errors import ValidationError


# --- normalisation ----------------------------------------------------------


def test_bare_string_reference_defaults_to_full():
    control = {"id": "D01-C01", "crosswalk": {"iso_42001": ["A.3.2"]}}
    assert normalise_crosswalk(control) == {"iso_42001": [("A.3.2", "full")]}


def test_object_form_carries_explicit_strength():
    control = {
        "id": "D15-C07",
        "crosswalk": {"iso_42001": [{"ref": "A.9.4", "strength": "partial"}]},
    }
    assert normalise_crosswalk(control) == {"iso_42001": [("A.9.4", "partial")]}


def test_mixed_forms_in_one_regime():
    control = {
        "id": "D07-C01",
        "crosswalk": {
            "iso_42001": ["A.6.2.6", {"ref": "A.9.4", "strength": "partial"}]
        },
    }
    assert normalise_crosswalk(control) == {
        "iso_42001": [("A.6.2.6", "full"), ("A.9.4", "partial")]
    }


def test_underscore_keys_and_empty_lists_are_dropped():
    control = {"id": "D19-C01", "crosswalk": {"_note": ["free text"], "iso_42001": []}}
    assert normalise_crosswalk(control) == {}


# --- provenance -------------------------------------------------------------


def test_no_crosswalk_is_original():
    controls = [{"id": "D15-C01", "crosswalk": {}}]
    assert compute_provenance(controls) == {"D15-C01": "OpenAISF-original"}


def test_all_partial_mappings_is_original_however_many_regimes():
    """The defect this replaced: breadth of mapping is not derivativeness.

    A control can touch four regimes loosely and still be required by none of
    them. That is originality, not adoption.
    """
    controls = [
        {
            "id": "D15-C07",
            "crosswalk": {
                "iso_42001": [{"ref": "A.9.4", "strength": "partial"}],
                "nist_ai_rmf": [{"ref": "MAP-1.1", "strength": "partial"}],
                "eu_ai_act": [{"ref": "Art.26(1)", "strength": "partial"}],
                "csa_aicm": [{"ref": "GRC-01", "strength": "partial"}],
            },
        }
    ]
    assert compute_provenance(controls) == {"D15-C07": "OpenAISF-original"}


def test_exactly_one_full_mapping_is_derived():
    controls = [
        {
            "id": "D01-C01",
            "crosswalk": {
                "iso_42001": ["A.3.2"],
                "nist_ai_rmf": [{"ref": "GOVERN-2.1", "strength": "partial"}],
            },
        }
    ]
    assert compute_provenance(controls) == {"D01-C01": "derived"}


def test_two_or_more_full_mappings_is_adopted():
    controls = [
        {
            "id": "D05-C01",
            "crosswalk": {"iso_42001": ["A.6.2.4"], "owasp_llm_2025": ["LLM01"]},
        }
    ]
    assert compute_provenance(controls) == {"D05-C01": "adopted"}


def test_two_full_mappings_within_one_regime_still_counts_as_adopted():
    controls = [{"id": "D03-C01", "crosswalk": {"iso_42001": ["A.7.2", "A.7.3"]}}]
    assert compute_provenance(controls) == {"D03-C01": "adopted"}


def test_declared_provenance_contradicting_computed_is_an_error():
    controls = [
        {
            "id": "D01-C01",
            "crosswalk": {"iso_42001": ["A.3.2"], "nist_ai_rmf": ["GOVERN-2.1"]},
            "provenance": "OpenAISF-original",
        }
    ]
    with pytest.raises(ValidationError, match="declares provenance"):
        compute_provenance(controls)


# --- threat regimes never count as full ------------------------------------

THREAT = frozenset({"owasp_llm_2025", "mitre_atlas", "mcp_38"})


def test_threat_regime_mappings_resolve_to_partial():
    control = {"id": "D07-C04", "crosswalk": {"owasp_llm_2025": ["LLM06"]}}
    assert normalise_crosswalk(control, THREAT) == {
        "owasp_llm_2025": [("LLM06", "partial")]
    }


def test_control_mapping_only_to_threat_catalogues_is_original():
    """A threat catalogue says an attack exists, not that a control is required."""
    controls = [
        {
            "id": "D07-C04",
            "crosswalk": {
                "owasp_llm_2025": ["LLM06"],
                "mitre_atlas": ["AML.T0053"],
                "mcp_38": ["MCP-22", "MCP-23"],
            },
        }
    ]
    assert compute_provenance(controls, THREAT) == {"D07-C04": "OpenAISF-original"}


def test_explicit_full_on_a_threat_regime_is_an_error():
    control = {
        "id": "D07-C04",
        "crosswalk": {"mitre_atlas": [{"ref": "AML.T0053", "strength": "full"}]},
    }
    with pytest.raises(ValidationError, match="threat catalogue"):
        normalise_crosswalk(control, THREAT)
