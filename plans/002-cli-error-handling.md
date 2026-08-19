# Plan 002: Turn CLI config errors into clean messages on exit 2

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 9424806..HEAD -- src/openaisf/cli.py tests/test_cli_check.py tests/test_cli_coverage.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `9424806`, 2026-08-19
- **Issue**: (none)

## Why this matters

The README sells this tool as something that "runs inside other
organisations' CI", and the documented exit-code contract is 0 = conformant,
1 = nonconformant/uncovered, 2 = load or validation error. But today a
typo'd `--context` path crashes with a raw Python `FileNotFoundError`
traceback and exits **1** — the code a CI treats as *"your system is not
conformant"*. A configuration mistake is not a failed audit, and a traceback
is not a diagnostic. This plan makes user-input errors exit 2 with a single
clean `error:` line on stderr, matching the contract, and locks it with a
regression test.

## Current state

- `src/openaisf/cli.py` `main()` (lines 413–417) catches only `SpecError`:

  ```python
  try:
      return args.func(args)
  except SpecError as exc:
      sys.stderr.write(f"error: {exc}\n")
      return 2
  ```

- `load_context(Path(args.context))` (cli.py:108, 136, 201, 307) calls
  `_read_yaml`, which does `path.read_text(...)` inside a `try` that only
  catches `ValidationError` and `yaml.YAMLError` (`src/openaisf/loader.py`
  lines 52–61). A missing or unreadable file therefore raises
  `FileNotFoundError` / `PermissionError` (both `OSError` subclasses) which
  propagate uncaught.
- `_cmd_verify` (cli.py:237) does `Path(args.key).read_bytes() if args.key
  else None` — a bad `--key` path raises `FileNotFoundError` uncaught.
- `Ed25519Signer.__init__` (`src/openaisf/signing.py:106–115`) calls
  `serialization.load_pem_private_key`, which raises `ValueError` (not
  `SpecError`) on a malformed or non-PEM key file — uncaught.
- Verified behaviour today: `./.venv/bin/python -m openaisf.cli scope
  --context nope.yaml --out /tmp/x.yaml` prints a traceback and exits 1.
- `main()` calls `parser.parse_args(argv)` (cli.py:408) *before* the try
  block, so argparse's own `SystemExit(2)` for unknown flags is unaffected.

Repo conventions that apply:

- Exit codes are load-bearing and documented; keep the SpecError→2 path
  exactly as-is. The CLI is the only layer that writes to stdout/stderr
  (`tests/test_licensing.py` enforces no `print()` in library code).
- Tests call `main([...])` directly with `capsys` — see
  `tests/test_cli_check.py` (asserts exit codes 0/1/2) and
  `tests/test_cli_coverage.py` (exit-2 paths).

## Commands you will need

| Purpose   | Command                                    | Expected on success |
|-----------|--------------------------------------------|---------------------|
| Repro     | `./.venv/bin/python -m openaisf.cli scope --context nope.yaml --out /tmp/x.yaml; echo $?` | exit 2, one `error:` line, no `Traceback` |
| Tests     | `./.venv/bin/python -m pytest -q`          | 174+ passed, exit 0 |

Note: on this machine a full pytest run takes roughly two minutes (slow
external volume). Let it finish.

## Scope

**In scope** (the only files you should modify):
- `src/openaisf/cli.py`
- `tests/test_cli_check.py`

**Out of scope** (do NOT touch, even though they look related):
- `src/openaisf/loader.py` — the fix is at the CLI boundary, not the loader.
- `src/openaisf/mcp.py` — it already converts unexpected errors to
  `INTERNAL_ERROR` in its stdio loop (mcp.py:684–686); its contract differs.
- Adding a blanket `except Exception` in `main()` — a genuine programming bug
  must still surface as a traceback for debugging, not be swallowed as a
  user error. Catch the narrow set below.
- `--keyring` plumbing for `export` — that is plan 003.

## Git workflow

