# Plan 008: Detect fabricated decisions as a disqualifying contradiction

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 9424806..HEAD -- src/openaisf/check.py tests/test_check.py`
> If either file changed since this plan was written, compare the "Current
> state" excerpts against the live code; on a mismatch, treat it as a STOP
> condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: correctness
- **Planned at**: commit `9424806`, 2026-08-19
- **Issue**: (none)

## Why this matters

The D19-C03 contradiction rule exists so a machine, with no auditor in the
room, can settle the question "was the policy actually operating?" Today
`_contradiction` catches one direction: a policy declared enabled while live
traffic crossed the enforcement point with zero decisions recorded — the
policy "was not operating". The mirror case is left undetected: a data plane
reporting decisions with **zero traffic** — a policy that allegedly fired
decisions while no requests crossed the enforcement point that produces them.
That record cannot have been produced by the enforcement point; it is either
fabricated or describes a different point, and under D19-C03 a contradiction
MUST NOT be resolvable by attestation, so accepting it as evidence weakens the
whole two-plane design. One branch closes the gap; two tests pin both
directions.

## Current state

- `src/openaisf/check.py:202-220` `_contradiction` (docstring at line 205:
  "The D19-C03 rule, stated generically over the reserved observation keys."):

  ```python
  def _contradiction(
      control_record: EvidenceRecord | None, data_record: EvidenceRecord | None
  ) -> str | None:
      """The D19-C03 rule, stated generically over the reserved observation keys."""
      if control_record is None or data_record is None:
          return None
      if control_record.enabled is not True:
          return None
      traffic = data_record.traffic_requests
      decisions = data_record.decisions_total
      if traffic is None or decisions is None:
          return None
      if traffic > 0 and decisions == 0:
          return (
              f"declared enabled, but {traffic} requests crossed the enforcement "
              f"point with 0 decisions recorded. A policy that never fired under "
              f"live traffic was not operating."
          )
      return None
  ```

- `tests/test_check.py:116-145` cover only the existing direction (traffic >
  0, decisions == 0) plus the both-zero non-contradiction case
  (`test_no_traffic_and_no_decisions_is_not_a_contradiction`, line 127).
- The `run`/`rec` helpers in `tests/test_check.py` (lines 62-79) build signed
  `EvidenceRecord`s; the gate on verification is tested separately, so tests
  here may use `verified=True` by default.

Repo conventions that apply:

- Never weaken the assertion that a contradiction cannot be resolved by
  attestation — this plan *adds* a contradiction source; the "cannot resolve
  this" path (`tests/test_check.py:136-145`) must keep passing.
- The `traffic > 0 and decisions > traffic` case is intentionally NOT a
  contradiction: one request may legitimately trigger several decisions at the
  enforcement point. Do not add it.
- Message strings in check.py are written as complete, plain-English sentences
  and asserted on word fragments by tests (e.g. "was not operating"); follow
  that pattern.

## Commands you will need

| Purpose   | Command                                    | Expected on success |
|-----------|--------------------------------------------|---------------------|
| Tests     | `./.venv/bin/python -m pytest tests/test_check.py -q` | 21+ passed, exit 0 |
| Full      | `./.venv/bin/python -m pytest -q`          | 175 passed, exit 0 |
| Coverage  | `./.venv/bin/python -m openaisf.cli coverage` | exit 0           |

Note: on this machine a full pytest run takes roughly two minutes (slow
external volume). Let it finish.

## Scope

**In scope** (the only files you should modify):
- `src/openaisf/check.py`
- `tests/test_check.py`

**Out of scope** (do NOT touch, even though they look related):
- `src/openaisf/evidence.py` — the record shape is fine; this is a
  contradiction-rule change only.
- The `traffic > 0 and decisions > traffic` direction (decisions per request
  are not bounded by request count at the enforcement point).
- The D14-C04 silence rule (`traffic == 0 and decisions == 0`) — already
  handled elsewhere and asserted in
  `test_no_traffic_and_no_decisions_is_not_a_contradiction`; keep it passing.
- Any spec/RFC text — the RFC states the rule over the reserved keys; the
  code comment already claims the generic reading, so no doc change is needed.

## Git workflow

- Branch: `advisor/008-fabrication-reverse` (or the repo's branch convention).
- Commit per step; message style matches `git log` (conventional commits):
  `fix: flag decisions recorded without traffic as a D19-C03 contradiction`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the reverse contradiction branch

In `src/openaisf/check.py`, after the existing `if traffic > 0 and decisions
== 0:` return block (lines 214-219) and before the final `return None`,
insert:

```python
    if traffic == 0 and decisions > 0:
        return (
            f"declared enabled, but {decisions} decisions were recorded with "
            f"0 requests crossing the enforcement point. Decisions with no "
            f"traffic could not have been produced by that point."
        )
