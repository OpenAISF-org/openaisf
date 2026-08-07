"""OSCAL export: an output format that carries what OSCAL cannot model."""

import json
from datetime import datetime, timezone
from pathlib import Path

from openaisf.check import ConformanceRun, ControlResult
from openaisf.cli import main
from openaisf.loader import load_catalog
from openaisf.oscal import OSCAL_VERSION, assessment_results, component_definition
from openaisf.soa import SoA, SoAEntry
from openaisf.statement import build_statement

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def _run(**overrides):
    results = (
        ControlResult("D07-C01", "pass", "fine", obligation="required",
                      planes_present=("control", "data"),
                      age_seconds=0, window_seconds=86400 * 30),
        ControlResult("D15-C01", "fail", "no data plane", obligation="required"),
        ControlResult("D20-C03", "not_applicable", "out of scope"),
    )
    base = dict(system_id="urn:test", tier="T2", evaluated_at=NOW, results=results)
    base.update(overrides)
    return ConformanceRun(**base)


def _soa():
    return SoA(system_id="urn:test", tier="T2",
               entries=(SoAEntry("D07-C01", "applies", "required"),))


def test_document_is_wellformed_oscal():
    doc = assessment_results(_run())["assessment-results"]
    assert doc["metadata"]["oscal-version"] == OSCAL_VERSION
    assert doc["uuid"]
    assert doc["results"][0]["start"] and doc["results"][0]["end"]


def test_out_of_scope_controls_are_not_reported_as_assessed():
    """A conformance artefact listing hundreds of inapplicable controls is unread."""
    result = assessment_results(_run())["assessment-results"]["results"][0]
    ids = {f["target"]["target-id"] for f in result["findings"]}
    assert ids == {"D07-C01", "D15-C01"}


def test_findings_map_status_onto_oscal_satisfaction():
    result = assessment_results(_run())["assessment-results"]["results"][0]
    states = {
        f["target"]["target-id"]: f["target"]["status"]["state"]
        for f in result["findings"]
    }
    assert states["D07-C01"] == "satisfied"
    assert states["D15-C01"] == "not-satisfied"


def test_lease_travels_as_properties_because_oscal_cannot_model_it():
    run = _run()
    statement = build_statement(run, _soa())
    result = assessment_results(run, statement)["assessment-results"]["results"][0]
    props = {p["name"]: p["value"] for p in result["props"]}
    assert props["openaisf-lease-state"] == run.lease_state
    assert props["openaisf-tier"] == "T2"
    assert "openaisf-expires-at" in props
    assert "openaisf-stale-after" in props


def test_evidence_planes_survive_the_export():
    result = assessment_results(_run())["assessment-results"]["results"][0]
    observation = next(
        o for o in result["observations"] if "D07-C01" in o["title"]
    )
    props = {p["name"]: p["value"] for p in observation["props"]}
    assert props["openaisf-evidence-planes"] == "control,data"


def test_uuids_are_deterministic_so_reexport_diffs_cleanly():
    first = assessment_results(_run())
    second = assessment_results(_run())
    assert first["assessment-results"]["uuid"] == second["assessment-results"]["uuid"]


def test_component_definition_describes_the_whole_catalog():
    controls = load_catalog(ROOT / "spec" / "catalog")
    doc = component_definition(controls)["component-definition"]
    implemented = doc["components"][0]["control-implementations"][0][
        "implemented-requirements"
    ]
    assert len(implemented) == len(controls)
    assert doc["metadata"]["oscal-version"] == OSCAL_VERSION


def test_cli_exports_both_documents(capsys):
    assert main([
        "export", "assessment-results",
        "--context", str(ROOT / "examples" / "agentic-support-bot.yaml"),
        "--evidence", str(ROOT / "examples" / "evidence"),
        "--tier", "T1",
    ]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert "assessment-results" in doc

    assert main(["export", "component-definition"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert "component-definition" in doc
