"""Load and index signed evidence records.

Evidence is produced by adapters at the enforcement point and signed there,
before transmission or aggregation. This module reads what they emit; it never
constructs evidence itself, because a conformance tool that can manufacture its
own evidence is not a conformance tool.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from openaisf.errors import ValidationError
from openaisf.loader import _validator
from openaisf.signing import Signature, verify

CONTROL_PLANE = "control"
DATA_PLANE = "data"


def _parse_timestamp(value: str, where: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{where}: bad timestamp {value!r}: {exc}") from exc
    if parsed.tzinfo is None:
        raise ValidationError(
            f"{where}: timestamp {value!r} has no timezone. Freshness is "
            f"decided on elapsed time, so an ambiguous clock is not acceptable."
        )
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class EvidenceRecord:
    control: str
    plane: str
    system_id: str
    window_from: datetime
    window_to: datetime
    observations: dict
    producer: str
    producer_version: str
    artefact_digest: str | None = None
    attested: bool = False
    signature: Signature | None = None
    #: True only when the signature was checked and held. An ed25519 record
    #: whose key was not supplied is signed but unverified, and the difference
    #: matters at T3 where authorship is the point.
    verified: bool = False
    #: Whether a key for this signature was available at all. "No key supplied"
    #: and "signature does not verify" are different problems with different
    #: remedies, and telling someone to supply a key they already supplied
    #: sends them the wrong way during an incident.
    key_known: bool = True
    source: str = "<memory>"

    @property
    def signed(self) -> bool:
        return self.signature is not None

    @property
    def authentic(self) -> bool:
        """Signed by a scheme that establishes who produced it, and checked."""
        return bool(
            self.signature and self.signature.provides_authenticity and self.verified
        )

    @property
    def enabled(self) -> bool | None:
        return self.observations.get("enabled")

    @property
    def traffic_requests(self) -> int | None:
        return self.observations.get("traffic_requests")

    @property
    def decisions_total(self) -> int | None:
        return self.observations.get("decisions_total")

    def age(self, now: datetime) -> timedelta:
        """How stale this record is, measured from the end of its window."""
        return now - self.window_to


def signable_payload(data: dict) -> dict:
    """The record as signed: everything except the signature block itself."""
    return {k: v for k, v in data.items() if k != "signature"}


def _from_dict(data: dict, source: str, keyring: dict[str, bytes] | None = None) -> EvidenceRecord:
    window = data["window"]
    frm = _parse_timestamp(window["from"], source)
    to = _parse_timestamp(window["to"], source)
    if to < frm:
        raise ValidationError(f"{source}: window ends before it begins")

    producer = data["producer"]

    signature = None
    verified = False
    key_known = True
    if data.get("signature"):
        signature = Signature.from_dict(data["signature"])
        payload = signable_payload(data)
        if signature.provides_authenticity:
            key = (keyring or {}).get(signature.key_id or "")
            # No key means unverified, never "assumed fine". Silently degrading
            # to an integrity check is how an unauthenticated record passes as
            # an authenticated one.
            key_known = key is not None
            verified = verify(payload, signature, key) if key else False
        else:
            verified = verify(payload, signature)

    return EvidenceRecord(
        control=data["control"],
        plane=data["plane"],
        system_id=data["subject"]["system_id"],
        window_from=frm,
        window_to=to,
        observations=data.get("observations") or {},
        producer=producer["adapter"],
        producer_version=producer["version"],
        artefact_digest=data["subject"].get("artefact_digest"),
        attested=bool(producer.get("attestation")),
        signature=signature,
        verified=verified,
        key_known=key_known,
        source=source,
    )


def load_keyring(keyring_dir: Path | None) -> dict[str, bytes]:
    """Public keys by key_id, from <key_id>.pem files."""
    if keyring_dir is None or not Path(keyring_dir).exists():
        return {}
    return {
        path.stem: path.read_bytes()
        for path in sorted(Path(keyring_dir).glob("*.pem"))
    }


def load_evidence(
    evidence_dir: Path, keyring: dict[str, bytes] | None = None
) -> list[EvidenceRecord]:
    """Read every .json evidence record under evidence_dir."""
    validator = _validator("evidence.schema.json")
    records: list[EvidenceRecord] = []

    for path in sorted(evidence_dir.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{path.name}: not valid JSON: {exc}") from exc

        entries = payload if isinstance(payload, list) else [payload]
        for index, entry in enumerate(entries):
            where = f"{path.name}[{index}]" if len(entries) > 1 else path.name
            errors = sorted(validator.iter_errors(entry), key=lambda e: list(e.path))
            if errors:
                first = errors[0]
                location = "/".join(str(p) for p in first.path) or "<root>"
                raise ValidationError(f"{where}: at {location}: {first.message}")
            records.append(_from_dict(entry, where, keyring))

    return records


def index_evidence(
    records: list[EvidenceRecord],
) -> dict[str, dict[str, list[EvidenceRecord]]]:
    """control id -> plane -> records, newest window first."""
    index: dict[str, dict[str, list[EvidenceRecord]]] = {}
    for record in records:
        index.setdefault(record.control, {}).setdefault(record.plane, []).append(record)
    for planes in index.values():
        for bucket in planes.values():
            bucket.sort(key=lambda r: r.window_to, reverse=True)
    return index
