import json

import pytest

from openaisf.cli import main
from openaisf.coverage import RegimeCoverage


def test_coverage_is_complete_and_exits_zero(capsys):
    """The release gate. v1.0 cannot freeze while any requirement is unresolved."""
    exit_code = main(["coverage"])
    captured = capsys.readouterr()
    assert "iso_42001" in captured.out
    assert "eu_ai_act" in captured.out
    assert exit_code == 0, captured.out


def test_coverage_json_output_is_parseable(capsys):
    main(["coverage", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["complete"] is True
    assert payload["controls"] > 0
    assert payload["openaisf_original"] > 0
    assert any(r["regime"] == "owasp_llm_2026" for r in payload["regimes"])


def test_every_regime_is_fully_resolved(capsys):
    main(["coverage", "--json"])
    payload = json.loads(capsys.readouterr().out)
    for regime in payload["regimes"]:
        assert regime["covered"] + regime["excluded"] == regime["total"], regime
        assert regime["uncovered"] == [], regime


def test_a_gap_would_fail_the_gate():
    """Guards the gate itself: an unresolved requirement must exit non-zero."""
    incomplete = RegimeCoverage(
        regime="demo", name="Demo", total=2, covered=1, excluded=0, uncovered=("R2",)
    )
    assert incomplete.is_complete is False

    complete = RegimeCoverage(
        regime="demo", name="Demo", total=2, covered=1, excluded=1, uncovered=()
    )
    assert complete.is_complete is True


def test_unknown_command_exits_two(capsys):
    # argparse rejects an unknown subcommand itself and exits 2 before main()
    # can return. The exit code is what CI observes, so that is what we assert.
    with pytest.raises(SystemExit) as exc:
        main(["nosuchcommand"])
    assert exc.value.code == 2


def test_no_command_returns_two(capsys):
    assert main([]) == 2
