import pytest

from openaisf.applicability import SystemContext
from openaisf.errors import ValidationError
from openaisf.soa import (
    APPLIES,
    EXCLUDED,
    INHERITED,
    NOT_APPLICABLE,
    load_context,
    resolve_soa,
    to_document,
)

CATALOG = [
    {"id": "D01-C01", "roles": ["deployer"], "tiers": {"T2": "required"}},
    {
        "id": "D07-C01",
        "roles": ["deployer"],
        "tiers": {"T2": "required"},
        "applies_when": {"system_class": ["agentic"]},
    },
    {"id": "D03-C01", "roles": ["deployer"], "tiers": {"T2": "recommended"}},
    {"id": "D04-C01", "roles": ["provider"], "tiers": {"T2": "required"}},
]


def ctx(**overrides) -> SystemContext:
    base = dict(
        system_id="urn:openaisf:system:test",
        roles=["deployer"],
        system_class=["llm"],
        autonomy="none",
    )
    base.update(overrides)
    return SystemContext(**base)


def test_verdicts_partition_the_catalog():
    soa = resolve_soa(CATALOG, ctx(), "T2")
    assert len(soa.entries) == len(CATALOG)
    assert sum(soa.counts.values()) == len(CATALOG)


def test_out_of_scope_controls_are_not_applicable():
    soa = resolve_soa(CATALOG, ctx(), "T2")
    verdicts = {e.control_id: e.verdict for e in soa.entries}
    # non-agentic system
    assert verdicts["D07-C01"] == NOT_APPLICABLE
    # provider-only control, we are a deployer
    assert verdicts["D04-C01"] == NOT_APPLICABLE
    assert verdicts["D01-C01"] == APPLIES


def test_obligation_is_carried_through():
    soa = resolve_soa(CATALOG, ctx(), "T2")
    by_id = {e.control_id: e for e in soa.entries}
    assert by_id["D01-C01"].obligation == "required"
    assert by_id["D03-C01"].obligation == "recommended"


def test_inheritance_records_the_upstream_component():
    soa = resolve_soa(
        CATALOG, ctx(), "T2", inherits={"D03-C01": "anthropic/claude-opus-5"}
    )
    entry = next(e for e in soa.entries if e.control_id == "D03-C01")
    assert entry.verdict == INHERITED
    assert entry.inherited_from == "anthropic/claude-opus-5"


def test_exclusion_requires_a_reason():
    with pytest.raises(ValidationError, match="states no reason"):
        resolve_soa(CATALOG, ctx(), "T2", exclusions={"D01-C01": "   "})


def test_exclusion_with_reason_is_recorded():
    soa = resolve_soa(
        CATALOG, ctx(), "T2", exclusions={"D01-C01": "Superseded by group policy"}
    )
    entry = next(e for e in soa.entries if e.control_id == "D01-C01")
    assert entry.verdict == EXCLUDED
    assert entry.reason == "Superseded by group policy"


def test_excluding_an_inapplicable_control_is_an_error():
    with pytest.raises(ValidationError, match="does not apply to this system"):
        resolve_soa(CATALOG, ctx(), "T2", exclusions={"D07-C01": "we are not agentic"})


def test_unknown_control_in_scoping_file_is_an_error():
    with pytest.raises(ValidationError, match="not in the catalog"):
        resolve_soa(CATALOG, ctx(), "T2", exclusions={"D99-C01": "nope"})


def test_control_cannot_be_both_inherited_and_excluded():
    with pytest.raises(ValidationError, match="both inherited and excluded"):
        resolve_soa(
            CATALOG,
            ctx(),
            "T2",
            inherits={"D01-C01": "upstream"},
            exclusions={"D01-C01": "reason"},
        )


def test_in_scope_counts_applies_plus_inherited():
    soa = resolve_soa(
        CATALOG,
        ctx(system_class=["llm", "agentic"]),
        "T2",
        inherits={"D03-C01": "upstream"},
    )
    assert soa.counts[APPLIES] == 2  # D01-C01, D07-C01
    assert soa.counts[INHERITED] == 1
    assert soa.in_scope == 3


def test_document_summarises_not_applicable_rather_than_listing_it_inline():
    soa = resolve_soa(CATALOG, ctx(), "T2")
    doc = to_document(soa)
    listed = {c["control_id"] for c in doc["controls"]}
    assert "D07-C01" not in listed
    assert "D07-C01" in doc["not_applicable"]
    assert doc["attribution"].startswith("OpenAISF")


def test_load_context_rejects_unknown_keys(tmp_path):
    path = tmp_path / "ctx.yaml"
    path.write_text(
        "system_id: urn:test\nroles: [deployer]\nfavourite_colour: blue\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="unknown scoping keys"):
        load_context(path)


def test_load_context_extracts_inherits_and_exclusions(tmp_path):
    path = tmp_path / "ctx.yaml"
    path.write_text(
        "system_id: urn:test\n"
        "roles: [deployer]\n"
        "system_class: [llm]\n"
        "autonomy: tool_use\n"
        "inherits:\n"
        "  D03-C01: upstream/model\n"
        "exclusions:\n"
        "  D01-C01: A stated reason\n",
        encoding="utf-8",
    )
    context, inherits, exclusions = load_context(path)
    assert context.autonomy == "tool_use"
    assert inherits == {"D03-C01": "upstream/model"}
    assert exclusions == {"D01-C01": "A stated reason"}
