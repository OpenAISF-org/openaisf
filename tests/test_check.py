from datetime import datetime, timedelta, timezone

import pytest

from openaisf.applicability import SystemContext
from openaisf.check import (
    EXPIRED,
    FAIL,
    FAILING,
    INHERITED_OK,
    LEASE_STALE,
    NA,
    PASS,
    STALE,
    VALID,
    evaluate,
)
from openaisf.errors import ValidationError
from openaisf.evidence import EvidenceRecord, index_evidence
from openaisf.signing import DIGEST, ED25519, Signature
from openaisf.soa import resolve_soa

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)

EMITTED = {
    "id": "D07-C01",
    "domain": "D07",
    "roles": ["deployer"],
    "tiers": {"T3": "required"},
    "verification": {
        "method": "emitted",
        "planes": ["control", "data"],
        "freshness": {"T3": "P7D"},
    },
    "crosswalk": {},
}
ASSERTED = {
    "id": "D01-C01",
    "domain": "D01",
    "roles": ["deployer"],
    "tiers": {"T3": "required"},
    "verification": {"method": "asserted", "planes": ["control"],
                     "freshness": {"T3": "P90D"}},
    "crosswalk": {},
}
ASSESSED = {
    "id": "D19-C02",
    "domain": "D19",
    "roles": ["deployer"],
    "tiers": {"T3": "required"},
    "verification": {"method": "assessed"},
    "crosswalk": {},
}
CATALOG = [ASSERTED, EMITTED, ASSESSED]

CTX = SystemContext(
    system_id="urn:test", roles=["deployer"], system_class=["agentic"],
    autonomy="tool_use",
)


def rec(control, plane, age_days=0.0, *, scheme=ED25519, verified=True,
        key_known=True, **obs):
    """A properly signed record by default; the gate is tested separately."""
    end = NOW - timedelta(days=age_days)
    signature = (
        Signature(scheme=scheme, value="x", key_id="test") if scheme else None
    )
    return EvidenceRecord(
        control=control, plane=plane, system_id="urn:test",
        window_from=end - timedelta(days=1), window_to=end,
        observations=obs, producer="test-adapter", producer_version="1.0",
        signature=signature, verified=verified, key_known=key_known,
    )


def run(records, catalog=CATALOG, tier="T3"):
    soa = resolve_soa(catalog, CTX, tier)
    return evaluate(catalog, soa, index_evidence(records), now=NOW)


def _status(result_run, control_id):
    return next(r.status for r in result_run.results if r.control_id == control_id)


# --- missing signal is failure, not silence --------------------------------


def test_missing_plane_fails_rather_than_passing_by_silence():
    out = run([rec("D07-C01", "control", enabled=True)])
    assert _status(out, "D07-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D07-C01")
    assert "silence is not a pass" in detail


def test_both_planes_present_and_fresh_passes():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=1000, decisions_total=1000),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D07-C01") == PASS


def test_no_record_at_all_fails_an_asserted_control():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=1, decisions_total=1),
    ])
    assert _status(out, "D01-C01") == FAIL


# --- the two-plane contradiction rule --------------------------------------


def test_declared_enabled_with_traffic_and_no_decisions_fails():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=1_000_000, decisions_total=0),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D07-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D07-C01")
    assert "was not operating" in detail


def test_no_traffic_and_no_decisions_is_not_a_contradiction():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=0, decisions_total=0),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D07-C01") == PASS


def test_decisions_without_traffic_fail_as_fabricated():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=0, decisions_total=3),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D07-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D07-C01")
    assert "no traffic" in detail


def test_decisions_outnumbering_requests_is_not_a_contradiction():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=1, decisions_total=7),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D07-C01") == PASS


def test_contradiction_on_an_asserted_control_cannot_be_resolved_by_attestation():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=1, decisions_total=1),
        rec("D01-C01", "control", enabled=True),
        rec("D01-C01", "data", traffic_requests=500, decisions_total=0),
    ])
    assert _status(out, "D01-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D01-C01")
    assert "cannot resolve this" in detail


# --- freshness and the lease ------------------------------------------------


