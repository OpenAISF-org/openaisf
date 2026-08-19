# Plan 005: Add a CI pipeline that runs the two release gates

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 9424806..HEAD -- pyproject.toml .github/`
> If pyproject.toml changed since this plan was written, compare the extras
> below against the live file; on a mismatch, treat it as a STOP condition.
> **This plan depends on plan 001** — `tests/test_version_consistency.py`
> must exist and pass before this pipeline can go green. Execute 001 first
> (or fold 001's merge into this branch before pushing).

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plan 001 (version-consistency test must exist before the
  pipeline runs green)
- **Category**: process
- **Planned at**: commit `9424806`, 2026-08-19
- **Issue**: (none)

## Why this matters

The repository's AGENTS.md says "No CI is configured. Commit and push ... when
work is done." The two release gates (full pytest; `coverage` exiting 0) are
real, load-bearing checks — a gap in the crosswalk inventory or an
unverifiable-control change silently blocks release — but nothing runs them
automatically, so a change that breaks conformance can be pushed and only
caught by a human later. For an open standard that accepts external
contributions (CONTRIBUTING.md), a PR that runs the gates on every push is the
difference between "trust us" and "here is the evidence". This plan adds a
minimal GitHub Actions workflow that installs the package with the `dev` and
`signing` extras (the latter is required or `tests/test_inheritance.py` fails
with `ModuleNotFoundError: cryptography`), runs the full suite, and runs the
coverage gate with the exit code enforced.

## Current state

- No `.github/` directory exists (verified 2026-08-19).
- `pyproject.toml` extras (lines 8-10):

  ```toml
  [project.optional-dependencies]
  dev = ["pytest>=8.0"]
  signing = ["cryptography>=42"]
  ```

- `requires-python = ">=3.11"` (line 5), so the matrix should cover 3.11 +
  current (3.12, 3.13). Do not include 3.10 or below.
- Package install is editable from `src/` layout (`[tool.setuptools.packages.find] where = ["src"]`).
- The gates, from AGENTS.md: `./.venv/bin/python -m pytest` must pass and
  `./.venv/bin/python -m openaisf.cli coverage` must exit 0.
- Repo remote: `github.com/OpenAISF-org/openaisf`, default branch `main`.

Repo conventions that apply:

- No CI exists yet, so this is the first; keep it minimal and readable, with
  no third-party actions beyond the canonical `actions/checkout` and
  `actions/setup-python`.
- The workflow file is YAML; the repo's other YAML is strict (schemas), but
  that does not affect this file.
- Coverage output is human-readable JSON/plain text; the job must capture the
  exit code, not just echo text.

## Commands you will need

| Purpose   | Command                                    | Expected on success |
|-----------|--------------------------------------------|---------------------|
| Validate  | `./.venv/bin/python -c "import yaml, pathlib; d=yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text()); print(list(d['jobs']))"` | `['test']` |
| Coverage  | `./.venv/bin/python -m openaisf.cli coverage` | exit 0           |

## Scope

**In scope** (the only files you should create):
- `.github/workflows/ci.yml` (create, plus the `.github/workflows/` path)

**Out of scope** (do NOT touch, even though they look related):
- `pyproject.toml` — no new dependencies or tooling (do not add ruff/mypy
  gates; those are separate decisions).
- `tests/` — no changes; the pipeline runs what exists.
- `plans/` — the execution index is a working artifact, not a release gate.
- Publishing/release automation (badges to websites, PyPI upload) — future
  work, not this plan.
- Any other branch protection or merge rules — that is repo-admin, not code.

## Git workflow

- Branch: `advisor/005-ci` (or the repo's branch convention).
- Create the file, validate it, commit once with a message matching `git log`
  style (conventional commits): `ci: run the pytest and coverage release gates on every push`.
- Do NOT push or open a PR unless the operator instructed it — the file takes
  effect on push to `main` or a PR, so pushing is the activation step and is
  gated on the operator's approval.

## Steps

### Step 1: Create the workflow file

Create `.github/workflows/ci.yml` with exactly this content (adjusted only if
the repo's YAML style demands it):

```yaml
name: release-gates

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -e '.[dev,signing]'

      - name: Test suite
        run: python -m pytest

      - name: Coverage gate
        run: python -m openaisf.cli coverage
```

Notes:

- The `signing` extra is non-negotiable: without it, `tests/test_inheritance.py`
  (6 tests) fails with `ModuleNotFoundError: cryptography`. Both gates in one
  job on one matrix keeps this obvious.
- The matrix runs 3.11, 3.12 and 3.13. If a runner's default Python matches,
  setup-python handles it; the explicit versions keep the guarantee.
- No `timeout-minutes` yet — add one only if jobs start hanging.

**Verify**: run the YAML validation command from the table → prints `['test']`.

### Step 2: Simulate the job locally once (the "will this go green" check)

You cannot run GitHub Actions locally without extra tooling, but you can
simulate the two gates with the same command shapes in the repo venv:

```bash
./.venv/bin/python -m pytest -q        # must report ~175+ passed, exit 0
./.venv/bin/python -m openaisf.cli coverage   # must exit 0
```

If either fails, do NOT push the workflow; fix the underlying cause (most
likely plan 001 not yet applied — the version-consistency test will fail).
When both pass, the CI job is as close to guaranteed-green as local
verification allows.

**Verify**: both commands exit 0.

## Test plan

- No code or test changes; the pipeline *is* the test. Local simulation in
  Step 2 stands in for a GitHub run.
- Post-merge verification (done by the operator or a reviewer after the push
  is approved): confirm the `release-gates` run on GitHub is green on
  `main` — that is the Done criterion that can only be checked remotely.

## Done criteria

Machine-checkable locally + one remote check. ALL must hold:

- [ ] `.github/workflows/ci.yml` exists and `yaml.safe_load` parses it, with a `test` job
- [ ] `./.venv/bin/python -m pytest -q` → passes, exit 0
- [ ] `./.venv/bin/python -m openaisf.cli coverage` → exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated
- [ ] (After operator approval of the push) the GitHub Actions `release-gates` run on `main` is green

## STOP conditions

Stop and report back (do not improvise) if:

- `pyproject.toml` no longer has the `dev`/`signing` extras, or
  `requires-python` dropped below 3.11.
- The local simulation of either gate fails and the cause is not plan 001
  (i.e. it is a pre-existing failure unrelated to this plan — report it, do
  not paper over it by making the workflow skip that gate).
- The operator asks you to push before you can confirm the local gates pass.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- The `coverage` gate is the release blocker: a crosswalk gap makes it exit 1
  and the job red. That is the desired behaviour — do not soften it.
- If the suite grows slow, revisit `timeout-minutes`; if the matrix starts
  failing only on one Python version, that is a real portability signal, not
  a reason to drop that version.
- When a GitHub token-scoped badge is added to the README later, it will show
  the `release-gates` workflow by name — keep the name stable.
- A reviewer should confirm no third-party actions beyond
  checkout/setup-python, and that the `signing` extra is present (the
  inheritance tests depend on it).