- Branch: `advisor/002-cli-errors` (or the repo's branch convention).
- Commit per step; message style matches `git log` (conventional commits):
  `fix: cli config errors exit 2 with a clean message instead of a traceback`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Widen the error boundary in `main()`

In `src/openaisf/cli.py`, replace the try/except in `main()` (lines 413–417)
so that, after the existing `except SpecError`, user-input and I/O errors are
also turned into clean exit-2 failures:

```python
    try:
        return args.func(args)
    except SpecError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
```

Rationale for the set: `OSError` covers missing/unreadable files
(`FileNotFoundError`, `PermissionError`) raised by `--context`, `--key`,
`--log` and evidence reads; `ValueError` covers malformed PEM keys from
`load_pem_private_key` and malformed inputs from the signing path. Do not
add `Exception` — programming errors must still traceback.

**Verify**: `./.venv/bin/python -m openaisf.cli scope --context nope.yaml --out /tmp/x.yaml; echo $?`
→ exactly one `error: [Errno 2] ... nope.yaml` line on stderr, no `Traceback`
line, exit 2.

### Step 2: Add regression tests

Append to `tests/test_cli_check.py` (which already imports `main`, `ROOT`,
`capsys`-based checks, and `pytest`):

```python
def test_missing_context_file_is_a_config_error_not_a_failure(tmp_path, capsys):
    exit_code = main(["scope", "--context", str(tmp_path / "nope.yaml"),
                      "--out", str(tmp_path / "soa.yaml")])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert err.startswith("error:")
    assert "Traceback" not in err


def test_missing_verify_key_file_is_a_config_error(tmp_path, capsys):
    import json
    from openaisf.cli import main as _main

    log = tmp_path / "log.jsonl"
    entry = {
        "index": 0,
        "previous_hash": "sha256:" + "0" * 64,
        "statement": {
            "schema_version": "1.0",
            "format": "OpenAISF-statement",
            "system_id": "urn:test",
            "tier": "T2",
            "conformant": True,
            "issued_at": "2026-08-07T12:00:00+00:00",
            "stale_after": "2027-08-07T12:00:00+00:00",
            "expires_at": "2027-08-07T12:00:00+00:00",
            "controls": {},
            "signature": {"scheme": "sha256-digest", "value": "x"},
        },
    }
    log.write_text(json.dumps(entry) + "\n")

    exit_code = _main(["verify", "--log", str(log),
                       "--key", str(tmp_path / "nope.pem")])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert err.startswith("error:")
    assert "Traceback" not in err
```

Note: keep the `_main` alias and the local import local to the second test so
the file's existing top-level import of `main` (used by all other tests) is
untouched. If `TransparencyLog.append`'s hash-chain check makes this fixture
awkward (it recomputes `entry_hash` from `previous_hash` + statement), build
the entry with the module API instead: import `TransparencyLog`,
`ConformanceStatement`, `build_statement` and `sign_statement` like
`tests/test_cli_lease.py:18-24` does, or simpler — drop the `--key` argument
and instead assert the missing-`--context` case plus a malformed-key case
using a real published log via the `_publish` helper pattern in
`tests/test_cli_lease.py`. Prefer whatever keeps the fixture genuine; the two
assertions that matter are `exit_code == 2`, `err.startswith("error:")`, and
`"Traceback" not in err`.

**Verify**: `./.venv/bin/python -m pytest tests/test_cli_check.py -q` → all
pass, exit 0.

## Test plan

- Two new tests in `tests/test_cli_check.py`:
  - missing `--context` file → exit 2, `error:` line, no traceback;
  - missing `--key` file on `verify` (via a real published log fixture) →
    exit 2, `error:` line, no traceback.
- Existing pattern to model after: `tests/test_cli_check.py`'s
  `test_evidence_for_another_system_is_refused` (exit-2 with stderr
  assertion) and `tests/test_cli_lease.py`'s `_publish` helper.
- Verification: `./.venv/bin/python -m pytest -q` → all pass (existing 172 +
  2 new), exit 0.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `scope --context <missing>` and `verify --key <missing>` exit 2 with a single `error:` line and no traceback
- [ ] `./.venv/bin/python -m pytest tests/test_cli_check.py -q` → all pass
- [ ] `./.venv/bin/python -m pytest -q` → 174 passed, exit 0
- [ ] `./.venv/bin/python -m openaisf.cli coverage` → exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The `main()` excerpt in "Current state" doesn't match the live code.
- Adding `ValueError` to the catch swallows a genuine programming error that
  a test then masks (i.e. a test passes only because an internal bug is now
  reported as exit 2 — that would mean the catch set is too wide).
- A verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- The exit-code contract (0/1/2) is now enforced at the boundary. Future
  commands that add new user-input paths inherit the behaviour for free.
- A reviewer should confirm `except Exception` was NOT added — the traceback
  path for real bugs must survive.
- Deferred: `export` still lacks `--keyring` (plan 003). Until then,
  `export assessment-results` at T3+ cannot verify signed evidence; that is
  a separate finding, not this plan.