def test_evidence_past_the_window_goes_stale():
    out = run([
        rec("D07-C01", "control", 10, enabled=True),
        rec("D07-C01", "data", 10, traffic_requests=10, decisions_total=10),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D07-C01") == STALE


def test_lease_is_valid_when_everything_is_fresh_and_passing():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=5, decisions_total=5),
        rec("D01-C01", "control"),
    ], catalog=[ASSERTED, EMITTED])
    assert out.conformant is True
    assert out.lease_state == VALID


def test_lease_goes_stale_within_grace_then_expires_beyond_it():
    # T3 window P7D, grace 3 days. 9 days old = 2 days overrun -> stale.
    within = run([
        rec("D07-C01", "control", 9, enabled=True),
        rec("D07-C01", "data", 9, traffic_requests=5, decisions_total=5),
        rec("D01-C01", "control"),
    ], catalog=[ASSERTED, EMITTED])
    assert within.lease_state == LEASE_STALE

    # 20 days old = 13 days overrun -> beyond grace.
    beyond = run([
        rec("D07-C01", "control", 20, enabled=True),
        rec("D07-C01", "data", 20, traffic_requests=5, decisions_total=5),
        rec("D01-C01", "control"),
    ], catalog=[ASSERTED, EMITTED])
    assert beyond.lease_state == EXPIRED


def test_a_hard_failure_reports_failing_rather_than_merely_stale():
    """A missing signal is a hard failure but not fabrication.

    It degrades the lease to failing rather than revoking it, because nothing
    about the evidence that does exist has been shown to be untrue.
    """
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=100, decisions_total=100),
    ], catalog=[ASSERTED, EMITTED])
    assert _status(out, "D01-C01") == FAIL
    assert out.lease_state == FAILING


def test_fabrication_revokes_where_a_missing_signal_only_fails():
    """The distinction that matters during an incident."""
    missing = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=100, decisions_total=100),
    ], catalog=[ASSERTED, EMITTED])
    lying = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=100, decisions_total=0),
        rec("D01-C01", "control"),
    ], catalog=[ASSERTED, EMITTED])
    assert missing.lease_state == FAILING
    assert lying.lease_state == "revoked"


# --- verdict handling -------------------------------------------------------


def test_out_of_scope_controls_do_not_block():
    soa = resolve_soa(
        CATALOG,
        SystemContext(system_id="urn:test", roles=["deployer"],
                      system_class=["llm"], autonomy="none"),
        "T1",
    )
    out = evaluate(CATALOG, soa, index_evidence([]))
    assert all(r.status == NA for r in out.results)
    assert out.conformant is True


def test_asserted_inheritance_is_accepted_below_t3():
    catalog = [{**ASSERTED, "tiers": {"T2": "required", "T3": "required"}}]
    soa = resolve_soa(catalog, CTX, "T2", inherits={"D01-C01": "upstream/model"})
    out = evaluate(catalog, soa, index_evidence([]), now=NOW)
    assert _status(out, "D01-C01") == INHERITED_OK


def test_asserted_inheritance_is_refused_at_t3():
    """An unverifiable claim about somebody else's conformance is not assurance."""
    soa = resolve_soa(CATALOG, CTX, "T3", inherits={"D01-C01": "upstream/model"})
    out = evaluate(CATALOG, soa, index_evidence([]), now=NOW)
    assert _status(out, "D01-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D01-C01")
    assert "not verifiable" in detail


def test_assessed_controls_require_a_certifier_and_block():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=5, decisions_total=5),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D19-C02") == "manual"
    assert out.conformant is False


def test_naive_evaluation_time_is_rejected():
    soa = resolve_soa(CATALOG, CTX, "T3")
    with pytest.raises(ValidationError, match="timezone-aware"):
        evaluate(CATALOG, soa, {}, now=datetime(2026, 8, 7, 12, 0))


# --- disqualifying failures -------------------------------------------------


RECOMMENDED_EMITTED = {
    "id": "D07-C01",
    "domain": "D07",
    "roles": ["deployer"],
    "tiers": {"T1": "recommended"},
    "verification": {
        "method": "emitted",
        "planes": ["control", "data"],
        "freshness": {"T1": "P90D"},
    },
    "crosswalk": {},
}


