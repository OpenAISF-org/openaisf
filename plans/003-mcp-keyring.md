# Plan 003: Give the MCP check tool a keyring so T3/T4 evidence can verify

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 9424806..HEAD -- src/openaisf/mcp.py src/openaisf/cli.py src/openaisf/evidence.py tests/test_mcp.py tests/test_cli_check.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `9424806`, 2026-08-19
- **Issue**: (none)

## Why this matters

The MCP server is the agent-facing conformance checker, and at T3 and above
conformance *means* verified authorship: a digest proves a record is intact
but not who produced it, and `check.py` treats an unverifiable record as
absent. But `openaisf_check` loads evidence with no keyring, so every
ed25519-signed record is marked "no public key available" and the check tool
cannot produce a passing T3/T4 result even for genuinely signed evidence.
The CLI solved this with `--keyring` (`cli.py:139,204`); the MCP tool has no
equivalent, so the agent path is functionally broken exactly at the tiers
where authenticity is the point. The same gap exists in `export
assessment-results` (`cli.py:309`), which also loads evidence without a
keyring. This plan plumbs a keyring through both.

## Current state

- `src/openaisf/mcp.py:52` imports only `index_evidence, load_evidence` from
  `openaisf.evidence`. The module also exports `load_keyring(keyring_dir:
  Path | None) -> dict[str, bytes]` (`src/openaisf/evidence.py:139-146`),
  which reads `<key_id>.pem` files from a directory.
- `_tool_check` (`src/openaisf/mcp.py:248-280`):

  ```python
  def _tool_check(arguments: dict) -> dict:
      context, inherits, exclusions = _context_from(arguments)
      tier = arguments.get("tier", "T2")
      evidence_dir = arguments.get("evidence_dir")
      if not evidence_dir:
          raise McpError(INVALID_PARAMS, "evidence_dir is required")
      ...
      records = load_evidence(Path(evidence_dir))
  ```

  `load_evidence(dir)` calls `_from_dict(entry, where, keyring=None)`, and
  `_from_dict` (`evidence.py:111-117`) then sets `key_known = False`,
  `verified = False` for every ed25519 record. `inadmissible`
  (`check.py:175-178`) reports "no public key available for ...".
- The `openaisf_check` tool schema (`mcp.py:397-412`) has properties
  `context`, `tier`, `evidence_dir` only.
- `src/openaisf/cli.py:299-314` `_cmd_export` loads evidence without a
  keyring: `load_evidence(Path(args.evidence))` (line 309). The `export`
  argparse parser (lines 399-406) has no `--keyring` argument, unlike `check`
  (lines 350-354) and `publish` (lines 367-371).
- Tests: `tests/test_mcp.py` has a `keypair`-less, stdlib-only harness
  (`handle`/`tool` helpers, lines 32-40) and uses the committed digest-signed
  examples at T1 (`ROOT / "examples" / "evidence"`). For real ed25519 tests it
  will need the `cryptography` extra — use `pytest.importorskip("cryptography")`
  exactly as `tests/test_cli_lease.py:87` and `tests/test_inheritance.py` do,
  so the suite still passes without `[signing]`.

Repo conventions that apply:

- MCP server is **stdlib-only** (`mcp.py:31`) — `load_keyring` from
  `openaisf.evidence` is stdlib (`pathlib` + `read_bytes`), so importing it is
  fine.
- MCP tool names must not contain writing verbs (`tests/test_mcp.py:46-61`);
  a `keyring` parameter is a read input, so no naming constraint applies.
- The D19 no-write rule must not be weakened: this plan adds a *verification
  key input*, not any evidence-writing capability.
- `--keyring` help text convention (from `cli.py:350-353`): "directory of
  producer public keys named <key_id>.pem; required from T3, where an
  unverifiable signature is treated as absent".

## Commands you will need

| Purpose   | Command                                    | Expected on success |
|-----------|--------------------------------------------|---------------------|
| Tests     | `./.venv/bin/python -m pytest tests/test_mcp.py -q` | all pass, exit 0 |
| Tests     | `./.venv/bin/python -m pytest -q`          | 177+ passed, exit 0 |
| Coverage  | `./.venv/bin/python -m openaisf.cli coverage` | exit 0           |

Note: on this machine a full pytest run takes roughly two minutes (slow
external volume). Let it finish.

## Scope

