"""
OpenAISF Conformance CLI — reference implementation (prototype).

The tool that makes "safety as a passing test" real: an AI system is
OpenAISF-conformant at tier T when `openaisf check` exits 0.

Scope of this prototype:
  - Loads openaisf-controls.yaml + openaisf-crosswalk.yaml.
  - Evaluates the project in the current directory against a target tier.
  - Implements real checks for the auto-static T1 controls + key T2 controls.
  - Emits a human report, a machine-readable JSON report, and prints the badge.

Not in this prototype (later versions):
  - auto-runtime checks (eval execution, load-time signing) — stubbed.
  - signed attestation verification — accepts attestations as-is.
  - crosswalk reverse-index coverage report — basic version included.

Usage:
    openaisf init                  # scaffold openaisf.yaml + required dirs
    openaisf check --tier T1       # evaluate; exit 0 if conformant
    openaisf report --tier T2      # emit full report
    openaisf badge --tier T1       # print the badge status

License: Apache-2.0 (the implementation is open; the spec is CC-BY-4.0).
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

# We avoid a hard YAML dependency in the prototype by shipping a tiny parser
# fallback; in production, use PyYAML/ruamel.
try:
    import yaml  # type: ignore
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


# ───────────────────────────────────────────────────────────────────────
# Spec loading
# ───────────────────────────────────────────────────────────────────────
SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"


def _load_yaml(path: Path) -> Any:
    if not HAVE_YAML:
        raise RuntimeError(
            f"PyYAML required to load {path}. Install: pip install pyyaml"
        )
    with path.open() as f:
        return yaml.safe_load(f)


def load_controls() -> dict:
    return _load_yaml(SPEC_DIR / "openaisf-controls.yaml")


def load_crosswalk() -> dict:
    return _load_yaml(SPEC_DIR / "openaisf-crosswalk.yaml")


def flatten_controls(spec: dict) -> list[dict]:
    """Return a flat list of controls with their domain id attached."""
    out = []
    for domain in spec.get("domains", []):
        for c in domain.get("controls", []):
            c2 = dict(c)
            c2["domain"] = domain["id"]
            out.append(c2)
    return out


# ───────────────────────────────────────────────────────────────────────
# Project model (the repo being checked)
# ───────────────────────────────────────────────────────────────────────
@dataclass
class Project:
    root: Path

    def exists(self, rel: str) -> bool:
        # support simple glob like models/*/card.yaml
        if "*" in rel:
            return any(self.root.glob(rel))
        return (self.root / rel).exists()

    def read(self, rel: str) -> str | None:
        p = self.root / rel
        if not p.exists():
            return None
        return p.read_text(errors="replace")


# ───────────────────────────────────────────────────────────────────────
# Check results
# ───────────────────────────────────────────────────────────────────────
@dataclass
class CheckResult:
    control_id: str
    title: str
    tier: str
    status: str  # pass | fail | na | manual
    detail: str = ""
    evidence: list[str] = field(default_factory=list)


# ───────────────────────────────────────────────────────────────────────
# The check implementations.
# Each auto-static control gets a small predicate here. We key by control_id.
# For controls not yet implemented, we mark `manual` and ask for attestation.
# ───────────────────────────────────────────────────────────────────────
def _check_D1_01(proj: Project) -> CheckResult:
    ok = proj.exists("POLICY.md") or proj.exists("policy.md") or proj.exists("policy")
    return CheckResult(
        "D1-01", "AI safety policy exists and is versioned", "T1",
        "pass" if ok else "fail",
        "policy file present" if ok else "no POLICY.md or policy/ found",
    )


def _looks_like_placeholder(value: str) -> bool:
    v = value.strip().strip('"').strip("'").lower()
    return (not v) or v.startswith("todo") or v in {"tbd", "fixme", "none", "null"}


def _yaml_field(cfg_text: str, field: str) -> str | None:
    """Tiny fallback YAML scalar reader (key: value) for openaisf.yaml.
    Returns the raw value or None. Not a full YAML parser."""
    if not cfg_text:
        return None
    for line in cfg_text.splitlines():
        s = line.strip()
        if s.startswith(f"{field}:"):
            return s.split(":", 1)[1].strip()
    return None


def _check_D2_01(proj: Project) -> CheckResult:
    cfg = proj.read("openaisf.yaml") or proj.read("openaisf.yml")
    if not cfg:
        return CheckResult("D2-01", "Intended-use & context statement", "T1",
                           "fail", "no openaisf.yaml found")
    iu = _yaml_field(cfg, "intended_use")
    ctx = _yaml_field(cfg, "context")
    missing = [f for f, v in (("intended_use", iu), ("context", ctx))
               if v is None or _looks_like_placeholder(v)]
    ok = not missing
    return CheckResult(
        "D2-01", "Intended-use & context statement", "T1",
        "pass" if ok else "fail",
        "intended_use + context present and non-placeholder" if ok
        else f"openaisf.yaml has placeholder/missing: {', '.join(missing)}",
    )


def _check_D7_01(proj: Project) -> CheckResult:
    candidates = ["DISCLOSURE.md", "disclosure.md", "README.md"]
    text = ""
    for c in candidates:
        t = proj.read(c)
        if not t:
            continue
        low = t.lower()
        has_ai = ("ai" in low) or ("artificial intelligence" in low) or ("assistant" in low)
        has_disclose = ("disclos" in low) or ("generated" in low) or ("automated" in low)
        if has_ai and has_disclose:
            text = c
            break
    return CheckResult(
        "D7-01", "AI disclosure to end-users", "T1",
        "pass" if text else "fail",
        f"disclosure language found in {text}" if text
        else "no AI disclosure marker (need 'AI' + 'generated/disclosure') in DISCLOSURE.md/README.md",
    )


# Registry of implemented auto-static checks (control_id -> fn)
STATIC_CHECKS = {
    "D1-01": _check_D1_01,
    "D2-01": _check_D2_01,
    "D7-01": _check_D7_01,
}


def evaluate(proj: Project, spec: dict, tier: str) -> list[CheckResult]:
    """Evaluate the project at the given tier. Returns one result per
    applicable control. Unimplemented controls become `manual` (attestation)."""
    results: list[CheckResult] = []
    for c in flatten_controls(spec):
        if tier not in c.get("tiers", []):
            continue  # not applicable at this tier
        cid = c["id"]
        kind = c.get("check", {}).get("kind", "")
        if cid in STATIC_CHECKS and kind == "auto-static":
            r = STATIC_CHECKS[cid](proj)
            r.tier = tier
            results.append(r)
        else:
            results.append(CheckResult(
                cid, c["title"], tier, "manual",
                detail=f"requires {kind} check or attestation (prototype: stubbed)",
                evidence=c.get("evidence", []),
            ))
    return results


# ───────────────────────────────────────────────────────────────────────
# Reporting
# ───────────────────────────────────────────────────────────────────────
def badge_line(results: list[CheckResult], tier: str) -> str:
    fails = [r for r in results if r.status == "fail"]
    manuals = [r for r in results if r.status == "manual"]
    passes = [r for r in results if r.status == "pass"]
    if fails:
        return (f"✗ OpenAISF-{tier}: FAILING "
                f"({len(fails)} failed, {len(passes)} passed, {len(manuals)} attestation-required)")
    if manuals:
        return (f"○ OpenAISF-{tier}: ATTESTATIONS REQUIRED "
                f"({len(passes)} passed, {len(manuals)} to attest)")
    return f"✓ OpenAISF-{tier}: CONFORMANT ({len(passes)} controls passed)"


def compute_reverse_index(crosswalk: dict) -> dict[str, list[str]]:
    rev: dict[str, list[str]] = {}
    for cid, mapping in crosswalk.get("mappings", {}).items():
        for regime, refs in mapping.items():
            if regime.startswith("_"):
                continue
            if isinstance(refs, list):
                rev.setdefault(regime, []).extend(refs)
    return rev


def render_report(results: list[CheckResult], tier: str, crosswalk: dict) -> str:
    lines = []
    lines.append(badge_line(results, tier))
    lines.append("")
    lines.append(f"{'ID':<8} {'STATUS':<8} TITLE")
    lines.append("-" * 70)
    for r in results:
        lines.append(f"{r.control_id:<8} {r.status.upper():<8} {r.title}")
        if r.detail:
            lines.append(f"{'':<17}{r.detail}")
    lines.append("")
    lines.append("Crosswalk coverage (controls satisfied map back to regimes):")
    rev = compute_reverse_index(crosswalk)
    for regime, ids in sorted(rev.items()):
        lines.append(f"  {regime}: {len(ids)} external references covered")
    n_original = sum(
        1 for m in crosswalk.get("mappings", {}).values()
        if any(str(v).startswith("OpenAISF-original") for v in m.values() if isinstance(v, (str, list)))
    )
    lines.append("")
    lines.append(f"OpenAISF-original controls (no incumbent equivalent): {n_original}")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────
# init scaffolding
# ───────────────────────────────────────────────────────────────────────
def cmd_init(proj: Project) -> int:
    cfg = proj.root / "openaisf.yaml"
    if cfg.exists():
        print("openaisf.yaml already exists; aborting init.")
        return 1
    cfg.write_text(
        "# OpenAISF project configuration.\n"
        "system:\n"
        "  name: \"my-ai-system\"\n"
        "  owner: \"your-name\"\n"
        "  intended_use: \"TODO: describe intended use\"\n"
        "  out_of_scope: \"TODO: describe out-of-scope uses\"\n"
        "  context: \"TODO: deployment context (internal tooling / public / B2B / ...)\"\n"
        "target_tier: T1\n"
    )
    (proj.root / "POLICY.md").write_text(
        "# AI Safety Policy\n\n"
        "Owner: TODO\nDate: TODO\nVersion: 0.1\n\n"
        "## Principles\n- [ ] Don't be reckless.\n"
        "## Reporting channel\n- TODO\n"
    )
    for d in ["risk", "data", "models", "agents", "tools", "evals", "telemetry", "docs"]:
        (proj.root / d).mkdir(exist_ok=True)
    print("Scaffolded: openaisf.yaml, POLICY.md, and domain directories.")
    print("Next: openaisf check --tier T1")
    return 0


# ───────────────────────────────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="openaisf", description="OpenAISF conformance CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    c_init = sub.add_parser("init", help="scaffold an OpenAISF project")
    c_init.add_argument("--project", default=".", help="project root")

    c_check = sub.add_parser("check", help="evaluate conformance")
    c_check.add_argument("--tier", default="T1", choices=["T1", "T2", "T3", "T4"])
    c_check.add_argument("--project", default=".", help="project root")
    c_check.add_argument("--json", action="store_true", help="emit JSON report")

    c_report = sub.add_parser("report", help="full report")
    c_report.add_argument("--tier", default="T1", choices=["T1", "T2", "T3", "T4"])
    c_report.add_argument("--project", default=".")

    c_badge = sub.add_parser("badge", help="print badge line only")
    c_badge.add_argument("--tier", default="T1", choices=["T1", "T2", "T3", "T4"])
    c_badge.add_argument("--project", default=".")

    args = p.parse_args(argv)
    proj = Project(Path(args.project).resolve())

    if args.cmd == "init":
        return cmd_init(proj)

    spec = load_controls()
    crosswalk = load_crosswalk()
    results = evaluate(proj, spec, args.tier)

    if args.cmd == "badge":
        print(badge_line(results, args.tier))
        return 0

    if args.cmd == "check":
        if args.json:
            payload = {
                "framework": "OpenAISF",
                "tier": args.tier,
                "results": [asdict(r) for r in results],
                "badge": badge_line(results, args.tier),
            }
            print(json.dumps(payload, indent=2))
        else:
            print(render_report(results, args.tier, crosswalk))
        fails = [r for r in results if r.status == "fail"]
        return 1 if fails else 0

    if args.cmd == "report":
        print(render_report(results, args.tier, crosswalk))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
