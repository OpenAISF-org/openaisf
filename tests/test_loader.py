from pathlib import Path

import pytest

from openaisf.errors import ValidationError
from openaisf.loader import load_catalog

SPEC = Path(__file__).resolve().parent.parent / "spec" / "catalog"


def test_load_catalog_returns_controls_sorted_by_id():
    controls = load_catalog(SPEC)
    assert len(controls) >= 1
    ids = [c["id"] for c in controls]
    assert ids == sorted(ids)
    assert all(c["id"].startswith("D") for c in controls)


def test_load_catalog_rejects_bad_identifier(tmp_path):
    (tmp_path / "bad.yaml").write_text(
        "controls:\n"
        "  - id: NOPE-1\n"
        "    title: Bad\n"
        "    domain: D01\n"
        "    level: core\n"
        "    normative: An identifier that does not match the scheme.\n"
        "    rfc2119: MUST\n"
        "    roles: [provider]\n"
        "    lifecycle: [conceive]\n"
        "    tiers: {T3: required}\n"
        "    verification: {method: attested}\n"
        "    crosswalk: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_catalog(tmp_path)


def test_load_catalog_rejects_duplicate_identifier(tmp_path):
    body = (
        "controls:\n"
        "  - id: D01-C01\n"
        "    title: One\n"
        "    domain: D01\n"
        "    level: core\n"
        "    normative: First control.\n"
        "    rfc2119: MUST\n"
        "    roles: [provider]\n"
        "    lifecycle: [conceive]\n"
        "    tiers: {T3: required}\n"
        "    verification: {method: attested}\n"
        "    crosswalk: {}\n"
    )
    (tmp_path / "a.yaml").write_text(body, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(ValidationError, match="D01-C01"):
        load_catalog(tmp_path)


def test_duplicate_mapping_key_is_rejected(tmp_path):
    """PyYAML keeps the last duplicate silently; in a crosswalk that discards
    mappings and the coverage report under-counts with no error anywhere."""
    (tmp_path / "dupe.yaml").write_text(
        "controls:\n"
        "  - id: D01-C01\n"
        "    title: A control with a duplicated crosswalk key\n"
        "    domain: D01\n"
        "    level: core\n"
        "    normative: A normative statement of adequate length.\n"
        "    rfc2119: MUST\n"
        "    roles: [provider]\n"
        "    lifecycle: [conceive]\n"
        "    tiers: {T3: required}\n"
        "    verification: {method: attested}\n"
        "    crosswalk:\n"
        "      iso_42001: [A.2.2]\n"
        "      iso_42001: [A.2.3]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="duplicate key"):
        load_catalog(tmp_path)
