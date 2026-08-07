from pathlib import Path

import pytest

from openaisf.errors import ValidationError
from openaisf.loader import load_inventories

INVENTORIES = Path(__file__).resolve().parent.parent / "spec" / "crosswalk" / "inventories"


def test_load_inventories_keys_by_regime():
    inventories = load_inventories(INVENTORIES)
    assert "iso_42001" in inventories
    assert inventories["iso_42001"]["requirements"]


def test_declared_total_must_match_actual_count(tmp_path):
    (tmp_path / "fake.yaml").write_text(
        "regime: fake\n"
        "name: Fake Regime\n"
        "version: '1.0'\n"
        "licence: CC0-1.0\n"
        "attribution: A fake regime used only in tests\n"
        "regime_kind: requirement\n"
        "reproduction: authored\n"
        "declared_total: 5\n"
        "requirements:\n"
        "  - ref: A.1\n"
        "    text_summary: Only one requirement here\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="declares 5 requirements but contains 1"):
        load_inventories(tmp_path)


def test_duplicate_ref_within_regime_is_rejected(tmp_path):
    (tmp_path / "dupe.yaml").write_text(
        "regime: dupe\n"
        "name: Duplicate Regime\n"
        "version: '1.0'\n"
        "licence: CC0-1.0\n"
        "attribution: A duplicate regime used only in tests\n"
        "regime_kind: requirement\n"
        "reproduction: authored\n"
        "requirements:\n"
        "  - ref: A.1\n"
        "    text_summary: First occurrence of this reference\n"
        "  - ref: A.1\n"
        "    text_summary: Second occurrence of this reference\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="duplicate requirement reference A.1"):
        load_inventories(tmp_path)
