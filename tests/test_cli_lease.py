"""publish, verify and badge, end to end, including the adversarial paths."""

import json
from pathlib import Path

import pytest

from openaisf.cli import main

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = str(ROOT / "examples" / "agentic-support-bot.yaml")
EVIDENCE = str(ROOT / "examples" / "evidence")
SYSTEM = "urn:openaisf:system:acme-support-agent"

cryptography = pytest.importorskip  # referenced below for the ed25519 tests


def _publish(tmp_path, tier="T1", key=None):
    log = str(tmp_path / "log.jsonl")
    argv = ["publish", "--context", CONTEXT, "--evidence", EVIDENCE,
            "--tier", tier, "--log", log]
    if key:
        argv += ["--key", key, "--key-id", "test"]
    return main(argv), log


def test_publish_then_verify_then_badge(tmp_path, capsys):
    code, log = _publish(tmp_path)
    assert code == 0
    capsys.readouterr()

    assert main(["verify", "--log", log, "--system", SYSTEM]) == 0
    assert "VALID" in capsys.readouterr().out

    assert main(["badge", "--log", log, "--system", SYSTEM]) == 0
    assert "OpenAISF-T1 · valid" in capsys.readouterr().out


def test_verify_reports_integrity_only_when_unauthenticated(tmp_path, capsys):
    _, log = _publish(tmp_path)
    capsys.readouterr()
    main(["verify", "--log", log, "--system", SYSTEM])
    assert "not authenticated" in capsys.readouterr().out


def test_publishing_at_t3_refuses_a_digest_only_signature(tmp_path, capsys):
    """The tier gate on signing strength, enforced at publish rather than review."""
    code, _ = _publish(tmp_path, tier="T3")
    assert code == 2
    assert "establishes authenticity" in capsys.readouterr().err


def test_tampering_with_the_log_is_detected_at_verification(tmp_path, capsys):
    _, log = _publish(tmp_path)
    capsys.readouterr()

    entry = json.loads(Path(log).read_text().splitlines()[0])
    entry["statement"]["tier"] = "T4"
    Path(log).write_text(json.dumps(entry, sort_keys=True) + "\n")

    assert main(["verify", "--log", log, "--system", SYSTEM]) == 2
    assert "tampered with" in capsys.readouterr().err


def test_verify_of_an_unknown_system_is_an_error(tmp_path, capsys):
    _, log = _publish(tmp_path)
    capsys.readouterr()
    assert main(["verify", "--log", log, "--system", "urn:nobody"]) == 2


def test_json_verification_reports_state_and_authentication(tmp_path, capsys):
    _, log = _publish(tmp_path)
    capsys.readouterr()
    main(["verify", "--log", log, "--system", SYSTEM, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "valid"
    assert payload["signature_valid"] is True
    assert payload["authenticated"] is False
    assert "checked_at" in payload


# --- signed with real asymmetric keys ---------------------------------------


@pytest.fixture()
def keypair(tmp_path):
    crypto = pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    private = tmp_path / "signer.key"
    public = tmp_path / "signer.pub"
    private.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    public.write_bytes(key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return str(private), str(public)


def test_signed_statement_verifies_with_the_right_key(tmp_path, capsys, keypair):
    private, public = keypair
    code, log = _publish(tmp_path, key=private)
    assert code == 0
    capsys.readouterr()

    assert main(["verify", "--log", log, "--system", SYSTEM, "--key", public]) == 0
    out = capsys.readouterr().out
    assert "signature       valid" in out
    assert "not authenticated" not in out


def test_signed_statement_fails_against_an_impostor_key(tmp_path, capsys, keypair):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private, _ = keypair
    _, log = _publish(tmp_path, key=private)
    capsys.readouterr()

    impostor = tmp_path / "impostor.pub"
    impostor.write_bytes(Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))

    assert main(["verify", "--log", log, "--system", SYSTEM,
                 "--key", str(impostor)]) == 1
    assert "INVALID" in capsys.readouterr().out


def test_t3_accepts_a_real_signature(tmp_path, capsys, keypair):
    private, _ = keypair
    code, _ = _publish(tmp_path, tier="T3", key=private)
    capsys.readouterr()
    # T3 is not conformant on this evidence, but it got past the signing gate.
    assert code == 1
