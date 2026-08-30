from pathlib import Path

from openaisf.loader import load_inventories

INVENTORIES = Path(__file__).resolve().parent.parent / "spec" / "crosswalk" / "inventories"

PUBLISHED_COUNTS = {
    "iso_42001": 38,
    "iso_23894": 13,
    "owasp_llm_2025": 10,
    "owasp_llm_2026": 10,
    "nist_ai_rmf": 72,
    "csa_aicm": 247,
    "mcp_38": 38,
    "mitre_atlas": 178,
}


def test_inventories_match_published_counts():
    inventories = load_inventories(INVENTORIES)
    for regime, expected in PUBLISHED_COUNTS.items():
        assert regime in inventories, f"missing inventory: {regime}"
        actual = len(inventories[regime]["requirements"])
        assert actual == expected, f"{regime}: expected {expected}, found {actual}"


def test_nist_function_subcategory_split():
    inventories = load_inventories(INVENTORIES)
    refs = [r["ref"] for r in inventories["nist_ai_rmf"]["requirements"]]
    counts = {
        "GOVERN": sum(1 for r in refs if r.startswith("GOVERN")),
        "MAP": sum(1 for r in refs if r.startswith("MAP")),
        "MEASURE": sum(1 for r in refs if r.startswith("MEASURE")),
        "MANAGE": sum(1 for r in refs if r.startswith("MANAGE")),
    }
    assert counts == {"GOVERN": 19, "MAP": 18, "MEASURE": 22, "MANAGE": 13}


def test_owasp_editions_are_separate_regimes_with_colliding_identifiers():
    """The 2026 edition reuses LLM01-LLM10 for a different set of risks.

    Keeping the editions as separate regimes is what stops an identifier's
    meaning changing under existing crosswalk entries. If these two ever get
    merged, this test is the thing that should stop it.
    """
    inventories = load_inventories(INVENTORIES)
    refs_2025 = {r["ref"] for r in inventories["owasp_llm_2025"]["requirements"]}
    refs_2026 = {r["ref"] for r in inventories["owasp_llm_2026"]["requirements"]}
    assert refs_2025 == refs_2026, "both editions use the same identifier space"

    # ...but the same identifier denotes a different risk in each edition.
    by_ref_2025 = {r["ref"]: r["text_summary"] for r in inventories["owasp_llm_2025"]["requirements"]}
    by_ref_2026 = {r["ref"]: r["text_summary"] for r in inventories["owasp_llm_2026"]["requirements"]}
    assert by_ref_2025["LLM03"] != by_ref_2026["LLM03"], (
        "LLM03 is Supply Chain in 2025 and Excessive Agency in 2026"
    )


def test_eu_ai_act_is_present_and_locked():
    inventories = load_inventories(INVENTORIES)
    assert "eu_ai_act" in inventories
    assert inventories["eu_ai_act"]["declared_total"] is not None


def test_every_inventory_declares_its_total():
    inventories = load_inventories(INVENTORIES)
    for regime, data in inventories.items():
        assert data["declared_total"] is not None, f"{regime} has no declared_total"