def test_fabrication_blocks_even_on_a_merely_recommended_control():
    """Section 12.3: a contradiction means the evidence cannot be trusted.

    Obligation level governs whether a shortfall degrades the lease. It does not
    govern whether a lie counts as a lie.
    """
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=184203, decisions_total=0),
    ], catalog=[RECOMMENDED_EMITTED], tier="T1")
    result = next(r for r in out.results if r.control_id == "D07-C01")
    assert result.obligation == "recommended"
    assert result.disqualifying is True
    assert result.blocks is True
    assert out.conformant is False
    assert out.lease_state == "revoked"


def test_an_ordinary_shortfall_on_a_recommended_control_does_not_block():
    out = run([], catalog=[RECOMMENDED_EMITTED], tier="T1")
    result = next(r for r in out.results if r.control_id == "D07-C01")
    assert result.status == FAIL
    assert result.disqualifying is False
    assert result.blocks is False
    assert out.conformant is True


def test_revoked_takes_precedence_over_stale():
    out = run([
        rec("D07-C01", "control", 200, enabled=True),
        rec("D07-C01", "data", 200, traffic_requests=10, decisions_total=0),
    ], catalog=[RECOMMENDED_EMITTED], tier="T1")
    assert out.lease_state == "revoked"


# --- D19-C01: an unsigned record is treated as absent, from T3 --------------


def test_unsigned_evidence_is_admissible_below_t3():
    catalog = [{**EMITTED, "tiers": {"T2": "required"},
                "verification": {**EMITTED["verification"],
                                 "freshness": {"T2": "P30D"}}}]
    out = run([
        rec("D07-C01", "control", scheme=None, verified=False, enabled=True),
        rec("D07-C01", "data", scheme=None, verified=False,
            traffic_requests=5, decisions_total=5),
    ], catalog=catalog, tier="T2")
    assert _status(out, "D07-C01") == PASS


def test_unsigned_evidence_is_treated_as_absent_at_t3():
    out = run([
        rec("D07-C01", "control", scheme=None, verified=False, enabled=True),
        rec("D07-C01", "data", scheme=None, verified=False,
            traffic_requests=5, decisions_total=5),
    ], catalog=[EMITTED])
    assert _status(out, "D07-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D07-C01")
    assert "no admissible evidence" in detail
    assert "unsigned" in detail


def test_digest_signed_evidence_is_inadmissible_at_t3():
    """A digest proves the record is intact, not who produced it."""
    out = run([
        rec("D07-C01", "control", scheme=DIGEST, enabled=True),
        rec("D07-C01", "data", scheme=DIGEST, traffic_requests=5, decisions_total=5),
    ], catalog=[EMITTED])
    assert _status(out, "D07-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D07-C01")
    assert "not who produced it" in detail


def test_a_failed_signature_says_the_record_was_altered():
    """Signed but unchecked is not the same as signed and checked."""
    out = run([
        rec("D07-C01", "control", verified=False, enabled=True),
        rec("D07-C01", "data", verified=False, traffic_requests=5, decisions_total=5),
    ], catalog=[EMITTED])
    assert _status(out, "D07-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D07-C01")
    assert "altered after it was signed" in detail


def test_a_missing_key_says_so_rather_than_blaming_the_record():
    """Two different problems with two different remedies.

    Telling somebody to supply a key they already supplied sends them the wrong
    way at exactly the moment that matters.
    """
    out = run([
        rec("D07-C01", "control", verified=False, key_known=False, enabled=True),
        rec("D07-C01", "data", verified=False, key_known=False,
            traffic_requests=5, decisions_total=5),
    ], catalog=[EMITTED])
    detail = next(r.detail for r in out.results if r.control_id == "D07-C01")
    assert "no public key available" in detail
    assert "altered" not in detail


def test_an_inadmissible_record_cannot_supply_a_contradiction_either():
    """A record that does not count as evidence does not count against you."""
    out = run([
        rec("D07-C01", "control", scheme=None, verified=False, enabled=True),
        rec("D07-C01", "data", scheme=None, verified=False,
            traffic_requests=100, decisions_total=0),
    ], catalog=[EMITTED])
    result = next(r for r in out.results if r.control_id == "D07-C01")
    assert result.status == FAIL
    assert result.disqualifying is False