```

**Verify**: `./.venv/bin/python -c "from openaisf.check import _contradiction; from openaisf.evidence import EvidenceRecord; from datetime import datetime, timezone, timedelta; from openaisf.signing import Signature; now=datetime(2026,8,7,12,0,tzinfo=timezone.utc); kw=dict(control='D07-C01', plane='data', system_id='urn:test', window_from=now-timedelta(days=1), window_to=now, signature=Signature(scheme='ed25519', value='x', key_id='t'), verified=True, key_known=True, observations={'traffic_requests':0,'decisions_total':3}); c=dict(kw, plane='control', observations={'enabled':True}); from openaisf.evidence import EvidenceRecord as E; print(bool(_contradiction(E(**c), E(**kw))))"` → `True` (and the existing direction still returns `True`).

### Step 2: Add the two tests

In `tests/test_check.py`, directly after
`test_no_traffic_and_no_decisions_is_not_a_contradiction` (line 127-133),
add:

```python
def test_decisions_without_traffic_fail_as_fabricated():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=0, decisions_total=3),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D07-C01") == FAIL
    detail = next(r.detail for r in out.results if r.control_id == "D07-C01")
    assert "no traffic" in detail


def test_decisions_outnumbering_requests_is_not_a_contradiction():
    out = run([
        rec("D07-C01", "control", enabled=True),
        rec("D07-C01", "data", traffic_requests=1, decisions_total=7),
        rec("D01-C01", "control"),
    ])
    assert _status(out, "D07-C01") == PASS
```

The second test pins the deliberate boundary: one request may legitimately
produce several decisions at the enforcement point, so `decisions > traffic`
with both non-zero must NOT trip the rule.

**Verify**: `./.venv/bin/python -m pytest tests/test_check.py -q` → all pass
(20 existing + 2 new = 22), exit 0.

## Test plan

- `tests/test_check.py`, two new tests:
  - `traffic_requests=0, decisions_total=3` on an enabled control → D07-C01
    fails with a "no traffic" detail;
  - `traffic_requests=1, decisions_total=7` → D07-C01 passes (boundary guard).
- The existing contradiction tests (lines 116-145) must remain green —
  nothing about the one-directional rule or the "cannot resolve by
  attestation" path changes.
- Verification: `./.venv/bin/python -m pytest -q` → 172 existing + 2 new =
  174 passed, exit 0.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `_contradiction` returns a message for `traffic == 0 and decisions > 0`
- [ ] The `traffic > 0 and decisions == 0` branch is byte-identical to before (only an *added* branch)
- [ ] `./.venv/bin/python -m pytest tests/test_check.py -q` → all pass, exit 0
- [ ] `./.venv/bin/python -m pytest -q` → 174 passed, exit 0
- [ ] `./.venv/bin/python -m openaisf.cli coverage` → exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- `_contradiction` or the contradiction tests in "Current state" don't match
  the live code.
- Adding the branch causes `test_declared_enabled_with_traffic_and_no_decisions_fails`
  or `test_contradiction_on_an_asserted_control_cannot_be_resolved_by_attestation`
  to fail (that would mean the fix is interfering with the existing rule — it
  should be purely additive).
- A verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- The contradiction rule is now symmetric over the reserved keys: both "claims
  operating but never fired" and "claims fired but no traffic" are machine-
  settled disqualifications. If a future D19-C03 revision adds a third
  condition, it belongs in this same function and its test section.
- A reviewer should confirm the decision-per-request boundary (second new
  test) was kept permissive, and that no code outside `_contradiction` and
  the test file changed.