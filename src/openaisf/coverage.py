"""Compute provable crosswalk coverage.

Iteration is over the external requirement inventories, never over the
controls. Mapping outward from controls can only ever show what was found;
mapping inward from requirements shows what was missed, which is the only
direction that supports a superset claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from openaisf.errors import ValidationError

COVERED = "covered"
EXCLUDED = "excluded"
UNCOVERED = "uncovered"


@dataclass(frozen=True)
class RequirementStatus:
    regime: str
    ref: str
    status: str
    controls: tuple[str, ...]
    reason: str | None


@dataclass(frozen=True)
class RegimeCoverage:
    regime: str
    name: str
    total: int
    covered: int
    excluded: int
    uncovered: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return not self.uncovered


def load_exclusions(path: Path) -> dict[str, dict[str, str]]:
    """Load regime -> ref -> reason. A missing file means no exclusions."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    result: dict[str, dict[str, str]] = {}
    for regime, entries in data.items():
        if regime.startswith("_"):
            continue
        result[regime] = {}
        for entry in entries or []:
            reason = (entry.get("reason") or "").strip()
            if not reason:
                raise ValidationError(
                    f"exclusion {regime}:{entry.get('ref')} has no reason"
                )
            result[regime][entry["ref"]] = reason
    return result


FULL = "full"
PARTIAL = "partial"


def normalise_crosswalk(
    control: dict, threat: frozenset[str] = frozenset()
) -> dict[str, list[tuple[str, str]]]:
    """Return regime -> [(ref, effective_strength)], expanding the shorthand.

    A bare string reference means strength 'full': the external requirement on
    its own demands substantially what this control demands. That default is
    deliberately conservative. Originality is a public claim about the
    framework, so disclaiming it must be free and asserting it must be an
    explicit, reviewable act.

    Mappings into a threat regime resolve to 'partial' regardless, because a
    threat catalogue imposes no obligation. Declaring one explicitly full is an
    error rather than a silent downgrade, since it means the author has
    misunderstood what the mapping asserts.
    """
    result: dict[str, list[tuple[str, str]]] = {}
    for regime, refs in (control.get("crosswalk") or {}).items():
        if regime.startswith("_"):
            continue
        entries: list[tuple[str, str]] = []
        for item in refs or []:
            if isinstance(item, str):
                ref, declared = item, None
            else:
                ref, declared = item["ref"], item.get("strength")

            if regime in threat:
                if declared == FULL:
                    raise ValidationError(
                        f"{control.get('id', '<no id>')}: mapping to "
                        f"{regime}:{ref} is marked full, but {regime} is a "
                        f"threat catalogue and imposes no requirement. Mark it "
                        f"partial or omit the strength."
                    )
                entries.append((ref, PARTIAL))
            else:
                entries.append((ref, declared or FULL))
        if entries:
            result[regime] = entries
    return result


def _index_controls(
    controls: list[dict], inventories: dict[str, dict]
) -> dict[tuple[str, str], list[str]]:
    index: dict[tuple[str, str], list[str]] = {}
    valid_refs = {
        regime: {r["ref"] for r in data["requirements"]}
        for regime, data in inventories.items()
    }

    for control in controls:
        for regime, entries in normalise_crosswalk(control).items():
            if regime not in valid_refs:
                raise ValidationError(
                    f"{control['id']}: unknown regime '{regime}' in crosswalk"
                )
            for ref, _strength in entries:
                if ref not in valid_refs[regime]:
                    raise ValidationError(
                        f"{control['id']} references {regime}:{ref}, which is "
                        f"not in the {regime} inventory"
                    )
                index.setdefault((regime, ref), []).append(control["id"])

    return index


def compute_coverage(
    controls: list[dict],
    inventories: dict[str, dict],
    exclusions: dict[str, dict[str, str]],
) -> tuple[list[RegimeCoverage], list[RequirementStatus]]:
    index = _index_controls(controls, inventories)
    regimes: list[RegimeCoverage] = []
    statuses: list[RequirementStatus] = []

    for regime in sorted(inventories):
        data = inventories[regime]
        regime_exclusions = exclusions.get(regime, {})
        uncovered: list[str] = []
        covered_count = 0
        excluded_count = 0

        for requirement in data["requirements"]:
            ref = requirement["ref"]
            mapped = tuple(sorted(index.get((regime, ref), [])))
            excluded_reason = regime_exclusions.get(ref)

            if mapped and excluded_reason:
                raise ValidationError(
                    f"{regime}:{ref} is both covered and excluded — "
                    f"covered by {', '.join(mapped)}"
                )

            if mapped:
                covered_count += 1
                statuses.append(
                    RequirementStatus(regime, ref, COVERED, mapped, None)
                )
            elif excluded_reason:
                excluded_count += 1
                statuses.append(
                    RequirementStatus(regime, ref, EXCLUDED, (), excluded_reason)
                )
            else:
                uncovered.append(ref)
                statuses.append(
                    RequirementStatus(regime, ref, UNCOVERED, (), None)
                )

        regimes.append(
            RegimeCoverage(
                regime=regime,
                name=data["name"],
                total=len(data["requirements"]),
                covered=covered_count,
                excluded=excluded_count,
                uncovered=tuple(uncovered),
            )
        )

    return regimes, statuses


def threat_regimes(inventories: dict[str, dict]) -> frozenset[str]:
    """Regimes that catalogue attacks rather than impose obligations."""
    return frozenset(
        regime
        for regime, data in inventories.items()
        if data.get("regime_kind") == "threat"
    )


def compute_provenance(
    controls: list[dict], threat: frozenset[str] = frozenset()
) -> dict[str, str]:
    """Derive each control's provenance from its crosswalk, not from assertion.

    Originality is a claim about whether any incumbent already *requires* what
    this control requires. It is not a claim about how many regimes the control
    is related to. Counting regimes conflates breadth of mapping with
    derivativeness, and understates controls that touch many frameworks loosely
    while being demanded by none of them.

    So the count that matters is full-strength mappings only:

      2 or more full   adopted           multiple regimes already require this
      exactly 1 full   derived           one regime requires it
      0 full           OpenAISF-original no incumbent requirement covers it,
                                         however many partial relationships exist

    Mappings into a threat regime never count as full, whatever they declare.
    OWASP, ATLAS and MCP-38 catalogue attacks; they impose no obligations, so a
    mapping to one establishes that a control is relevant to a known attack and
    can never establish that somebody already requires it. Making that
    structural removes most of the discretion from this calculation.

    A hand-written provenance field that contradicts the computed value is an
    error rather than an override, because the published originality figure is
    a public claim and must never be hand-maintained.
    """
    result: dict[str, str] = {}

    for control in controls:
        full_mappings = sum(
            1
            for entries in normalise_crosswalk(control, threat).values()
            for _ref, strength in entries
            if strength == FULL
        )

        if full_mappings == 0:
            computed = "OpenAISF-original"
        elif full_mappings == 1:
            computed = "derived"
        else:
            computed = "adopted"

        declared = control.get("provenance")
        if declared is not None and declared != computed:
            raise ValidationError(
                f"{control['id']}: declares provenance '{declared}' but its "
                f"crosswalk computes to '{computed}'"
            )

        result[control["id"]] = computed

    return result
