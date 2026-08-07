"""D17-C02: assurance decay propagates downstream.

The property no existing framework models. An upstream provider whose badge
goes stale degrades every dependent within one freshness window, and it only
works because the downstream run goes and looks rather than trusting a string.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from openaisf.applicability import SystemContext
from openaisf.check import FAIL, INHERITED_OK, STALE, evaluate
from openaisf.evidence import index_evidence
from openaisf.log import TransparencyLog
from openaisf.signing import Ed25519Signer
from openaisf.soa import resolve_soa
from openaisf.statement import ConformanceStatement, sign_statement

CONTROL = {
    "id": "D03-C01",
    "domain": "D03",
    "roles": ["deployer"],
    "tiers": {"T2": "required", "T3": "required"},
    "verification": {"method": "attested", "planes": ["control"],
                     "freshness": {"T2": "P90D", "T3": "P30D"}},
    "crosswalk": {},
}
CTX = SystemContext(system_id="urn:downstream", roles=["deployer"],
                    system_class=["llm"], autonomy="none")


def _signer(tmp_path):
    """Upstream statements at T3+ need a real signature, so the fixture uses one."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key_path = tmp_path / "upstream.key"
    if not key_path.exists():
        key_path.write_bytes(Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
    return Ed25519Signer(key_path.read_bytes(), "upstream")


def _upstream(tmp_path, *, age_days=0, lease_days=90, tier="T4", conformant=True):
    """Publish an upstream statement whose lease is a chosen age."""
    issued = datetime.now(timezone.utc) - timedelta(days=age_days)
    stmt = ConformanceStatement(
        system_id="urn:upstream", tier=tier, issued_at=issued,
        stale_after=issued + timedelta(days=lease_days),
        expires_at=issued + timedelta(days=lease_days + 14),
        conformant=conformant, soa_digest="sha256:aa", counts={}, blocking=(),
    )
    log_path = tmp_path / "upstream-log.jsonl"
    TransparencyLog(log_path).append(
        sign_statement(stmt, _signer(tmp_path)).to_dict()
    )
    return {"upstream": "upstream/model", "log": str(log_path),
            "system_id": "urn:upstream"}


def _run(ref, tier="T2"):
    soa = resolve_soa([CONTROL], CTX, tier, inherits={"D03-C01": ref})
    out = evaluate([CONTROL], soa, index_evidence([]))
    return next(r for r in out.results if r.control_id == "D03-C01")


def test_a_live_upstream_lease_satisfies_the_inherited_control(tmp_path):
    result = _run(_upstream(tmp_path))
    assert result.status == INHERITED_OK
    assert "upstream lease valid until" in result.detail


def test_a_stale_upstream_lease_degrades_the_dependent(tmp_path):
    result = _run(_upstream(tmp_path, age_days=95, lease_days=90))
    assert result.status == STALE
    assert "propagates downstream" in result.detail


def test_an_expired_upstream_lease_fails_the_dependent(tmp_path):
    result = _run(_upstream(tmp_path, age_days=200, lease_days=90))
    assert result.status == FAIL
    assert "no longer proven by anybody" in result.detail


def test_assurance_cannot_be_laundered_upward_through_a_dependency(tmp_path):
    """You cannot inherit above the upstream's verified tier."""
    result = _run(_upstream(tmp_path, tier="T2"), tier="T3")
    assert result.status == FAIL
    assert "laundered upward" in result.detail


def test_a_non_conformant_upstream_is_not_inheritable(tmp_path):
    result = _run(_upstream(tmp_path, conformant=False))
    assert result.status == FAIL


def test_a_missing_upstream_statement_fails_rather_than_passing(tmp_path):
    log_path = tmp_path / "empty-log.jsonl"
    TransparencyLog(log_path).append({"system_id": "urn:somebody-else"})
    result = _run({"upstream": "ghost", "log": str(log_path),
                   "system_id": "urn:upstream"})
    assert result.status == FAIL
    assert "nothing is being inherited" in result.detail


def test_a_tampered_upstream_log_fails_the_dependent(tmp_path):
    """A downstream system inherits from a log it does not control."""
    ref = _upstream(tmp_path)
    path = Path(ref["log"])
    entry = json.loads(path.read_text().splitlines()[0])
    entry["statement"]["soa_digest"] = "sha256:forged"
    path.write_text(json.dumps(entry, sort_keys=True) + "\n")
    result = _run(ref)
    assert result.status == FAIL
    assert "not intact" in result.detail


def test_an_inheritance_without_a_log_reference_is_rejected_as_malformed():
    with pytest.raises(Exception, match="log and system_id"):
        resolve_soa([CONTROL], CTX, "T2",
                    inherits={"D03-C01": {"upstream": "x", "system_id": "urn:y"}})
