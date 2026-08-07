"""Resolve a Statement of Applicability.

The SoA is not a document written for an auditor. It is the executable check
plan: every catalog control resolves to exactly one verdict, and the verdicts
are what a conformance run then demands evidence for.

Four verdicts, and the distinction between the first two matters:

  not_applicable  the control's own scope predicate says no. Computed, needs
                  no justification, and cannot be argued with.
  applies         in scope; this system owes evidence.
  inherited       in scope, but an upstream certified component already proves
                  it. Evidence is imported by reference.
  excluded        in scope, but the organisation excludes it and must say why.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from openaisf.applicability import SystemContext, applies_to, obligation_at_tier
from openaisf.errors import ValidationError

NOT_APPLICABLE = "not_applicable"
APPLIES = "applies"
INHERITED = "inherited"
EXCLUDED = "excluded"

ATTRIBUTION = "OpenAISF — created by Maarten Loose."


@dataclass(frozen=True)
class SoAEntry:
    control_id: str
    verdict: str
    obligation: str | None = None
    reason: str | None = None
    inherited_from: str | None = None
    #: Where the upstream lease can be checked, when the declaration says.
    #: {"log": path, "system_id": urn, "tier": "T4"}. Absent means the
    #: inheritance is asserted rather than verifiable, which D17-C02 permits
    #: only below T3.
    upstream_ref: dict | None = None


@dataclass(frozen=True)
class SoA:
    system_id: str
    tier: str
    entries: tuple[SoAEntry, ...]

    def of(self, verdict: str) -> tuple[SoAEntry, ...]:
        return tuple(e for e in self.entries if e.verdict == verdict)

    @property
    def counts(self) -> dict[str, int]:
        return {
            verdict: len(self.of(verdict))
            for verdict in (APPLIES, INHERITED, EXCLUDED, NOT_APPLICABLE)
        }

    @property
    def in_scope(self) -> int:
        """Controls this system must actually satisfy or import."""
        return len(self.of(APPLIES)) + len(self.of(INHERITED))


def load_context(path: Path) -> tuple[SystemContext, dict[str, str], dict[str, str]]:
    """Read a scoping file into a context plus its inheritance and exclusions."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValidationError(f"{path.name}: top level must be a mapping")

    if "system_id" not in data:
        raise ValidationError(f"{path.name}: system_id is required")

    inherits = data.pop("inherits", None) or {}
    exclusions = data.pop("exclusions", None) or {}
    known = {
        "system_id",
        "roles",
        "system_class",
        "autonomy",
        "data_class",
        "eu_risk",
        "labels",
    }
    unknown = set(data) - known
    if unknown:
        raise ValidationError(
            f"{path.name}: unknown scoping keys: {', '.join(sorted(unknown))}"
        )

    return SystemContext(**data), dict(inherits), dict(exclusions)


def resolve_soa(
    controls: list[dict],
    context: SystemContext,
    tier: str,
    inherits: dict[str, str] | None = None,
    exclusions: dict[str, str] | None = None,
) -> SoA:
    inherits = inherits or {}
    exclusions = exclusions or {}

    catalog_ids = {c["id"] for c in controls}
    for control_id in set(inherits) | set(exclusions):
        if control_id not in catalog_ids:
            raise ValidationError(
                f"{control_id} is declared in the scoping file but is not in the catalog"
            )

    overlap = set(inherits) & set(exclusions)
    if overlap:
        raise ValidationError(
            f"{', '.join(sorted(overlap))} is both inherited and excluded; "
            f"a control cannot be proven upstream and out of scope at once"
        )

    entries: list[SoAEntry] = []
    for control in sorted(controls, key=lambda c: c["id"]):
        control_id = control["id"]

        if not applies_to(control, context, tier):
            # Excluding something that was never in scope means the scoping
            # file is stale or the context is wrong. Either way it is a defect,
            # not a harmless leftover.
            if control_id in exclusions:
                raise ValidationError(
                    f"{control_id} is excluded but does not apply to this system "
                    f"at {tier} anyway; remove the exclusion"
                )
            if control_id in inherits:
                raise ValidationError(
                    f"{control_id} is inherited but does not apply to this system "
                    f"at {tier} anyway; remove the inheritance"
                )
            entries.append(SoAEntry(control_id, NOT_APPLICABLE))
            continue

        obligation = obligation_at_tier(control, tier)

        if control_id in inherits:
            declared = inherits[control_id]
            if isinstance(declared, dict):
                component = (declared.get("upstream") or "").strip()
                ref = {k: v for k, v in declared.items() if k != "upstream"}
            else:
                component = (declared or "").strip()
                ref = None
            if not component:
                raise ValidationError(
                    f"{control_id}: inheritance names no upstream component"
                )
            if ref and not (ref.get("log") and ref.get("system_id")):
                raise ValidationError(
                    f"{control_id}: a verifiable inheritance needs both log and "
                    f"system_id, so the upstream lease can actually be checked"
                )
            entries.append(
                SoAEntry(control_id, INHERITED, obligation,
                         inherited_from=component, upstream_ref=ref)
            )
            continue

        if control_id in exclusions:
            reason = (exclusions[control_id] or "").strip()
            if not reason:
                raise ValidationError(
                    f"{control_id}: exclusion states no reason. An exclusion "
                    f"without a reason is how a coverage report goes green "
                    f"without anything being true."
                )
            entries.append(SoAEntry(control_id, EXCLUDED, obligation, reason=reason))
            continue

        entries.append(SoAEntry(control_id, APPLIES, obligation))

    return SoA(system_id=context.system_id, tier=tier, entries=tuple(entries))


def to_document(soa: SoA) -> dict:
    """Serialisable form. not_applicable entries are summarised, not listed.

    A conformance artefact that lists several hundred controls a system does
    not have to satisfy is unreadable, and unreadable artefacts do not get read.
    """
    return {
        "openaisf_soa": "1.0",
        "attribution": ATTRIBUTION,
        "system_id": soa.system_id,
        "tier": soa.tier,
        "counts": soa.counts,
        "in_scope": soa.in_scope,
        "controls": [
            {k: v for k, v in asdict(entry).items() if v is not None}
            for entry in soa.entries
            if entry.verdict != NOT_APPLICABLE
        ],
        "not_applicable": [e.control_id for e in soa.of(NOT_APPLICABLE)],
    }


def write_soa(soa: SoA, path: Path) -> None:
    path.write_text(
        yaml.safe_dump(to_document(soa), sort_keys=False, width=88, allow_unicode=True),
        encoding="utf-8",
    )
