"""The package version must report the standard it actually ships.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

import re
import tomllib
from pathlib import Path

import openaisf
from openaisf.mcp import SERVER_VERSION

ROOT = Path(__file__).resolve().parent.parent


def test_package_version_is_the_latest_release_everywhere():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]

    assert openaisf.__version__ == version
    assert SERVER_VERSION == version

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    latest = re.search(r"^## (v[0-9]+\.[0-9]+\.[0-9]+(?:a[0-9]+|b[0-9]+|rc[0-9]+)?)\b", changelog, re.MULTILINE)
    assert latest is not None, "no version heading found in CHANGELOG.md"
    assert latest.group(1).lstrip("v") == version, (
        f"package version {version} does not match the changelog's latest "
        f"release {latest.group(1)}"
    )