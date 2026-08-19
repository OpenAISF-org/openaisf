"""The MCP server: protocol conformance, and the D19 constraint it enforces."""

import io
import json
from pathlib import Path

import pytest

from openaisf.mcp import (
    LATEST_VERSION,
    META_PROTOCOL,
    META_SERVER_INFO,
    SUPPORTED_VERSIONS,
    TOOLS,
    UNSUPPORTED_PROTOCOL_VERSION,
    McpError,
    handle,
    serve,
)

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_YAML = """
system_id: urn:openaisf:system:acme-support-agent
roles: [deployer]
system_class: [llm, agentic]
autonomy: tool_use
data_class: [internal, personal]
eu_risk: [limited]
"""


def call(method, params=None, version=LATEST_VERSION):
    params = dict(params or {})
    if version:
        params.setdefault("_meta", {})[META_PROTOCOL] = version
    return handle({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})


def tool(name, arguments=None):
    return call("tools/call", {"name": name, "arguments": arguments or {}})


# --- the governance constraint, first because it is the point ---------------


def test_no_tool_can_write_evidence_sign_or_publish():
    """D19: an agent asserting its own conformance is a claim, not evidence.

    If a future change adds a writing tool, this test is what should stop it.
    """
    names = {name for name, _d, _s, _h in TOOLS}
    forbidden = {
        "openaisf_submit_evidence", "openaisf_publish", "openaisf_sign",
        "openaisf_attest", "openaisf_append_log", "openaisf_write_evidence",
    }
    assert names & forbidden == set()
    for name in names:
        assert not any(
            verb in name for verb in ("submit", "publish", "sign", "attest", "write")
        ), f"{name} looks like it asserts something"


def test_server_states_plainly_that_it_cannot_assert():
    result = call("server/discover")
    assert "cannot submit evidence" in result["instructions"]


# --- protocol conformance ---------------------------------------------------


def test_discover_advertises_versions_capabilities_and_identity():
    result = call("server/discover")
    assert result["protocolVersions"] == list(SUPPORTED_VERSIONS)
    assert result["serverInfo"]["name"] == "openaisf"
    assert set(result["capabilities"]) == {"tools", "resources", "prompts"}


def test_every_result_carries_result_type_and_server_info():
    for method in ("server/discover", "tools/list", "resources/list", "prompts/list"):
        result = call(method)
        assert result["resultType"] == "complete"
        assert result["_meta"][META_SERVER_INFO]["name"] == "openaisf"


def test_list_results_carry_cache_hints():
    for method in ("tools/list", "resources/list", "prompts/list"):
        result = call(method)
        assert result["ttlMs"] > 0
        assert result["cacheScope"] in ("public", "private")


def test_tools_are_returned_in_deterministic_order():
    first = [t["name"] for t in call("tools/list")["tools"]]
    second = [t["name"] for t in call("tools/list")["tools"]]
    assert first == second


def test_unsupported_protocol_version_is_rejected_with_the_reserved_code():
    with pytest.raises(McpError) as exc:
        call("tools/list", version="1999-01-01")
    assert exc.value.code == UNSUPPORTED_PROTOCOL_VERSION
    assert "2026-07-28" in exc.value.data["supported"]


def test_legacy_initialize_still_answers_as_a_compatibility_probe():
    result = handle({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-11-25"},
    })
    assert result["protocolVersion"] == "2025-11-25"
    assert result["serverInfo"]["name"] == "openaisf"


def test_notifications_produce_no_response():
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_unknown_method_and_unknown_tool_are_errors():
    with pytest.raises(McpError):
        call("nonsense/method")
    with pytest.raises(McpError):
        tool("openaisf_nope")


# --- tools ------------------------------------------------------------------


def test_explain_control_returns_the_failure_mode():
    result = tool("openaisf_explain_control", {"control_id": "D07-C01"})
    text = result["content"][0]["text"]
    assert "D07-C01" in text
    assert "What goes wrong" in text
    assert result["structuredContent"]["verification"]["method"] == "emitted"


def test_explain_rejects_an_unknown_control():
    with pytest.raises(McpError, match="no such control"):
        tool("openaisf_explain_control", {"control_id": "D99-C99"})


def test_find_controls_filters_by_domain_and_system_class():
    agentic = tool("openaisf_find_controls",
                   {"domain": "D07", "system_class": "agentic"})
    assert agentic["structuredContent"]
    assert all(c["domain"] == "D07" for c in agentic["structuredContent"])

    classical = tool("openaisf_find_controls",
                     {"domain": "D07", "system_class": "classical_ml"})
    assert len(classical["structuredContent"]) < len(agentic["structuredContent"])


def test_scope_resolves_applicability_from_an_inline_context():
    result = tool("openaisf_scope", {"context": CONTEXT_YAML, "tier": "T1"})
    assert result["structuredContent"]["tier"] == "T1"
    assert result["structuredContent"]["in_scope"] == 4


