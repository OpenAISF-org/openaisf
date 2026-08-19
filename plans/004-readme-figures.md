# Plan 004: Align the README's published figures with the pinned tests

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 9424806..HEAD -- README.md tests/test_soa_size.py`
> If either file changed since this plan was written, compare the "Current
> state" excerpts against the live code before proceeding; on a mismatch,
> treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: docs
- **Planned at**: commit `9424806`, 2026-08-19
- **Issue**: (none)

## Why this matters

The README's opening pitch and contributing section publish numbers the test
suite does not produce. `tests/test_soa_size.py` pins the typical internal
non-agentic T1 scope to `[3, 35, 54]`, and the RFC's tier table says tier 1 is
three controls; the README says "four". The test suite now has 172 tests; the
README's contribution gate says "170". For a conformance standard whose
credibility is the product, a published figure that contradicts the enforced
one is a factual error — and the README itself lists "a factual error in any
published figure" as one of the most valuable things a contributor can find
(README.md:341). Three small edits make the README self-consistent and
machine-checkable again.

## Current state

- `README.md:171-176` (in "Part II — The model in five pieces"):

  > A typical internal non-agentic LLM application resolves to **35 controls
  > of 118**; tier 1 resolves to **four**, of which one is mandatory. Both
  > figures are enforced by tests that fail the build if they rise.

- `README.md:316` (in "Adopting it in an organisation"):

  > 1. **Scope one real system at T1.** Four controls, one mandatory. This
  >    exists to prove the loop runs end to end, not to produce assurance.

- `README.md:333` (in "Contributing"): `python -m pytest                      # 170 tests`

- The enforcement that the paragraph at README.md:174-176 refers to:
  `tests/test_soa_size.py` pins `[3, 35, 54]` (typical internal non-agentic)
  and `[4, 51, 82]` (agentic), with ceilings 40/55.

- The authoritative tier scope: `rfc/RFC-OpenAISF-v1.0.md` tier table — T1
  resolves to three controls (one mandatory), T2 to 35 (eight mandatory),
  T3 to 54 (15 mandatory). This is the *source of truth*; the test pins
  follow it.

- Actual test count today: 172 (`./.venv/bin/python -m pytest -q` → "172
  passed"). The count drifts upward as tests are added; the README must not
  hard-pin it to a value that will go stale again.

Repo conventions that apply:

- The RFC is the source of truth for numbers (`tests/test_soa_size.py`
  references it); the README must agree with both.
- README line length wraps at ~80 columns; keep the edits on the same lines
  so the paragraph structure stays intact.

## Commands you will need

| Purpose   | Command                                    | Expected on success |
|-----------|--------------------------------------------|---------------------|
| Read test | `./.venv/bin/python -m pytest tests/test_soa_size.py -q` | 2 passed, exit 0 |
| Full tests| `./.venv/bin/python -m pytest -q`          | 172 passed, exit 0 |
| Coverage  | `./.venv/bin/python -m openaisf.cli coverage` | exit 0           |

Note: on this machine a full pytest run takes roughly two minutes (slow
external volume). Let it finish.

## Scope

**In scope** (the only file you should modify):
- `README.md`

**Out of scope** (do NOT touch, even though they look related):
- `rfc/RFC-OpenAISF-v1.0.md` — source of truth; already correct.
- `tests/test_soa_size.py` — the pins are correct; the README is the liar.
- `CHANGELOG.md` — its v1.0 table's "170" describes the v1.0.0a1 release
  historically and is left alone (see `plans/README.md` "Findings considered").
- Any other README section beyond the three lines below.

## Git workflow

- Branch: `advisor/004-readme-figures` (or the repo's branch convention).
- Commit once, single message matching `git log` style (conventional
  commits): `docs: correct the published tier-1 and test-count figures`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Fix the tier-1 figure in the model paragraph

`README.md:174` — change:

```
application resolves to **35 controls of 118**; tier 1 resolves to **four**, of
```

to:

```
application resolves to **35 controls of 118**; tier 1 resolves to **three**, of
```

(Line 175 keeps "which one is mandatory" — unchanged and now correct.)

### Step 2: Fix the tier-1 figure in the adoption list

`README.md:316` — change:

```
1. **Scope one real system at T1.** Four controls, one mandatory. This exists to
```

to:

```
1. **Scope one real system at T1.** Three controls, one mandatory. This exists to
```

### Step 3: Fix the test-count figure in the contributing gate

`README.md:333` — change:

```
python -m pytest                      # 170 tests
```

to:

```
python -m pytest                      # 172 tests and counting
```

The trailing ", and counting" is deliberate: pinning the exact number here
invites stale figures every time the suite grows (plan 005 will make this
number move again). If you prefer, omit the suffix and instead write the
comment to reflect the *suite must pass* intent — pick one, keep it simple,
and make sure the number you print is the number pytest prints on the next
full run.

**Verify (all three steps)**:
- `grep -n 'four\b' README.md` → only the digest-word "four" in the changelog
  link or other out-of-scope text; no "Four controls" / "four controls of"
  remaining.
- `grep -n 'three\b\|three controls' README.md` → the two edited lines now
  read "three".
- `./.venv/bin/python -m pytest -q` → prints "172 passed" (matches the
  figure you left in the contributing section).

## Test plan

- No code or tests change; verification is `grep` + a full pytest run to
  confirm the printed count matches the README's.
- Verification: `./.venv/bin/python -m pytest -q` → 172 passed, exit 0;
  `./.venv/bin/python -m openaisf.cli coverage` → exit 0.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `README.md` contains "tier 1 resolves to **three**" and "Three controls, one mandatory"
- [ ] No "Four controls" / "**four**" remains in the in-scope paragraphs
- [ ] The number in the contributing section equals what `python -m pytest -q` prints (172)
- [ ] `./.venv/bin/python -m pytest tests/test_soa_size.py -q` → 2 passed
- [ ] `./.venv/bin/python -m pytest -q` → 172 passed, exit 0
- [ ] `./.venv/bin/python -m openaisf.cli coverage` → exit 0
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- `tests/test_soa_size.py` no longer pins `[3, 35, 54]`, or the RFC tier table
  no longer says T1 = 3 — in which case the README's new "three" would be
  wrong too, and the fix belongs in test/RFC instead.
- The paragraph text at `README.md:171-176` has been rewritten and the quoted
  strings no longer match.
- A full pytest run reports a count other than 172 (recheck the README number
  against whatever it reports).
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- The two "three controls" claims are now consistent with `test_soa_size.py`
  and the RFC; if a future control is added to tier 1's scope, both the pin
  and these two README sentences must move together.
- The test-count comment is the one line most likely to rot. When plan 005
  lands, the CI job prints the count; consider teaching a small check (not in
  this plan) that greps the README comment against the pytest run, or accept
  the minor drift risk in exchange for a readable README.
- A reviewer should confirm no *other* README figure was changed and that the
  RFC/pins were not touched.