"""Decide whether a system is conformant, and for how much longer.

Three rules carry most of the weight here, and each exists because of a
specific way conformance goes wrong:

  Missing signal is failure, not silence. A control whose required evidence was
  never produced fails. Treating absence as an absence of contradiction would
  pass a system whose pipeline stopped emitting anything at all, because a
  perfectly compliant system and a completely broken one produce the same
  silence. (D14-C04.)

  Declared policy is checked against observed enforcement. A control plane
  claiming a policy is enabled while the data plane shows live traffic and zero
  decisions is a contradiction a machine settles, with no auditor in the room,
  and it MUST NOT be resolvable by attestation. (D19-C03.)

  Freshness is per control and capped by tier. Conformance is a state with a
  heartbeat: past its window a control goes stale, and past grace the lease
  expires without anybody deciding it should.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from openaisf.duration import parse_duration
from openaisf.errors import ValidationError
from openaisf.evidence import CONTROL_PLANE, DATA_PLANE, EvidenceRecord
from openaisf.soa import APPLIES, EXCLUDED, INHERITED, NOT_APPLICABLE, SoA

PASS = "pass"
FAIL = "fail"
STALE = "stale"
MANUAL = "manual"
INHERITED_OK = "inherited"
EXCLUDED_OK = "excluded"
NA = "not_applicable"

BLOCKING = frozenset({FAIL, STALE, MANUAL})

#: Grace beyond the freshness window before a lease expires rather than merely
#: going stale. Generous at T1 because pipelines break and honest systems have
#: outages; short at T4 because that is what the tier means.
GRACE = {
    "T1": timedelta(days=30),
    "T2": timedelta(days=14),
    "T3": timedelta(days=3),
    "T4": timedelta(hours=12),
}

VALID = "valid"
LEASE_STALE = "stale"
EXPIRED = "expired"
FAILING = "failing"
REVOKED = "revoked"


@dataclass(frozen=True)
class ControlResult:
    control_id: str
    status: str
    detail: str
    obligation: str | None = None
    planes_required: tuple[str, ...] = ()
    planes_present: tuple[str, ...] = ()
    age_seconds: float | None = None
    window_seconds: float | None = None
    disqualifying: bool = False

    @property
    def blocks(self) -> bool:
        """Disqualifying failures block whatever the obligation says.

        Architecture section 12.3: most control failures degrade the lease, but
        a defined few revoke it, because they mean the evidence itself cannot be
        trusted. A contradiction between a declared policy and the telemetry for
        that policy is fabrication, and fabrication on a merely recommended
        control is still fabrication.
        """
        if self.disqualifying:
            return True
        return self.obligation == "required" and self.status in BLOCKING


@dataclass(frozen=True)
class ConformanceRun:
    system_id: str
    tier: str
    evaluated_at: datetime
    results: tuple[ControlResult, ...]

    def of(self, status: str) -> tuple[ControlResult, ...]:
        return tuple(r for r in self.results if r.status == status)

    @property
    def blocking(self) -> tuple[ControlResult, ...]:
        return tuple(r for r in self.results if r.blocks)

    @property
    def conformant(self) -> bool:
        return not self.blocking

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for result in self.results:
            out[result.status] = out.get(result.status, 0) + 1
        return out

    @property
    def lease_state(self) -> str:
        """revoked, failing, expired, stale or valid, in that precedence.

        Staleness and failure are different conditions and are reported
        differently. A system whose evidence is late is not the same as one
        whose evidence contradicts itself, and collapsing them would hide the
        distinction that matters most during an incident.
        """
        if any(r.disqualifying for r in self.results):
            return REVOKED

        hard = [r for r in self.blocking if r.status in (FAIL, MANUAL)]
        if hard:
            return FAILING

        grace = GRACE.get(self.tier, timedelta(days=7))
        worst_overrun = timedelta(0)
        for result in self.blocking:
            if result.status != STALE:
                continue
            if result.age_seconds is None or result.window_seconds is None:
                continue
            overrun = timedelta(seconds=result.age_seconds - result.window_seconds)
            worst_overrun = max(worst_overrun, overrun)

        if worst_overrun > grace:
            return EXPIRED
        if worst_overrun > timedelta(0):
            return LEASE_STALE
        return VALID


def _freshness_for(control: dict, tier: str) -> timedelta | None:
    windows = (control.get("verification") or {}).get("freshness") or {}
    text = windows.get(tier)
    return parse_duration(text) if text else None


#: Tiers at which D19-C01 is required rather than recommended, and therefore
#: the tiers at which an unsigned record is treated as absent.
SIGNING_REQUIRED_FROM = ("T3", "T4")


def inadmissible(record: EvidenceRecord, tier: str) -> str | None:
    """Why a record cannot count as evidence at this tier, or None.

    D19-C01: a record that arrives unsigned, or signed by something other than
    the producer, MUST be treated as absent rather than as evidence. The
    obligation is itself tier-gated — recommended at T2, required from T3 — so
    the gate follows the control rather than being stricter than it.
    """
    if tier not in SIGNING_REQUIRED_FROM:
        return None
    if record.signature is None:
        return "unsigned"
    if not record.signature.provides_authenticity:
        return (
            f"signed with {record.signature.scheme}, which proves the record is "
            f"intact but not who produced it"
        )
    if not record.verified:
        who = record.signature.key_id or "an unnamed key"
        if not record.key_known:
            return f"no public key available for {who}; supply it to verify"
        return (
            f"signature by {who} does not verify — the record was altered "
            f"after it was signed"
        )
    return None


def _admissible(
    records: list[EvidenceRecord] | None, tier: str
) -> tuple[list[EvidenceRecord], str | None]:
    """Records that count as evidence, and why any were discarded."""
    if not records:
        return [], None
    usable = [r for r in records if inadmissible(r, tier) is None]
    if usable:
        return usable, None
    return [], inadmissible(records[0], tier)


def _newest(records: list[EvidenceRecord] | None) -> EvidenceRecord | None:
    return records[0] if records else None


def _contradiction(
    control_record: EvidenceRecord | None, data_record: EvidenceRecord | None
) -> str | None:
    """The D19-C03 rule, stated generically over the reserved observation keys."""
    if control_record is None or data_record is None:
        return None
    if control_record.enabled is not True:
        return None
    traffic = data_record.traffic_requests
    decisions = data_record.decisions_total
    if traffic is None or decisions is None:
        return None
    if traffic > 0 and decisions == 0:
        return (
            f"declared enabled, but {traffic} requests crossed the enforcement "
            f"point with 0 decisions recorded. A policy that never fired under "
            f"live traffic was not operating."
        )
    if traffic == 0 and decisions > 0:
        return (
            f"declared enabled, but {decisions} decisions were recorded with "
            f"0 requests crossing the enforcement point. Decisions with no "
            f"traffic could not have been produced by that point."
        )
    return None


def _evaluate_emitted(
    control: dict,
    obligation: str,
    tier: str,
    planes: dict[str, list[EvidenceRecord]],
    now: datetime,
) -> ControlResult:
    control_id = control["id"]
    verification = control["verification"]
    required = tuple(verification.get("planes") or (CONTROL_PLANE,))
    window = _freshness_for(control, tier)

    present: list[str] = []
    ages: dict[str, float] = {}
    missing: list[str] = []
    stale: list[str] = []
    discarded: dict[str, str] = {}

    for plane in required:
        usable, reason = _admissible(planes.get(plane), tier)
        if reason:
            discarded[plane] = reason
        record = _newest(usable)
        if record is None:
            missing.append(plane)
            continue
        present.append(plane)
        age = (now - record.window_to).total_seconds()
        ages[plane] = age
        if window is not None and age > window.total_seconds():
            stale.append(plane)

    common = dict(
        control_id=control_id,
        obligation=obligation,
        planes_required=required,
        planes_present=tuple(present),
        window_seconds=window.total_seconds() if window else None,
        age_seconds=max(ages.values()) if ages else None,
    )

    if missing:
        rejected = "; ".join(
            f"{plane} plane record rejected: {why}"
            for plane, why in discarded.items()
        )
        detail = (
            f"no admissible evidence on the {', '.join(missing)} plane. A "
            f"required signal that was never produced fails; silence is not a "
            f"pass."
        )
        if rejected:
            detail += f" ({rejected})"
        return ControlResult(status=FAIL, detail=detail, **common)

    contradiction = _contradiction(
        _newest(_admissible(planes.get(CONTROL_PLANE), tier)[0]),
        _newest(_admissible(planes.get(DATA_PLANE), tier)[0]),
    )
    if contradiction:
        return ControlResult(
            status=FAIL, detail=contradiction, disqualifying=True, **common
        )

    if stale:
        return ControlResult(
            status=STALE,
            detail=(
                f"evidence on the {', '.join(stale)} plane is older than the "
                f"{tier} freshness window"
            ),
            **common,
        )

    return ControlResult(status=PASS, detail="within freshness on every plane", **common)


def _evaluate_declared(
    control: dict,
    obligation: str,
    tier: str,
    planes: dict[str, list[EvidenceRecord]],
    now: datetime,
    method: str,
) -> ControlResult:
    """asserted and attested controls: a signed statement, consistency-checked."""
    control_id = control["id"]
    window = _freshness_for(control, tier)
    usable, rejected = _admissible(planes.get(CONTROL_PLANE), tier)
    record = _newest(usable)

    common = dict(
        control_id=control_id,
        obligation=obligation,
        planes_required=(CONTROL_PLANE,),
        planes_present=(CONTROL_PLANE,) if record else (),
        window_seconds=window.total_seconds() if window else None,
    )

    if record is None:
        detail = f"no admissible {method} record for this control"
        if rejected:
            detail += f" (record rejected: {rejected})"
        return ControlResult(status=FAIL, detail=detail, age_seconds=None, **common)

    age = (now - record.window_to).total_seconds()

    contradiction = _contradiction(
        record, _newest(_admissible(planes.get(DATA_PLANE), tier)[0])
    )
    if contradiction:
        return ControlResult(
            status=FAIL,
            detail=f"{contradiction} An attestation cannot resolve this.",
            age_seconds=age,
            disqualifying=True,
            **common,
        )

    if window is not None and age > window.total_seconds():
        return ControlResult(
            status=STALE,
            detail=f"{method} record is older than the {tier} freshness window",
            age_seconds=age,
            **common,
        )

    return ControlResult(
        status=PASS, detail=f"{method} record present and current",
        age_seconds=age, **common,
    )


TIER_ORDER = ("T1", "T2", "T3", "T4")


def _evaluate_inherited(entry, tier: str, now: datetime) -> ControlResult:
    """Resolve an inherited control against the upstream lease, if it is checkable.

    D17-C02: assurance decay propagates downstream. An upstream provider whose
    badge goes stale degrades every dependent within one freshness window. This
    is the property no existing framework models, and it only works if the
    downstream run actually goes and looks rather than trusting a string in a
    scoping file.
    """
    common = dict(control_id=entry.control_id, obligation=entry.obligation)
    ref = entry.upstream_ref

    if not ref:
        # An asserted inheritance. Acceptable below T3, where the whole tier is
        # self-asserted anyway; at T3 and above an unverifiable claim about
        # somebody else's conformance is not assurance.
        if tier in ("T3", "T4"):
            return ControlResult(
                status=FAIL,
                detail=(
                    f"inheritance from {entry.inherited_from} is asserted but not "
                    f"verifiable. At {tier} an inherited control must reference an "
                    f"upstream conformance statement that can be checked."
                ),
                **common,
            )
        return ControlResult(
            status=INHERITED_OK,
            detail=f"inherited from {entry.inherited_from} (asserted, not verified)",
            **common,
        )

    from openaisf.log import TransparencyLog
    from openaisf.statement import ConformanceStatement

    log = TransparencyLog(Path(ref["log"]))
    try:
        log.verify_chain()
    except ValidationError as exc:
        return ControlResult(
            status=FAIL,
            detail=f"upstream log for {entry.inherited_from} is not intact: {exc}",
            **common,
        )

    upstream_entry = log.latest_for(ref["system_id"])
    if upstream_entry is None:
        return ControlResult(
            status=FAIL,
            detail=(
                f"no conformance statement found for upstream "
                f"{ref['system_id']}; nothing is being inherited"
            ),
            **common,
        )

    statement = ConformanceStatement.from_dict(upstream_entry.statement)
    state = statement.state_at(now)

    if statement.tier in TIER_ORDER and tier in TIER_ORDER:
        if TIER_ORDER.index(statement.tier) < TIER_ORDER.index(tier):
            return ControlResult(
                status=FAIL,
                detail=(
                    f"upstream {entry.inherited_from} is verified at "
                    f"{statement.tier}; assurance cannot be laundered upward to "
                    f"{tier} through a dependency"
                ),
                **common,
            )

    if state == VALID:
        return ControlResult(
            status=INHERITED_OK,
            detail=(
                f"inherited from {entry.inherited_from}, upstream lease valid "
                f"until {statement.expires_at.isoformat()}"
            ),
            **common,
        )

    if state == LEASE_STALE:
        return ControlResult(
            status=STALE,
            detail=(
                f"upstream {entry.inherited_from} lease is stale; assurance decay "
                f"propagates downstream"
            ),
            **common,
        )

    return ControlResult(
        status=FAIL,
        detail=(
            f"upstream {entry.inherited_from} lease is {state}; this control is "
            f"no longer proven by anybody"
        ),
        disqualifying=(state == REVOKED),
        **common,
    )


def evaluate(
    controls: list[dict],
    soa: SoA,
    evidence_index: dict[str, dict[str, list[EvidenceRecord]]],
    now: datetime | None = None,
) -> ConformanceRun:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValidationError("evaluation time must be timezone-aware")

    catalog = {c["id"]: c for c in controls}
    results: list[ControlResult] = []

    for entry in soa.entries:
        control = catalog.get(entry.control_id)
        if control is None:
            raise ValidationError(
                f"{entry.control_id} is in the Statement of Applicability but "
                f"not in the catalog"
            )

        if entry.verdict == NOT_APPLICABLE:
            results.append(
                ControlResult(entry.control_id, NA, "out of scope for this system")
            )
            continue

        if entry.verdict == EXCLUDED:
            results.append(
                ControlResult(
                    entry.control_id, EXCLUDED_OK,
                    f"excluded: {entry.reason}", obligation=entry.obligation,
                )
            )
            continue

        if entry.verdict == INHERITED:
            results.append(_evaluate_inherited(entry, soa.tier, now))
            continue

        assert entry.verdict == APPLIES
        planes = evidence_index.get(entry.control_id, {})
        method = control["verification"]["method"]

        if method == "emitted":
            results.append(
                _evaluate_emitted(control, entry.obligation, soa.tier, planes, now)
            )
        elif method in ("asserted", "attested"):
            results.append(
                _evaluate_declared(
                    control, entry.obligation, soa.tier, planes, now, method
                )
            )
        else:  # assessed
            results.append(
                ControlResult(
                    entry.control_id, MANUAL,
                    "requires independent assessment by a certifier",
                    obligation=entry.obligation,
                )
            )

    return ConformanceRun(
        system_id=soa.system_id, tier=soa.tier, evaluated_at=now,
        results=tuple(results),
    )
