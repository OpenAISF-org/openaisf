# Plan 007: Fix the `EvidenceRecord.age` return annotation

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 9424806..HEAD -- src/openaisf/evidence.py`
> If `evidence.py` changed since this plan was written, compare the "Current
> state" excerpt against the live code; on a mismatch, treat it as a STOP
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

`EvidenceRecord.age()` computes `now - window_to`, which is a
`datetime.timedelta`, but its declared return type is `"object"`. The
annotation says *nothing* about what callers get, so a type checker or a
maintainer reading the source cannot tell that `age()` yields an elapsed-time
span. Because the module has `from __future__ import annotations` (line 11),
the wrong annotation is stored as a string and never validated at runtime —
it lies silently until someone calls `typing.get_type_hints` and gets
`object` back. For a library whose whole job is telling callers how stale a
record is, the public type of `age()` should be honest. One line fixes it;
one test proves the fix.

## Current state

- `src/openaisf/evidence.py:15`: `from datetime import datetime, timezone`
  (no `timedelta`).
- `src/openaisf/evidence.py:86-88`:

  ```python
  def age(self, now: datetime) -> "object":
      """How stale this record is, measured from the end of its window."""
      return now - self.window_to
  ```

- Callers (e.g. `src/openaisf/check.py`) already use the value as a
  `timedelta` (comparisons against `datetime.timedelta` thresholds). The
  runtime behaviour is correct; only the type contract is wrong.

Repo conventions that apply:

- The module is stdlib-only (a load/read library); the fix adds only a
  stdlib `timedelta` import.
- Annotations across the codebase are explicit and typed (see
  `traffic_requests(self) -> int | None` at lines 79-80); `"object"` is an
  outlier, not the style.
- Tests live in `tests/`, pytest, plain asserts (see `tests/test_invariants.py`).

## Commands you will need

| Purpose   | Command                                    | Expected on success |
|-----------|--------------------------------------------|---------------------|
| Typecheck | `./.venv/bin/python -c "from openaisf.evidence import EvidenceRecord; import typing; print(typing.get_type_hints(EvidenceRecord.age)['return'].__name__)"` | `timedelta` |
| Tests     | `./.venv/bin/python -m pytest -q`          | 173 passed, exit 0 |

Note: on this machine a full pytest run takes roughly two minutes (slow
external volume). Let it finish.

## Scope

**In scope** (the only files you should modify):
- `src/openaisf/evidence.py`
- `tests/test_evidence.py` (create if it does not exist; if a test file for
  the evidence module already exists, append there)

**Out of scope** (do NOT touch):
- `src/openaisf/check.py` — callers are already correct; no change needed.
- Adding runtime type guards or pydantic-style validation — out of proportion
  to the fix.
- `mcp.py`, `cli.py`, schemas — unaffected.

## Git workflow

- Branch: `advisor/007-age-annotation` (or the repo's branch convention).
- Commit per step; message style matches `git log` (conventional commits):
  `fix: EvidenceRecord.age returns a timedelta, not object`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Fix the import and the annotation

- `evidence.py:15`: change to `from datetime import datetime, timedelta, timezone`.
- `evidence.py:86`: change the signature to

  ```python
  def age(self, now: datetime) -> timedelta:
  ```

  (The `from __future__ import annotations` makes the unquoted annotation
  safe; the explicit `timedelta` import also makes `typing.get_type_hints`
  resolvable.)

**Verify**: run the Typecheck command from the table → prints `timedelta`
(was `object`).

### Step 2: Add a test that pins the type

Create `tests/test_evidence.py` (or append to the existing evidence test file):

```python
"""EvidenceRecord type contracts.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

import typing
from datetime import datetime, timedelta, timezone

from openaisf.evidence import EvidenceRecord


def test_age_returns_a_timedelta():
    record = EvidenceRecord(
        control="D07-C01",
        plane="control",
        system_id="urn:openaisf:system:test",
        window_from=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        window_to=datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc),
        signature=None,
        verified=False,
        key_known=True,
        observations={},
    )
    resolved = typing.get_type_hints(EvidenceRecord.age)["return"]
    assert resolved is timedelta
    age = record.age(datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc))
    assert isinstance(age, timedelta)
    assert age == timedelta(days=1)
```

Notes for the executor:

- If the `EvidenceRecord` dataclass's constructor field order differs (it is
  frozen; check the field list at `evidence.py:39-65`), use keyword arguments
  exactly as shown or match the actual field names — the assertions that
  matter are `resolved is timedelta`, `isinstance(age, timedelta)` and the
  elapsed-time equality.
- The `key_known` and `verified` fields are positional in the frozen
  dataclass; keyword args avoid ordering surprises.

**Verify**: `./.venv/bin/python -m pytest tests/test_evidence.py -q` → 1
passed, exit 0.

## Test plan

- New/updated `tests/test_evidence.py`: one test asserting
  `typing.get_type_hints(EvidenceRecord.age)["return"] is timedelta` and that
  a computed `age()` is a `timedelta` of the right length.
- Pattern to model after: `tests/test_invariants.py` (plain asserts, no
  fixtures).
- Verification: `./.venv/bin/python -m pytest -q` → 172 existing + 1 new =
  173 passed, exit 0.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `evidence.py:15` imports `timedelta`; `evidence.py:86` annotates `-> timedelta`
- [ ] `typing.get_type_hints(EvidenceRecord.age)["return"]` resolves to `timedelta` (not `object`)
- [ ] `./.venv/bin/python -m pytest tests/test_evidence.py -q` → 1 passed
- [ ] `./.venv/bin/python -m pytest -q` → 173 passed, exit 0
- [ ] `./.venv/bin/python -m openaisf.cli coverage` → exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The `age` method or the `datetime` import line does not match "Current state".
- The `EvidenceRecord` constructor signature makes the test fixture in Step 2
  invalid in a way you cannot adapt by matching actual field names (the
  keywords shown are illustrative; matching the real dataclass is in scope).
- A verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- The `from __future__ import annotations` in this module means future
  annotations must stay importable if any tool resolves them; keep `timedelta`
  imported as long as `age()` is annotated with it.
- A reviewer should confirm the runtime behaviour of `age()` was not changed
  (return value identical) and that check.py's threshold comparisons were
  untouched.