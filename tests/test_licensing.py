"""Licensing invariants for the requirement inventories.

OpenAISF references external regimes; it does not reproduce them. These tests
make that a property of the repository rather than a promise in a document.
"""

from pathlib import Path

import pytest

from openaisf.errors import ValidationError
from openaisf.loader import load_inventories

INVENTORIES = Path(__file__).resolve().parent.parent / "spec" / "crosswalk" / "inventories"

# Regimes whose terms do not permit reproducing their authored text in a work
# that is redistributed and commercially leveraged. These MUST stay
# reference-only. Adding a regime here is a legal decision, not a style choice.
RESTRICTED = {"iso_42001", "csa_aicm"}


def test_every_inventory_declares_licence_and_reproduction_policy():
    for regime, data in load_inventories(INVENTORIES).items():
        assert data.get("licence"), f"{regime}: no licence declared"
        assert data.get("attribution"), f"{regime}: no attribution notice"
        assert data.get("reproduction") in {
            "reference-only",
            "descriptive",
            "authored",
        }, f"{regime}: invalid reproduction policy"


def test_restricted_regimes_are_reference_only():
    inventories = load_inventories(INVENTORIES)
    for regime in RESTRICTED:
        assert regime in inventories, f"missing inventory: {regime}"
        assert inventories[regime]["reproduction"] == "reference-only", (
            f"{regime} is under terms that do not permit reproducing its text. "
            f"Its inventory must stay reference-only."
        )


def test_restricted_regime_summaries_carry_no_source_authored_text():
    """A reference-only inventory must use a single generated descriptor form.

    If someone pastes real control titles back in, the number of distinct
    descriptors explodes. Holding the distinct count low is a crude but
    effective tripwire, and it fails loudly at exactly the moment the mistake
    is introduced.
    """
    inventories = load_inventories(INVENTORIES)
    for regime in RESTRICTED:
        summaries = {r["text_summary"] for r in inventories[regime]["requirements"]}
        total = len(inventories[regime]["requirements"])
        # A generated descriptor form yields one distinct string per grouping
        # (9 objectives for ISO, 18 domains for AICM). Pasting real titles back
        # yields one distinct string per requirement. Half is a wide margin
        # between those two regimes.
        assert len(summaries) <= total // 2, (
            f"{regime} has {len(summaries)} distinct descriptors across {total} "
            f"requirements, which suggests source-authored text was reintroduced"
        )


def test_inventory_without_licence_fails_to_load(tmp_path):
    (tmp_path / "nolicence.yaml").write_text(
        "regime: nolicence\n"
        "name: No Licence Regime\n"
        "version: '1.0'\n"
        "requirements:\n"
        "  - ref: A.1\n"
        "    text_summary: A requirement with no licence block\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_inventories(tmp_path)
