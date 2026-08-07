"""The conformance lease: signing, statements, the log, and expiry by physics."""

from datetime import datetime, timedelta, timezone

import pytest

from openaisf.check import ConformanceRun, ControlResult
from openaisf.errors import ValidationError
from openaisf.log import GENESIS, TransparencyLog
from openaisf.signing import (
    DIGEST,
    DigestSigner,
    Signature,
    canonical,
    require_authenticity,
    verify,
)
from openaisf.soa import SoA, SoAEntry
from openaisf.statement import build_statement, sign_statement, verify_statement

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def _run(tier="T2", conformant=True, age_days=0.0, window_days=30.0):
    results = [
        ControlResult(
            control_id="D07-C01",
            status="pass" if conformant else "fail",
            detail="",
            obligation="required",
            age_seconds=age_days * 86400,
            window_seconds=window_days * 86400,
        )
    ]
    return ConformanceRun(
        system_id="urn:test", tier=tier, evaluated_at=NOW, results=tuple(results)
    )


def _soa(tier="T2"):
    return SoA(
        system_id="urn:test", tier=tier,
        entries=(SoAEntry("D07-C01", "applies", "required"),),
    )


# --- canonical form and signing --------------------------------------------


def test_canonical_form_is_key_order_independent():
    assert canonical({"b": 1, "a": 2}) == canonical({"a": 2, "b": 1})


def test_digest_scheme_verifies_but_provides_no_authenticity():
    payload = {"claim": "conformant"}
    sig = DigestSigner("dev").sign(payload)
    assert verify(payload, sig) is True
    assert sig.provides_authenticity is False


def test_digest_fails_verification_if_the_payload_changed():
    sig = DigestSigner().sign({"claim": "conformant"})
    assert verify({"claim": "not conformant"}, sig) is False


def test_t3_refuses_an_integrity_only_scheme():
    """A digest anybody can compute is not a signature. The gate is mechanical."""
    sig = Signature(scheme=DIGEST, value="deadbeef")
    require_authenticity(sig, "T2")  # fine below T3
    with pytest.raises(ValidationError, match="establishes authenticity"):
        require_authenticity(sig, "T3")


def test_ed25519_verification_refuses_to_degrade_without_a_key():
    sig = Signature(scheme="ed25519", value="00")
    with pytest.raises(ValidationError, match="refusing to fall back"):
        verify({"a": 1}, sig, public_key_pem=None)


# --- statements and the deadlines they carry --------------------------------


def test_statement_carries_deadlines_so_a_verifier_needs_no_catalog():
    stmt = build_statement(_run(), _soa())
    assert stmt.stale_after > stmt.issued_at
    assert stmt.expires_at > stmt.stale_after
    assert stmt.conformant is True


def test_stale_after_reflects_the_freshest_control_deadline():
    # Evidence is 10 days into a 30 day window, so 20 days of life remain.
    stmt = build_statement(_run(age_days=10, window_days=30), _soa())
    assert stmt.stale_after == NOW + timedelta(days=20)


def test_no_lease_outlives_the_tier_ceiling():
    """Certification lapses by physics: a huge window cannot buy a longer lease."""
    stmt = build_statement(_run(tier="T4", age_days=0, window_days=9999), _soa("T4"))
    assert stmt.stale_after == NOW + timedelta(days=30)


def test_a_run_with_no_freshness_windows_still_expires():
    run = ConformanceRun(
        system_id="urn:test", tier="T2", evaluated_at=NOW,
        results=(ControlResult("D01-C01", "pass", "", obligation="required"),),
    )
    stmt = build_statement(run, _soa())
    assert stmt.expires_at > NOW
    assert stmt.state_at(NOW + timedelta(days=365)) == "expired"


# --- the badge is a function of the reader's clock --------------------------


def test_state_moves_from_valid_to_stale_to_expired_with_nobody_deciding():
    stmt = build_statement(_run(age_days=0, window_days=30), _soa("T2"))
    assert stmt.state_at(NOW) == "valid"
    assert stmt.state_at(NOW + timedelta(days=31)) == "stale"
    # T2 grace is 14 days on top of the 30 day window.
    assert stmt.state_at(NOW + timedelta(days=50)) == "expired"


def test_a_non_conformant_statement_never_reads_as_valid():
    run = _run(conformant=False)
    stmt = build_statement(run, _soa())
    assert stmt.conformant is False
    assert stmt.state_at(NOW) == "revoked"


def test_statement_round_trips_through_serialisation():
    signed = sign_statement(build_statement(_run(), _soa()), DigestSigner("dev"))
    restored = type(signed).from_dict(signed.to_dict())
    assert restored.payload() == signed.payload()
    assert verify_statement(restored) is True


def test_tampering_with_a_statement_breaks_its_signature():
    signed = sign_statement(build_statement(_run(), _soa()), DigestSigner("dev"))
    data = signed.to_dict()
    data["tier"] = "T4"
    forged = type(signed).from_dict(data)
    assert verify_statement(forged) is False


# --- the transparency log ---------------------------------------------------


def test_empty_log_head_is_genesis(tmp_path):
    assert TransparencyLog(tmp_path / "log.jsonl").head() == GENESIS


def test_entries_chain_to_their_predecessor(tmp_path):
    log = TransparencyLog(tmp_path / "log.jsonl")
    first = log.append({"system_id": "a"})
    second = log.append({"system_id": "b"})
    assert first.previous == GENESIS
    assert second.previous == first.entry_hash
    log.verify_chain()


def test_altering_a_past_entry_is_detected(tmp_path):
    path = tmp_path / "log.jsonl"
    log = TransparencyLog(path)
    log.append({"system_id": "a", "conformant": False})
    log.append({"system_id": "b"})

    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace('"conformant": false', '"conformant": true')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="tampered with"):
        log.verify_chain()


def test_removing_an_entry_is_detected(tmp_path):
    path = tmp_path / "log.jsonl"
    log = TransparencyLog(path)
    log.append({"system_id": "a"})
    log.append({"system_id": "b"})
    log.append({"system_id": "c"})

    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="removed or reordered"):
        log.verify_chain()


def test_latest_entry_for_a_system_is_the_most_recent(tmp_path):
    log = TransparencyLog(tmp_path / "log.jsonl")
    log.append({"system_id": "urn:a", "tier": "T1"})
    log.append({"system_id": "urn:b", "tier": "T1"})
    log.append({"system_id": "urn:a", "tier": "T2"})
    assert log.latest_for("urn:a").statement["tier"] == "T2"
    assert log.latest_for("urn:nope") is None
