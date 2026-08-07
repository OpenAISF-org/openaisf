#!/usr/bin/env python3
"""Regenerate the MITRE ATLAS requirement inventory from the official dataset.

Not part of the runtime package. Requires only the standard library plus
PyYAML, which openaisf already depends on.

    python tools/gen_atlas_inventory.py

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import yaml

SOURCE_URL = (
    "https://raw.githubusercontent.com/mitre-atlas/atlas-data/"
    "main/dist/v6/ATLAS-2026.07.yaml"
)
OUT = Path(__file__).resolve().parents[1] / "spec/crosswalk/inventories/mitre_atlas.yaml"


def esc(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def collect(node, found: list[tuple[str, str, str]]) -> None:
    """ATLAS nests objects arbitrarily; walk everything."""
    if isinstance(node, dict):
        otype = node.get("object-type")
        if otype in ("technique", "tactic") and node.get("id") and node.get("name"):
            found.append((otype, str(node["id"]), str(node["name"])))
        for value in node.values():
            collect(value, found)
    elif isinstance(node, list):
        for item in node:
            collect(item, found)


def main() -> int:
    print(f"fetching {SOURCE_URL}")
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
        raw = response.read().decode("utf-8")

    data = yaml.safe_load(raw)
    found: list[tuple[str, str, str]] = []
    collect(data, found)

    seen: set[str] = set()
    techniques: list[tuple[str, str]] = []
    for otype, oid, name in found:
        if otype != "technique" or oid in seen:
            continue
        seen.add(oid)
        summary = name if len(name) >= 10 else f"{name} technique"
        techniques.append((oid, summary))
    techniques.sort()

    version = str(data.get("collection", {}).get("version") or "2026.07")

    lines = [
        "# MITRE ATLAS adversarial technique inventory.",
        "# GENERATED FILE — do not edit by hand.",
        "# Regenerate with: python tools/gen_atlas_inventory.py",
        f"# Source: {SOURCE_URL}",
        "#",
        "# COPYRIGHT POSITION. The ATLAS dataset is Copyright 2021-2026 MITRE and",
        "# is licensed under the Apache License, Version 2.0, which permits use,",
        "# reproduction and distribution with attribution and retention of the",
        "# licence notice. Technique identifiers and names are reproduced under",
        "# that licence. No endorsement by MITRE is implied.",
        "#",
        "# OpenAISF — created by Maarten Loose. Specification licensed CC-BY-4.0.",
        "regime: mitre_atlas",
        "name: MITRE ATLAS — Adversarial Threat Landscape for AI Systems",
        f'version: "{version}"',
        'source: "https://atlas.mitre.org/"',
        'licence: "Apache-2.0"',
        'licence_url: "https://www.apache.org/licenses/LICENSE-2.0"',
        "attribution: >",
        "  MITRE ATLAS, Copyright 2021-2026 MITRE, licensed under the Apache",
        "  License, Version 2.0. Technique identifiers and names are reproduced",
        "  under that licence. MITRE does not endorse OpenAISF.",
        "regime_kind: threat",
        "reproduction: descriptive",
        f"declared_total: {len(techniques)}",
        "requirements:",
    ]
    for oid, summary in techniques:
        lines.append(f"  - ref: {oid}")
        lines.append(f"    text_summary: {esc(summary)}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(techniques)} techniques")
    return 0


if __name__ == "__main__":
    sys.exit(main())
