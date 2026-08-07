"""Signing schemes for evidence and conformance statements.

Signing is pluggable on purpose. A standard that hardcodes one algorithm ages
badly, and organisations arrive with key management they already run.

Two schemes ship. They are not equivalent and the difference is enforced rather
than documented:

  sha256-digest  Integrity only. Detects accidental corruption and nothing else.
                 Anybody can produce a valid digest, so it proves nothing about
                 who produced a record. Adequate for local development, and
                 REJECTED at T3 and above.

  ed25519        Integrity and authenticity. Requires the optional `cryptography`
                 extra. This is what a conformance statement anyone else is
                 expected to rely on must carry.

Calling a digest a signature would be the exact species of dishonesty D19
exists to prevent, so the capability is a property of the scheme and the tier
gate reads it.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from openaisf.errors import ValidationError

DIGEST = "sha256-digest"
ED25519 = "ed25519"

#: Schemes that establish who produced an artefact, not merely that it is intact.
AUTHENTIC_SCHEMES = frozenset({ED25519})

#: Tiers at which a scheme without authenticity is not acceptable.
AUTHENTICITY_REQUIRED_FROM = ("T3", "T4")


def canonical(payload: dict) -> bytes:
    """Deterministic bytes for a payload, so a signature is reproducible.

    Sorted keys, no insignificant whitespace, UTF-8. Any signing scheme signs
    exactly these bytes, which is what lets a verifier recompute them from the
    parsed document rather than having to preserve the original file.
    """
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


@dataclass(frozen=True)
class Signature:
    scheme: str
    value: str
    key_id: str | None = None

    @property
    def provides_authenticity(self) -> bool:
        return self.scheme in AUTHENTIC_SCHEMES

    def to_dict(self) -> dict:
        out = {"scheme": self.scheme, "value": self.value}
        if self.key_id:
            out["key_id"] = self.key_id
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "Signature":
        return cls(
            scheme=data["scheme"], value=data["value"], key_id=data.get("key_id")
        )


class Signer(Protocol):
    scheme: str

    def sign(self, payload: dict) -> Signature: ...


class DigestSigner:
    """Integrity only. Deliberately not called a signature anywhere it matters."""

    scheme = DIGEST

    def __init__(self, key_id: str = "unkeyed") -> None:
        self.key_id = key_id

    def sign(self, payload: dict) -> Signature:
        return Signature(
            scheme=DIGEST,
            value=hashlib.sha256(canonical(payload)).hexdigest(),
            key_id=self.key_id,
        )


class Ed25519Signer:
    """Real asymmetric signing. Requires the optional `cryptography` extra."""

    scheme = ED25519

    def __init__(self, private_key_pem: bytes, key_id: str) -> None:
        try:
            from cryptography.hazmat.primitives import serialization
        except ImportError as exc:  # pragma: no cover - exercised by extras
            raise ValidationError(
                "ed25519 signing requires the optional dependency: "
                "pip install 'openaisf[signing]'"
            ) from exc
        self._key = serialization.load_pem_private_key(private_key_pem, password=None)
        self.key_id = key_id

    def sign(self, payload: dict) -> Signature:
        return Signature(
            scheme=ED25519,
            value=self._key.sign(canonical(payload)).hex(),
            key_id=self.key_id,
        )


def verify(payload: dict, signature: Signature, public_key_pem: bytes | None = None) -> bool:
    """Verify a signature over a payload.

    A digest verifies against itself and establishes nothing about origin. An
    ed25519 signature requires the public key, and refusing to verify without
    one is deliberate: silently degrading to an integrity check when the key is
    missing would let an unauthenticated statement pass as an authenticated one.
    """
    if signature.scheme == DIGEST:
        return hashlib.sha256(canonical(payload)).hexdigest() == signature.value

    if signature.scheme == ED25519:
        if public_key_pem is None:
            raise ValidationError(
                "ed25519 verification requires the signer's public key; "
                "refusing to fall back to an integrity-only check"
            )
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives import serialization
        except ImportError as exc:  # pragma: no cover
            raise ValidationError(
                "ed25519 verification requires the optional dependency: "
                "pip install 'openaisf[signing]'"
            ) from exc
        key = serialization.load_pem_public_key(public_key_pem)
        try:
            key.verify(bytes.fromhex(signature.value), canonical(payload))
        except (InvalidSignature, ValueError):
            return False
        return True

    raise ValidationError(f"unknown signature scheme {signature.scheme!r}")


def require_authenticity(signature: Signature, tier: str) -> None:
    """Enforce the tier gate on signing strength."""
    if tier in AUTHENTICITY_REQUIRED_FROM and not signature.provides_authenticity:
        raise ValidationError(
            f"{tier} requires a signature scheme that establishes authenticity. "
            f"{signature.scheme!r} proves only that the payload is intact, which "
            f"anyone can produce for any payload."
        )
