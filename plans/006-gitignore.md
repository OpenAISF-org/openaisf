# Plan 006: Ignore generated build artifacts

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 9424806..HEAD -- .gitignore`
> If `.gitignore` changed since this plan was written, compare the "Current
> state" excerpt against the live file; on a mismatch, treat it as a STOP
> condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: hygiene
- **Planned at**: commit `9424806`, 2026-08-19
- **Issue**: (none)

## Why this matters

Every local `pip install -e .` run generates `src/openaisf.egg-info/` (setuptools'
build metadata). It is machine-generated, not source, and today it shows up
unignored in `git status` (`?? src/openaisf.egg-info/`), which means it can be
committed by accident in a broad `git add`. Committed egg-info is churn on
every install and invites confusing diffs for reviewers of an open standard.
This plan teaches git to ignore it (and the sibling artifacts that `build`
and `dist` produce if anyone runs a real build), and cleans the one leftover
directory.

## Current state

- `.gitignore` (entire file, 5 lines):

  ```
  .venv/
  __pycache__/
  *.pyc
  .pytest_cache/
  *.jsonl
  ```

- `git status --porcelain` shows `?? src/openaisf.egg-info/` (untracked,
  present at `src/openaisf.egg-info/`).

Repo conventions that apply:

- `.gitignore` is sorted by broadness and keeps trailing comments minimal
  (currently none). Add the new lines at the end in the same bare style.
- Never ignore anything in `src/openaisf/` that is real source (only the
  `*.egg-info` sibling directory).

## Commands you will need

| Purpose   | Command                                    | Expected on success |
|-----------|--------------------------------------------|---------------------|
| Verify    | `git status --porcelain`                   | only `?? plans/` remains untracked |
| Tests     | `./.venv/bin/python -m pytest -q`          | 172 passed, exit 0 |
| Coverage  | `./.venv/bin/python -m openaisf.cli coverage` | exit 0           |

## Scope

**In scope** (the only files you should modify):
- `.gitignore`
- Delete `src/openaisf.egg-info/` from the working tree (it is regenerated on
  the next install; if you prefer to keep the venv's metadata intact, run
  `./.venv/bin/pip install -e .` again *after* deleting — that is exactly
  what recreates it, and it will now be ignored).

**Out of scope** (do NOT touch):
- `plans/` — it is untracked by design while plans are being authored; it
  will be committed as a unit when the plans are finalised (not by this plan).
- Any change to `.gitignore` beyond the artifact lines below.
- The `.venv/`, `.pytest_cache/` entries (already correct).

## Git workflow

- Branch: `advisor/006-gitignore` (or the repo's branch convention).
- Commit once with a message matching `git log` style (conventional
  commits): `chore: ignore setuptools egg-info and build artifacts`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Append the artifact ignores

Append to the end of `.gitignore`:

```
*.egg-info/
dist/
build/
```

Notes:

- `*.egg-info/` is the fix (matches `src/openaisf.egg-info/` at any depth).
- `dist/` and `build/` are the conventional setuptools outputs for a real
  `python -m build`; include them so the file doesn't need revisiting the day
  someone cuts a release. If you consider them scope creep for this finding,
  drop them and keep only `*.egg-info/` — either way, `*.egg-info/` must be
  present.

**Verify**: `git status --porcelain` → `src/openaisf.egg-info/` no longer
appears (it is ignored even though still on disk).

### Step 2: Remove the leftover directory

```bash
rm -rf src/openaisf.egg-info
```

If the venv still works after this (it will — egg-info is only build
metadata), you are done. If you want to prove regeneration is clean:

```bash
./.venv/bin/pip install -e . --quiet && git status --porcelain
```

→ the directory is recreated and `git status` still shows no
`src/openaisf.egg-info/` line.

## Test plan

- No code changes; verification is `git status` plus a final gate run.
- Verification: `./.venv/bin/python -m pytest -q` → 172 passed, exit 0;
  `./.venv/bin/python -m openaisf.cli coverage` → exit 0.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `.gitignore` contains `*.egg-info/` (and, if kept, `dist/`, `build/`)
- [ ] `git status --porcelain` no longer lists `src/openaisf.egg-info/` even after `pip install -e .`
- [ ] `./.venv/bin/python -m pytest -q` → passes, exit 0
- [ ] `./.venv/bin/python -m openaisf.cli coverage` → exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- `.gitignore` does not match the excerpt above.
- Deleting `src/openaisf.egg-info/` breaks `./.venv/bin/python -m pytest`
  (it should not; if it does, restore the directory and report).
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- When a release build is added later (sdist/wheel), `dist/` and `build/` are
  already covered.
- A reviewer should confirm nothing real under `src/openaisf/` was ignored and
  that the `plans/` directory was left untouched (it is committed separately
  once plans are final).