def test_scope_rejects_unknown_context_keys():
    with pytest.raises(McpError, match="unknown scoping keys"):
        tool("openaisf_scope", {"context": CONTEXT_YAML + "\nfavourite: blue\n"})


def test_check_evaluates_conformance_without_writing_anything():
    result = tool("openaisf_check", {
        "context": CONTEXT_YAML,
        "tier": "T1",
        "evidence_dir": str(ROOT / "examples" / "evidence"),
    })
    assert result["structuredContent"]["conformant"] is True
    assert result["structuredContent"]["lease_state"] == "valid"


def test_check_refuses_evidence_belonging_to_another_system(tmp_path):
    source = ROOT / "examples" / "evidence" / "D07-C01-control.json"
    record = json.loads(source.read_text())
    record["subject"]["system_id"] = "urn:somebody-else"
    (tmp_path / "foreign.json").write_text(json.dumps(record))
    with pytest.raises(McpError, match="other systems"):
        tool("openaisf_check", {"context": CONTEXT_YAML, "tier": "T1",
                                "evidence_dir": str(tmp_path)})


def test_coverage_reports_completeness():
    result = tool("openaisf_coverage")
    assert result["structuredContent"]["complete"] is True
    assert result["structuredContent"]["openaisf_original"] > 0


# --- resources and prompts --------------------------------------------------


def test_principles_resource_states_the_no_prevention_rule():
    result = call("resources/read", {"uri": "openaisf://principles"})
    assert "never" in result["contents"][0]["text"].lower()
    assert "P2" in result["contents"][0]["text"]


def test_catalog_resource_is_parseable_json():
    result = call("resources/read", {"uri": "openaisf://catalog"})
    controls = json.loads(result["contents"][0]["text"])
    assert len(controls) > 100


def test_unknown_resource_is_an_error():
    with pytest.raises(McpError, match="no such resource"):
        call("resources/read", {"uri": "openaisf://nope"})


def test_remediation_prompt_forbids_fixing_the_evidence():
    result = call("prompts/get", {
        "name": "openaisf_remediate_control",
        "arguments": {"control_id": "D07-C01", "failure": "no data plane"},
    })
    text = result["messages"][0]["content"]["text"]
    assert "change to the system, not to the evidence" in text


def test_incident_prompt_walks_the_containment_chain():
    result = call("prompts/get", {
        "name": "openaisf_incident_triage",
        "arguments": {"symptoms": "agent reached an unexpected host"},
    })
    text = result["messages"][0]["content"]["text"]
    for stage in ("Bound", "Detect", "Contain", "Recover", "Prove"):
        assert stage in text


# --- T3/T4: signed evidence needs a keyring -----------------------------------


@pytest.fixture()
def signed_evidence(tmp_path):
    """A control-plane record signed by an ed25519 producer key, plus the keyring."""
    crypto = pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from openaisf.evidence import signable_payload
    from openaisf.signing import Ed25519Signer

    key = Ed25519PrivateKey.generate()
    key_id = "gateway-prod"
    private_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption())

    record = {
        "openaisf_evidence": "1.0",
        "subject": {"system_id": "urn:openaisf:system:acme-support-agent"},
        "control": "D07-C01",
        "plane": "control",
        "window": {"from": "2026-08-06T12:00:00+00:00",
                   "to": "2026-08-07T12:00:00+00:00"},
        "observations": {"enabled": True},
        "producer": {"adapter": "test", "version": "1.0"},
    }
    signature = Ed25519Signer(private_pem, key_id).sign(signable_payload(record))
    record["signature"] = signature.to_dict()

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "D07-C01-control.json").write_text(json.dumps(record))

    keyring = tmp_path / "keyring"
    keyring.mkdir()
    (keyring / f"{key_id}.pem").write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
    return str(evidence_dir), str(keyring)


def test_check_with_a_keyring_verifies_signed_evidence(signed_evidence):
    evidence_dir, keyring = signed_evidence
    result = tool("openaisf_check", {
        "context": CONTEXT_YAML, "tier": "T3",
        "evidence_dir": evidence_dir, "keyring": keyring,
    })
    text = result["content"][0]["text"]
    assert "no public key available" not in text


def test_check_without_a_keyring_reports_the_missing_key(signed_evidence):
    evidence_dir, _keyring = signed_evidence
    result = tool("openaisf_check", {
        "context": CONTEXT_YAML, "tier": "T3",
        "evidence_dir": evidence_dir,
    })
    text = result["content"][0]["text"]
    assert "no public key available" in text


# --- transport --------------------------------------------------------------


def test_stdio_loop_answers_and_survives_bad_input():
    requests = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "server/discover"}),
        "{ not json",
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    ])
    out = io.StringIO()
    serve(io.StringIO(requests), out)

    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert replies[0]["result"]["serverInfo"]["name"] == "openaisf"
    assert replies[1]["error"]["code"] == -32700
    assert replies[2]["result"]["tools"]