**In scope** (the only files you should modify):
- `src/openaisf/mcp.py`
- `src/openaisf/cli.py`
- `tests/test_mcp.py`
- `tests/test_cli_check.py`

**Out of scope** (do NOT touch, even though they look related):
- `src/openaisf/evidence.py` — its keyring contract is already correct and
  tested at the unit level; this plan only wires callers to it.
- The MCP `server/discover` `instructions` text — optional wording tweak only;
  leave unchanged unless a test demands it.
- `tools/adapters/gateway_adapter.py` — producers sign at the source; no change.
- `mcp.py` `SUPPORTED_VERSIONS` — protocol versions, not affected.

## Git workflow

- Branch: `advisor/003-mcp-keyring` (or the repo's branch convention).
- Commit per step; message style matches `git log` (conventional commits):
  `fix: mcp openaisf_check and export accept a keyring for T3/T4 evidence`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Plumb a keyring through the MCP `openaisf_check` tool

- `src/openaisf/mcp.py:52`: extend the import to
  `from openaisf.evidence import index_evidence, load_evidence, load_keyring`.
- In `_tool_check` (`mcp.py:248-280`), read an optional `keyring` argument and
  pass it to `load_evidence`:

  ```python
  keyring_dir = arguments.get("keyring")
  keyring = load_keyring(Path(keyring_dir)) if keyring_dir else {}
  ...
  records = load_evidence(Path(evidence_dir), keyring)
  ```

- In the `openaisf_check` tool schema (`mcp.py:400-408`), add a property:

  ```python
  "keyring": {
      "type": "string",
      "description": "Directory of producer public keys named <key_id>.pem; "
                     "required from T3, where an unverifiable signature is "
                     "treated as absent.",
  },
  ```

  Leave `required` as `["context", "evidence_dir"]` — keyring stays optional.

**Verify**: `./.venv/bin/python -c "from openaisf.mcp import TOOLS; s = dict((n, s) for n, _d, s, _h in TOOLS)['openaisf_check']; print('keyring' in s['properties'])"` → `True`.

### Step 2: Add the `--keyring` argument to `export` and pass it through

- In `cli.py` `export` parser (lines 399-406), add the same argument as
  `check`/`publish`:

  ```python
  export.add_argument(
      "--keyring",
      help="directory of producer public keys named <key_id>.pem; required "
           "from T3, where an unverifiable signature is treated as absent",
  )
  ```

- In `_cmd_export` (line 309), load with the keyring:

  ```python
  run = evaluate(controls, soa, index_evidence(
      load_evidence(
          Path(args.evidence),
          load_keyring(Path(args.keyring) if args.keyring else None),
      )
  ))
  ```

  `load_keyring` is already imported at `cli.py:32`.

**Verify**: `./.venv/bin/python -m openaisf.cli export assessment-results --help`
→ the help output lists `--keyring`.

### Step 3: Add MCP tests for the keyring path

Append to `tests/test_mcp.py`:

```python
# --- T3/T4: signed evidence needs a keyring -------------------------------


@pytest.fixture()
def signed_evidence(tmp_path):
    """A control-plane record signed by an ed25519 producer key, plus the keyring."""
    crypto = pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from openaisf.evidence import signable_payload
    from openaisf.signing import Ed25519Signer

    key = Ed25519PrivateKey.generate()
    key_id = "gateway-prod"
    private_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption())

    record = {
        "openaisf_evidence": "1.0",
        "subject": {"system_id": "urn:openaisf:system:acme-support-agent"},
        "control": "D07-C01",
        "plane": "control",
        "window": {"from": "2026-08-06T12:00:00+00:00",
                   "to": "2026-08-07T12:00:00+00:00"},
        "observations": {"enabled": True},
        "producer": {"adapter": "test", "version": "1.0"},
    }
    signature = Ed25519Signer(private_pem, key_id).sign(signable_payload(record))
    record["signature"] = signature.to_dict()

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "D07-C01-control.json").write_text(json.dumps(record))

    keyring = tmp_path / "keyring"
    keyring.mkdir()
    (keyring / f"{key_id}.pem").write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
    return str(evidence_dir), str(keyring)


def test_check_with_a_keyring_verifies_signed_evidence(signed_evidence):
    evidence_dir, keyring = signed_evidence
    result = tool("openaisf_check", {
        "context": CONTEXT_YAML, "tier": "T3",
        "evidence_dir": evidence_dir, "keyring": keyring,
    })
    text = result["content"][0]["text"]
    assert "no public key available" not in text


def test_check_without_a_keyring_reports_the_missing_key(signed_evidence):
    evidence_dir, _keyring = signed_evidence
    result = tool("openaisf_check", {
        "context": CONTEXT_YAML, "tier": "T3",
        "evidence_dir": evidence_dir,
    })
    text = result["content"][0]["text"]
    assert "no public key available" in text
```

Notes for the executor:

- `CONTEXT_YAML` (already defined in `tests/test_mcp.py:22-29`) declares
  `system_id: urn:openaisf:system:acme-support-agent`, which matches the
  fixture's `subject.system_id`. The T3 result will be NOT conformant (only
  one control has evidence) — that is fine; the assertions are about the
  keyring being used, not conformance.
