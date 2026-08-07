"""Load and validate OpenAISF specification artefacts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from openaisf.errors import ValidationError

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"


def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys.

    PyYAML silently keeps the last value when a key repeats. In a crosswalk that
    means a second `nist_ai_rmf:` key discards every mapping under the first one,
    the coverage report drops requirements that were in fact addressed, and
    nothing anywhere reports an error. Loud failure is the only safe behaviour
    for a file whose whole purpose is to be counted.
    """


def _no_duplicate_keys(loader: yaml.Loader, node: yaml.MappingNode) -> dict:
    seen: set = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in seen:
            mark = key_node.start_mark
            raise ValidationError(
                f"duplicate key {key!r} at line {mark.line + 1}, "
                f"column {mark.column + 1}: the earlier value would be silently "
                f"discarded"
            )
        seen.add(key)
    return loader.construct_mapping(node, deep=True)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def _read_yaml(path: Path) -> dict:
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictLoader)
    except ValidationError as exc:
        raise ValidationError(f"{path.name}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValidationError(f"{path.name}: not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{path.name}: top level must be a mapping")
    return data


def load_catalog(catalog_dir: Path) -> list[dict]:
    """Load every control from every YAML file in catalog_dir.

    Raises ValidationError on schema violation or duplicate identifier.
    Returns controls sorted by id.
    """
    validator = _validator("control.schema.json")
    controls: dict[str, dict] = {}

    for path in sorted(catalog_dir.glob("*.yaml")):
        data = _read_yaml(path)
        entries = data.get("controls")
        if not isinstance(entries, list):
            raise ValidationError(f"{path.name}: missing a 'controls' list")

        for entry in entries:
            errors = sorted(validator.iter_errors(entry), key=lambda e: list(e.path))
            if errors:
                first = errors[0]
                location = "/".join(str(p) for p in first.path) or "<root>"
                raise ValidationError(
                    f"{path.name}: control "
                    f"{entry.get('id', '<no id>')} at {location}: {first.message}"
                )

            control_id = entry["id"]
            if control_id in controls:
                raise ValidationError(
                    f"{path.name}: duplicate control identifier {control_id}"
                )
            if not control_id.startswith(entry["domain"]):
                raise ValidationError(
                    f"{path.name}: control {control_id} declares domain "
                    f"{entry['domain']} which does not match its identifier"
                )
            controls[control_id] = entry

    ordered = [controls[k] for k in sorted(controls)]
    check_invariants(ordered)
    return ordered


def load_inventories(inventory_dir: Path) -> dict[str, dict]:
    """Load external requirement inventories, keyed by regime slug.

    declared_total is a deliberate redundancy: it is the published count for
    the regime (ISO 42001 has 38 Annex A controls, NIST AI RMF has 72
    subcategories). If transcription drifts from the published figure the
    load fails, which is the only cheap defence against a silently incomplete
    inventory producing a falsely complete coverage report.
    """
    validator = _validator("inventory.schema.json")
    inventories: dict[str, dict] = {}

    for path in sorted(inventory_dir.glob("*.yaml")):
        data = _read_yaml(path)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if errors:
            first = errors[0]
            location = "/".join(str(p) for p in first.path) or "<root>"
            raise ValidationError(f"{path.name}: at {location}: {first.message}")

        regime = data["regime"]
        if regime in inventories:
            raise ValidationError(f"{path.name}: regime {regime} already defined")

        seen: set[str] = set()
        for requirement in data["requirements"]:
            ref = requirement["ref"]
            if ref in seen:
                raise ValidationError(
                    f"{path.name}: duplicate requirement reference {ref}"
                )
            seen.add(ref)

        declared = data.get("declared_total")
        actual = len(data["requirements"])
        if declared is not None and declared != actual:
            raise ValidationError(
                f"{path.name}: declares {declared} requirements but contains {actual}"
            )

        data.setdefault("declared_total", None)
        inventories[regime] = data

    return inventories


def check_invariants(controls: list[dict]) -> None:
    """Enforce catalog rules that JSON Schema cannot express.

    1. An emitted control must name at least one evidence source.
    2. Every declared verification plane must have an evidence source.
    3. Every tier where an emitted control is required must have a freshness
       window, otherwise the conformance lease has no expiry and the control
       silently never goes stale.
    """
    for control in controls:
        verification = control["verification"]
        if verification["method"] != "emitted":
            continue

        control_id = control["id"]
        evidence = control.get("evidence") or []
        if not evidence:
            raise ValidationError(
                f"{control_id}: emitted controls must declare at least one "
                f"evidence source"
            )

        supplied = {item["plane"] for item in evidence}
        for plane in verification.get("planes", []):
            if plane not in supplied:
                raise ValidationError(
                    f"{control_id}: no evidence source for plane '{plane}'"
                )

        freshness = verification.get("freshness") or {}
        for tier, obligation in control["tiers"].items():
            if obligation == "required" and tier not in freshness:
                raise ValidationError(
                    f"{control_id}: required at {tier} but declares no "
                    f"freshness window for tier {tier}"
                )
