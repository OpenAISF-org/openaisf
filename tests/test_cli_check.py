"""End-to-end: the example system, its adapter output, and the check command."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from openaisf.cli import main

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = str(ROOT / "examples" / "agentic-support-bot.yaml")
EVIDENCE = str(ROOT / "examples" / "evidence")


def test_example_system_is_conformant_at_t1(capsys):
    exit_code = main(["check", "--context", CONTEXT, "--evidence", EVIDENCE,
                      "--tier", "T1"])
    out = capsys.readouterr().out
    assert "CONFORMANT" in out
    assert "lease: valid" in out
    assert exit_code == 0


def test_example_system_is_not_conformant_at_t2(capsys):
    """The same evidence does not carry a higher tier. Scope is not assurance."""
    exit_code = main(["check", "--context", CONTEXT, "--evidence", EVIDENCE,
                      "--tier", "T2"])
    out = capsys.readouterr().out
    assert "NOT CONFORMANT" in out
    assert "silence is not a pass" in out
    assert exit_code == 1


def test_json_output_carries_lease_state(capsys):
    main(["check", "--context", CONTEXT, "--evidence", EVIDENCE,
          "--tier", "T1", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["conformant"] is True
    assert payload["lease_state"] == "valid"
    assert payload["tier"] == "T1"
    assert payload["attribution"].startswith("OpenAISF")


def test_evidence_for_another_system_is_refused(tmp_path, capsys):
    record = json.loads((Path(EVIDENCE) / "D07-C01-control.json").read_text())
    record["subject"]["system_id"] = "urn:openaisf:system:somebody-else"
    (tmp_path / "foreign.json").write_text(json.dumps(record))
    exit_code = main(["check", "--context", CONTEXT, "--evidence", str(tmp_path),
                      "--tier", "T1"])
    assert exit_code == 2
    assert "scoped to one subject" in capsys.readouterr().err


def test_missing_context_file_is_a_config_error_not_a_failure(tmp_path, capsys):
    exit_code = main(["scope", "--context", str(tmp_path / "nope.yaml"),
                      "--out", str(tmp_path / "soa.yaml")])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert err.startswith("error:")
    assert "Traceback" not in err


def test_missing_verify_key_file_is_a_config_error(tmp_path, capsys):
    log = str(tmp_path / "log.jsonl")
    assert main(["publish", "--context", CONTEXT, "--evidence", EVIDENCE,
                 "--tier", "T1", "--log", log]) == 0
    capsys.readouterr()

    exit_code = main(["verify", "--log", log,
                      "--system", "urn:openaisf:system:acme-support-agent",
                      "--key", str(tmp_path / "nope.pem")])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert err.startswith("error:")
    assert "Traceback" not in err


def test_reference_adapter_reproduces_the_example_evidence(tmp_path):
    """The committed example is generated, not hand-written."""
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "adapters" / "gateway_adapter.py"),
         str(ROOT / "examples" / "gateway-summary.json"), str(tmp_path)],
        check=True, capture_output=True,
    )
    produced = {p.name for p in tmp_path.glob("*.json")}
    committed = {p.name for p in Path(EVIDENCE).glob("*.json")}
    assert produced == committed