- `D07-C01` exists in the real catalog and is `emitted` at T3, so the
  `_tool_check` foreign-evidence guard (which compares record system_ids to
  the SoA's) will pass.
- If `cryptography` is absent, both tests skip via `importorskip` and the
  suite stays green without `[signing]`.

**Verify**: `./.venv/bin/python -m pytest tests/test_mcp.py -q` → all pass
(19 existing + 2 new), exit 0.

### Step 4: Add an export keyring test

Append to `tests/test_cli_check.py` a test that `export assessment-results`
accepts `--keyring` and produces OSCAL JSON (exit 0 implies the evaluate path
ran; it does not require conformance):

```python
def test_export_accepts_a_keyring(tmp_path, capsys):
    exit_code = main(["export", "assessment-results",
                      "--context", CONTEXT, "--evidence", EVIDENCE,
                      "--tier", "T1", "--keyring", str(tmp_path)])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["catalog"] or payload.get("results")
```

Note: `CONTEXT`/`EVIDENCE` and `json` are already imported in
`tests/test_cli_check.py`. `str(tmp_path)` is an empty keyring directory —
`load_keyring` returns `{}` for it (`evidence.py:141-142`), so the call is a
round-trip of the new argument. If the real `assessment_results` payload shape
doesn't match the assertion above, inspect a live run and assert on whatever
stable top-level key exists (the point is exit 0 with `--keyring` accepted).

**Verify**: `./.venv/bin/python -m pytest tests/test_cli_check.py -q` → all
pass, exit 0.

## Test plan

- `tests/test_mcp.py`: two new tests — with keyring, signed T3 evidence is
  verified (no "no public key available"); without keyring, the tool reports
  the missing key. Model the keyring fixture on
  `tests/test_cli_lease.py:85-99`.
- `tests/test_cli_check.py`: one new test that `export assessment-results
  --keyring <empty dir>` exits 0 and emits JSON.
- Verification: `./.venv/bin/python -m pytest -q` → all pass (172 existing +
  3 new), exit 0.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -n 'load_keyring' src/openaisf/mcp.py` → import + one use in `_tool_check`
- [ ] `./.venv/bin/python -m openaisf.cli export assessment-results --help` lists `--keyring`
- [ ] `./.venv/bin/python -m pytest tests/test_mcp.py tests/test_cli_check.py -q` → all pass
- [ ] `./.venv/bin/python -m pytest -q` → 175 passed, exit 0 (172 + 3 new)
- [ ] `./.venv/bin/python -m openaisf.cli coverage` → exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The excerpts in "Current state" don't match the live code.
- `pytest.importorskip("cryptography")` is required but `cryptography` is not
  installed and you cannot install it (install with
  `./.venv/bin/pip install '.[signing]'` — this is allowed inside the
  executor's own worktree; the test will skip if absent, but then the two new
  MCP tests won't actually run, and that must be reported, not hidden).
- A verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- `openaisf_check`'s schema now mirrors the CLI's `--keyring` contract; if the
  CLI help text changes, update the MCP description to match.
- The `verify_statement` path (badge verification, `mcp.py:311-342`) does not
  take a keyring and is intentionally keyless — anyone can verify a badge. Do
  not conflate the two; this plan is about *evidence* verification only.
- A reviewer should confirm no tool gained a writing verb (the D19 test in
  `tests/test_mcp.py:46-61` enforces it) and that the optional `keyring` did
  not become `required`.