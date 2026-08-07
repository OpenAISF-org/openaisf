"""The conformance statement: the signed artefact a relying party consumes.

A statement is not evidence. Evidence stays with the subject, often containing
prompts and traces that must not leave the boundary. What travels is the claim,
its scope, its results in summary, and — the part that matters — the two
deadlines at which the claim goes stale and then expires.

Carrying the deadlines in the statement is what makes verification independent.
A relying party does not need the catalog, the evidence, the subject's
cooperation or a registry to answer "is this still true?". They need the
statement, the signer's key, and a clock.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from openaisf.check import EXPIRED, GRACE, LEASE_STALE, REVOKED, VALID, ConformanceRun
from openaisf.errors import ValidationError
from openaisf.signing import Signature, canonical, require_authenticity, verify
from openaisf.soa import SoA, to_document

STATEMENT_VERSION = "1.0"
ATTRIBUTION = "OpenAISF — created by Maarten Loose."

#: However fresh the evidence, no lease outlives this. Certification lapses by
#: physics: a subject cannot construct a statement that never needs renewing.
MAX_LEASE = {
    "T1": timedelta(days=365),
    "T2": timedelta(days=180),
    "T3": timedelta(days=90),
    "T4": timedelta(days=30),
}


def digest(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical(payload)).hexdigest()


@dataclass(frozen=True)
class ConformanceStatement:
    system_id: str
    tier: str
    issued_at: datetime
    stale_after: datetime
    expires_at: datetime
    conformant: bool
    soa_digest: str
    counts: dict
    blocking: tuple[str, ...]
    inherits: tuple[dict, ...] = ()
    signature: Signature | None = None

    def payload(self) -> dict:
        """Exactly what gets signed. The signature is never part of it."""
        return {
            "openaisf_statement": STATEMENT_VERSION,
            "attribution": ATTRIBUTION,
            "system_id": self.system_id,
            "tier": self.tier,
            "issued_at": self.issued_at.isoformat(),
            "stale_after": self.stale_after.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "conformant": self.conformant,
            "soa_digest": self.soa_digest,
            "counts": self.counts,
            "blocking": list(self.blocking),
            "inherits": [dict(i) for i in self.inherits],
        }

    def to_dict(self) -> dict:
        out = self.payload()
        if self.signature:
            out["signature"] = self.signature.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "ConformanceStatement":
        if data.get("openaisf_statement") != STATEMENT_VERSION:
            raise ValidationError(
                f"unsupported statement version "
                f"{data.get('openaisf_statement')!r}"
            )
        sig = data.get("signature")
        return cls(
            system_id=data["system_id"],
            tier=data["tier"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
            stale_after=datetime.fromisoformat(data["stale_after"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            conformant=data["conformant"],
            soa_digest=data["soa_digest"],
            counts=data["counts"],
            blocking=tuple(data.get("blocking") or ()),
            inherits=tuple(data.get("inherits") or ()),
            signature=Signature.from_dict(sig) if sig else None,
        )

    def state_at(self, now: datetime) -> str:
        """Render the lease state at the moment somebody looks.

        This is the whole mechanism. A badge is not a stored value; it is this
        function evaluated against the reader's clock. A statement issued valid
        goes stale and then expires in somebody else's README with nobody
        notified and nobody able to prevent it.
        """
        if not self.conformant:
            return REVOKED if self.blocking else EXPIRED
        if now >= self.expires_at:
            return EXPIRED
        if now >= self.stale_after:
            return LEASE_STALE
        return VALID


def _deadlines(run: ConformanceRun) -> tuple[datetime, datetime]:
    """When the freshest possible reading of this run stops being current."""
    soonest: datetime | None = None
    for result in run.results:
        if result.obligation != "required":
            continue
        if result.window_seconds is None or result.age_seconds is None:
            continue
        remaining = result.window_seconds - result.age_seconds
        deadline = run.evaluated_at + timedelta(seconds=remaining)
        soonest = deadline if soonest is None else min(soonest, deadline)

    ceiling = run.evaluated_at + MAX_LEASE.get(run.tier, timedelta(days=90))
    stale_after = min(soonest, ceiling) if soonest else ceiling
    expires_at = stale_after + GRACE.get(run.tier, timedelta(days=7))
    return stale_after, expires_at


def build_statement(run: ConformanceRun, soa: SoA) -> ConformanceStatement:
    stale_after, expires_at = _deadlines(run)
    return ConformanceStatement(
        system_id=run.system_id,
        tier=run.tier,
        issued_at=run.evaluated_at,
        stale_after=stale_after,
        expires_at=expires_at,
        conformant=run.conformant,
        soa_digest=digest(to_document(soa)),
        counts=run.counts,
        blocking=tuple(sorted(r.control_id for r in run.blocking)),
        inherits=tuple(
            {"control": e.control_id, "upstream": e.inherited_from}
            for e in soa.entries
            if e.inherited_from
        ),
    )


def sign_statement(statement: ConformanceStatement, signer) -> ConformanceStatement:
    signature = signer.sign(statement.payload())
    require_authenticity(signature, statement.tier)
    return ConformanceStatement(
        **{
            **{k: getattr(statement, k) for k in statement.__dataclass_fields__},
            "signature": signature,
        }
    )


def verify_statement(
    statement: ConformanceStatement, public_key_pem: bytes | None = None
) -> bool:
    if statement.signature is None:
        raise ValidationError("statement carries no signature")
    return verify(statement.payload(), statement.signature, public_key_pem)
