# Plan 001: Make the package version report the live standard (1.0.0a2)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 9424806..HEAD -- pyproject.toml src/openaisf/__init__.py src/openaisf/mcp.py CHANGELOG.md tests/`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `9424806`, 2026-08-19
- **Issue**: (none)

## Why this matters

The repository ships the v1.0.0a2 standard — the catalog has 118 controls, the
changelog's newest release is v1.0.0a2 — but every place the software reports
its own version says `1.0.0a1`. Anyone who installs `openaisf`, imports
`openaisf.__version__`, or reads the MCP server's `serverInfo` is told they are
on a1 when they are on a2. For a conformance standard whose version number is
part of the trust surface, a stale version is a real defect: consumers and CI
pipeline labels will disagree with the artifact. This plan makes the three
version touchpoints agree with each other and with the changelog, and adds a
test that keeps them agreeing forever.

## Current state

- `pyproject.toml` (line 3): `version = "1.0.0a1"`
- `src/openaisf/__init__.py` (line 7): `__version__ = "1.0.0a1"`
- `src/openaisf/mcp.py` (line 63): `SERVER_VERSION = "1.0.0a1"`
- `CHANGELOG.md`: the file's first `## v` heading is `## v1.0.0a1 — 7 August
  2026` (line 5); the `## v1.0.0a2 — 7 August 2026` section (lines 109–135)
  sits below it, followed by `## v0.1 — August 2026`. The changelog is not
  newest-first.

Repo conventions that apply:

- Version-bearing code lives in three independent places; there is no single
  source of truth yet. This plan introduces a test instead of an import-time
  coupling, which keeps `mcp.py` stdlib-only (its build constraint) and keeps
  setuptools static metadata (no dynamic-version machinery).
- Tests live in `tests/`, are pytest, and follow the pattern in
  `tests/test_soa_size.py` / `tests/test_invariants.py`: a module docstring,
  plain `assert`s, no mocking framework.
- Python floor is 3.11, so `tomllib` (stdlib) is available for parsing
  `pyproject.toml` in tests. Do not add `tomli` as a dependency.

## Commands you will need

| Purpose   | Command                                    | Expected on success |
|-----------|--------------------------------------------|---------------------|
| Tests     | `./.venv/bin/python -m pytest -q`          | 173+ passed, exit 0 |
| Coverage  | `./.venv/bin/python -m openaisf.cli coverage` | exit 0           |

Note: on this machine the repo sits on a slow external volume and a full
pytest run takes roughly two minutes. That is environmental; let it finish.

## Scope

**In scope** (the only files you should modify):
- `pyproject.toml`
- `src/openaisf/__init__.py`
- `src/openaisf/mcp.py`
- `CHANGELOG.md`
- `tests/test_version_consistency.py` (create)

**Out of scope** (do NOT touch, even though they look related):
- `src/openaisf/mcp.py` `SUPPORTED_VERSIONS` / `LATEST_VERSION` (lines 66–67) —
  these are wire-protocol versions, not package versions.
- `tools/adapters/gateway_adapter.py` `VERSION = "1.0.0"` — the adapter's
  producer version written into evidence records, not the package version.
- `schema/` files — `"openaisf_evidence": "1.0"` etc. are artefact-format
  versions.
- Any new dependency in `pyproject.toml`.

## Git workflow

- Branch: `advisor/001-version-sync` (or your repo's branch convention).
- Commit per step; message style matches `git log` (conventional commits):
  `fix: version metadata reports the live 1.0.0a2 standard`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Bump the three version touchpoints to `1.0.0a2`

- `pyproject.toml` line 3: `version = "1.0.0a2"`
- `src/openaisf/__init__.py` line 7: `__version__ = "1.0.0a2"`
- `src/openaisf/mcp.py` line 63: `SERVER_VERSION = "1.0.0a2"`

**Verify**: `grep -n '1\.0\.0a2' pyproject.toml src/openaisf/__init__.py src/openaisf/mcp.py`
→ three hits, one per file, and `grep -rn '1\.0\.0a1' pyproject.toml src/` → no matches.

### Step 2: Make the changelog newest-first

Move the entire `## v1.0.0a2 — 7 August 2026` section (currently lines
109–135, ending with the blank line before `## v0.1`) so it sits immediately
after the attribution line `**OpenAISF — created by Maarten Loose.**` (line 3),
i.e. directly above the `## v1.0.0a1` section. Do not change any wording inside
the sections. The resulting heading order must be: `v1.0.0a2`, `v1.0.0a1`,
`v0.1`.

**Verify**: `grep -n '^## ' CHANGELOG.md` → first match is `## v1.0.0a2`.

### Step 3: Add the version-consistency test

Create `tests/test_version_consistency.py`:

```python
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
    assert latest.group(1) == version, (
        f"package version {version} does not match the changelog's latest "
        f"release {latest.group(1)}"
    )
```

**Verify**: `./.venv/bin/python -m pytest tests/test_version_consistency.py -q`
→ 1 passed, exit 0. (Note: pytest startup is slow on this volume; give it up
to two minutes.)

## Test plan

- New file `tests/test_version_consistency.py` with one test asserting that
  `pyproject.toml`, `openaisf.__version__`, `mcp.SERVER_VERSION`, and the
  changelog's newest heading all equal `1.0.0a2`.
- Structural pattern: `tests/test_soa_size.py` (module docstring, plain
  asserts, `Path(__file__)` root derivation).
- Verification: `./.venv/bin/python -m pytest -q` → all pass (172 existing +
  1 new = 173), exit 0.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pyproject.toml`, `src/openaisf/__init__.py`, `src/openaisf/mcp.py` all contain `1.0.0a2` and none contain `1.0.0a1`
- [ ] `grep -n '^## ' CHANGELOG.md` lists `v1.0.0a2` first
- [ ] `./.venv/bin/python -m pytest tests/test_version_consistency.py -q` → 1 passed
- [ ] `./.venv/bin/python -m pytest -q` → 173 passed, exit 0
- [ ] `./.venv/bin/python -m openaisf.cli coverage` → exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written).
- `CHANGELOG.md` no longer contains a `## v1.0.0a2` section to reorder.
- A verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- When the next standard version is cut, the change is now mechanical: bump the
  three touchpoints, add the changelog section at the top, and
  `tests/test_version_consistency.py` enforces that all four agree.
- If a future change wants a single source of truth (e.g. import-time dynamic
  version), it must preserve the stdlib-only constraint on `mcp.py` — a shared
  `_version.py` imported by both packages is fine; reading `tomllib` at import
  time in `mcp.py` is not.
- A reviewer should confirm the changelog reorder is move-only (no wording
  edits) and that protocol/format versions (`SUPPORTED_VERSIONS`,
  `openaisf_evidence: "1.0"`) were not touched.