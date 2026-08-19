"""OpenAISF command line interface.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from openaisf.coverage import (
    compute_coverage,
    compute_provenance,
    load_exclusions,
    threat_regimes,
)
from datetime import datetime, timezone

from openaisf.check import evaluate
from openaisf.errors import SpecError
from openaisf.log import TransparencyLog
from openaisf.signing import DigestSigner, Ed25519Signer
from openaisf.statement import (
    ConformanceStatement,
    build_statement,
    sign_statement,
    verify_statement,
)
from openaisf.evidence import index_evidence, load_evidence, load_keyring
from openaisf.loader import load_catalog, load_inventories
from openaisf.soa import (
    APPLIES,
    EXCLUDED,
    INHERITED,
    NOT_APPLICABLE,
    load_context,
    resolve_soa,
    to_document,
    write_soa,
)

ROOT = Path(__file__).resolve().parents[2]
CATALOG_DIR = ROOT / "spec" / "catalog"
INVENTORY_DIR = ROOT / "spec" / "crosswalk" / "inventories"
EXCLUSIONS_FILE = ROOT / "spec" / "crosswalk" / "exclusions.yaml"

ATTRIBUTION = "OpenAISF — created by Maarten Loose."


def _cmd_coverage(args: argparse.Namespace) -> int:
    controls = load_catalog(CATALOG_DIR)
    inventories = load_inventories(INVENTORY_DIR)
    exclusions = load_exclusions(EXCLUSIONS_FILE)
    regimes, statuses = compute_coverage(controls, inventories, exclusions)
    provenance = compute_provenance(controls, threat_regimes(inventories))
    originals = sum(1 for v in provenance.values() if v == "OpenAISF-original")

    complete = all(r.is_complete for r in regimes)

    if args.json:
        payload = {
            "attribution": ATTRIBUTION,
            "controls": len(controls),
            "openaisf_original": originals,
            "complete": complete,
            "regimes": [asdict(r) for r in regimes],
        }
        if args.verbose:
            payload["requirements"] = [asdict(s) for s in statuses]
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 0 if complete else 1

    sys.stdout.write(f"OpenAISF crosswalk coverage — {len(controls)} controls\n\n")
    header = f"{'regime':<22}{'total':>7}{'covered':>9}{'excluded':>10}{'gap':>6}"
    sys.stdout.write(header + "\n")
    sys.stdout.write("-" * len(header) + "\n")
    total_all = 0
    gap_all = 0
    for regime in regimes:
        total_all += regime.total
        gap_all += len(regime.uncovered)
        sys.stdout.write(
            f"{regime.regime:<22}{regime.total:>7}{regime.covered:>9}"
            f"{regime.excluded:>10}{len(regime.uncovered):>6}\n"
        )
    sys.stdout.write("-" * len(header) + "\n")
    sys.stdout.write(f"{'TOTAL':<22}{total_all:>7}{'':>9}{'':>10}{gap_all:>6}\n")

    if not complete:
        sys.stdout.write(
            f"\n{gap_all} requirements are neither covered nor excluded.\n"
            f"Coverage incomplete. v1.0 cannot freeze.\n"
        )
    else:
        sys.stdout.write("\nEvery in-scope requirement is covered or excluded.\n")

    sys.stdout.write(
        f"\nOpenAISF-original controls: {originals} of {len(controls)}\n"
    )
    return 0 if complete else 1


def _cmd_scope(args: argparse.Namespace) -> int:
    controls = load_catalog(CATALOG_DIR)
    context, inherits, exclusions = load_context(Path(args.context))
    soa = resolve_soa(controls, context, args.tier, inherits, exclusions)

    if args.json:
        sys.stdout.write(json.dumps(to_document(soa), indent=2) + "\n")
        return 0

    out = Path(args.out)
    write_soa(soa, out)

    counts = soa.counts
    sys.stdout.write(f"Statement of Applicability — {soa.system_id} at {args.tier}\n\n")
    sys.stdout.write(f"  applies         {counts[APPLIES]:>5}\n")
    sys.stdout.write(f"  inherited       {counts[INHERITED]:>5}\n")
    sys.stdout.write(f"  excluded        {counts[EXCLUDED]:>5}\n")
    sys.stdout.write(f"  not applicable  {counts[NOT_APPLICABLE]:>5}\n")
    sys.stdout.write(f"  {'-' * 21}\n")
    sys.stdout.write(f"  in scope        {soa.in_scope:>5}  of {len(controls)} in the catalog\n")
    sys.stdout.write(f"\nWritten to {out}\n")
    return 0


_STATUS_ORDER = ["fail", "stale", "manual", "pass", "inherited", "excluded",
                 "not_applicable"]


def _cmd_check(args: argparse.Namespace) -> int:
    controls = load_catalog(CATALOG_DIR)
    context, inherits, exclusions = load_context(Path(args.context))
    soa = resolve_soa(controls, context, args.tier, inherits, exclusions)
    records = load_evidence(
        Path(args.evidence), load_keyring(Path(args.keyring) if args.keyring else None)
    )

    foreign = {r.system_id for r in records} - {soa.system_id}
    if foreign:
        raise SpecError(
            f"evidence for other systems found: {', '.join(sorted(foreign))}. "
            f"Evidence is scoped to one subject."
        )

    run = evaluate(controls, soa, index_evidence(records))

    if args.json:
        payload = {
            "attribution": ATTRIBUTION,
            "system_id": run.system_id,
            "tier": run.tier,
            "evaluated_at": run.evaluated_at.isoformat(),
            "conformant": run.conformant,
            "lease_state": run.lease_state,
            "counts": run.counts,
            "controls": [asdict(r) for r in run.results
                         if args.verbose or r.status not in ("not_applicable",)],
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 0 if run.conformant else 1

    sys.stdout.write(f"OpenAISF conformance — {run.system_id} at {run.tier}\n\n")
    counts = run.counts
    for status in _STATUS_ORDER:
        if counts.get(status):
            sys.stdout.write(f"  {status:<16}{counts[status]:>5}\n")

    blocking = run.blocking
    if blocking:
        sys.stdout.write("\nBlocking:\n")
        for result in sorted(blocking, key=lambda r: r.control_id):
            sys.stdout.write(f"  {result.control_id}  [{result.status}]  {result.detail}\n")

    sys.stdout.write(f"\nlease: {run.lease_state}\n")
    if run.conformant:
        sys.stdout.write(
            f"\n✓ CONFORMANT · OpenAISF-{run.tier} "
            f"({counts.get('pass', 0)} controls passed, "
            f"{counts.get('inherited', 0)} inherited)\n"
        )
    else:
        sys.stdout.write(
            f"\n✗ NOT CONFORMANT · {len(blocking)} blocking control(s)\n"
        )
    sys.stdout.write(f"\n{ATTRIBUTION}\n")
    return 0 if run.conformant else 1


def _signer(args: argparse.Namespace):
    if args.key:
        return Ed25519Signer(Path(args.key).read_bytes(), args.key_id or "default")
    return DigestSigner(args.key_id or "unkeyed")


def _cmd_publish(args: argparse.Namespace) -> int:
    controls = load_catalog(CATALOG_DIR)
    context, inherits, exclusions = load_context(Path(args.context))
    soa = resolve_soa(controls, context, args.tier, inherits, exclusions)
    records = load_evidence(
        Path(args.evidence), load_keyring(Path(args.keyring) if args.keyring else None)
    )
    run = evaluate(controls, soa, index_evidence(records))

    statement = sign_statement(build_statement(run, soa), _signer(args))
    entry = TransparencyLog(Path(args.log)).append(statement.to_dict())

    sys.stdout.write(
        f"published entry {entry.index} to {args.log}\n"
        f"  system     {statement.system_id}\n"
        f"  tier       {statement.tier}\n"
        f"  conformant {statement.conformant}\n"
        f"  stale after {statement.stale_after.isoformat()}\n"
        f"  expires     {statement.expires_at.isoformat()}\n"
        f"  entry hash  {entry.entry_hash}\n"
    )
    return 0 if statement.conformant else 1


def _cmd_verify(args: argparse.Namespace) -> int:
    """Verify somebody else's badge. No account, no relationship, no permission."""
    log = TransparencyLog(Path(args.log))
    log.verify_chain()

    entry = (
        log.entries()[args.entry] if args.entry is not None
        else log.latest_for(args.system)
    )
    if entry is None:
        sys.stderr.write(f"error: no entry found for {args.system}\n")
        return 2

    statement = ConformanceStatement.from_dict(entry.statement)
    key = Path(args.key).read_bytes() if args.key else None
    signature_ok = verify_statement(statement, key)
    now = datetime.now(timezone.utc)
    state = statement.state_at(now)
    trustworthy = signature_ok and state == "valid"

    if args.json:
        sys.stdout.write(json.dumps({
            "attribution": ATTRIBUTION,
            "system_id": statement.system_id,
            "tier": statement.tier,
            "state": state,
            "signature_valid": signature_ok,
            "authenticated": bool(
                statement.signature and statement.signature.provides_authenticity
            ),
            "issued_at": statement.issued_at.isoformat(),
            "stale_after": statement.stale_after.isoformat(),
            "expires_at": statement.expires_at.isoformat(),
            "checked_at": now.isoformat(),
            "log_entry": entry.index,
            "entry_hash": entry.entry_hash,
        }, indent=2) + "\n")
        return 0 if trustworthy else 1

    sys.stdout.write(f"OpenAISF verification — {statement.system_id}\n\n")
    sys.stdout.write(f"  tier            {statement.tier}\n")
    sys.stdout.write(f"  log entry       {entry.index}\n")
    sys.stdout.write("  chain           intact\n")
    sys.stdout.write(
        f"  signature       {'valid' if signature_ok else 'INVALID'}"
        f"{'' if statement.signature and statement.signature.provides_authenticity else ' (integrity only, not authenticated)'}\n"
    )
    sys.stdout.write(f"  issued          {statement.issued_at.isoformat()}\n")
    sys.stdout.write(f"  stale after     {statement.stale_after.isoformat()}\n")
    sys.stdout.write(f"  expires         {statement.expires_at.isoformat()}\n")
    sys.stdout.write(f"  checked at      {now.isoformat()}\n")
    sys.stdout.write(f"\n  state           {state.upper()}\n")
    if state != "valid":
        sys.stdout.write(
            "\nThis badge no longer asserts conformance. Nobody revoked it; "
            "the lease simply ran out.\n"
        )
    sys.stdout.write(f"\n{ATTRIBUTION}\n")
    return 0 if trustworthy else 1


def _cmd_badge(args: argparse.Namespace) -> int:
    log = TransparencyLog(Path(args.log))
    entry = log.latest_for(args.system)
    if entry is None:
        sys.stderr.write(f"error: no entry found for {args.system}\n")
        return 2
    statement = ConformanceStatement.from_dict(entry.statement)
    state = statement.state_at(datetime.now(timezone.utc))
    mark = {"valid": "✓", "stale": "⚠", "expired": "✗", "revoked": "✗"}.get(state, "?")
    sys.stdout.write(
        f"{mark} TruCert · OpenAISF-{statement.tier} · {state}\n"
    )
    return 0 if state == "valid" else 1


def _cmd_export(args: argparse.Namespace) -> int:
    from openaisf.oscal import assessment_results, component_definition

    controls = load_catalog(CATALOG_DIR)
    if args.what == "component-definition":
        sys.stdout.write(json.dumps(component_definition(controls), indent=2) + "\n")
        return 0

    context, inherits, exclusions = load_context(Path(args.context))
    soa = resolve_soa(controls, context, args.tier, inherits, exclusions)
    keyring = load_keyring(Path(args.keyring) if args.keyring else None)
    run = evaluate(controls, soa, index_evidence(load_evidence(Path(args.evidence), keyring)))
    statement = build_statement(run, soa)
    sys.stdout.write(
        json.dumps(assessment_results(run, statement), indent=2) + "\n"
    )
    return 0 if run.conformant else 1


def _cmd_mcp(args: argparse.Namespace) -> int:
    from openaisf.mcp import serve
    return serve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openaisf", description=ATTRIBUTION)
    subparsers = parser.add_subparsers(dest="command")

    coverage = subparsers.add_parser(
        "coverage", help="report crosswalk coverage against external regimes"
    )
    coverage.add_argument("--json", action="store_true", help="emit JSON")
    coverage.add_argument(
        "--verbose", action="store_true", help="include per-requirement detail"
    )
    coverage.set_defaults(func=_cmd_coverage)

    scope = subparsers.add_parser(
        "scope", help="resolve a Statement of Applicability for one system"
    )
    scope.add_argument("--context", required=True, help="path to the scoping file")
    scope.add_argument("--tier", default="T2", choices=["T1", "T2", "T3", "T4"])
    scope.add_argument("--out", default="openaisf-soa.yaml", help="output path")
    scope.add_argument("--json", action="store_true", help="emit JSON to stdout instead")
    scope.set_defaults(func=_cmd_scope)

    check = subparsers.add_parser(
        "check", help="evaluate conformance against collected evidence"
    )
    check.add_argument("--context", required=True, help="path to the scoping file")
    check.add_argument("--evidence", required=True, help="directory of evidence records")
    check.add_argument("--tier", default="T2", choices=["T1", "T2", "T3", "T4"])
    check.add_argument(
        "--keyring",
        help="directory of producer public keys named <key_id>.pem; required "
             "from T3, where an unverifiable signature is treated as absent",
    )
    check.add_argument("--json", action="store_true", help="emit JSON")
    check.add_argument(
        "--verbose", action="store_true", help="include out-of-scope controls"
    )
    check.set_defaults(func=_cmd_check)

    publish = subparsers.add_parser(
        "publish", help="sign a conformance statement and append it to a log"
    )
    publish.add_argument("--context", required=True)
    publish.add_argument("--evidence", required=True)
    publish.add_argument("--tier", default="T2", choices=["T1", "T2", "T3", "T4"])
    publish.add_argument(
        "--keyring",
        help="directory of producer public keys named <key_id>.pem; required "
             "from T3, where an unverifiable signature is treated as absent",
    )
    publish.add_argument("--log", default="openaisf-log.jsonl")
    publish.add_argument("--key", help="Ed25519 private key PEM; omitted means digest only")
    publish.add_argument("--key-id")
    publish.set_defaults(func=_cmd_publish)

    verify_cmd = subparsers.add_parser(
        "verify", help="verify anyone's badge without their cooperation"
    )
    verify_cmd.add_argument("--log", required=True)
    verify_cmd.add_argument("--system", help="system id; defaults to its latest entry")
    verify_cmd.add_argument("--entry", type=int, help="verify a specific log index")
    verify_cmd.add_argument("--key", help="signer public key PEM")
    verify_cmd.add_argument("--json", action="store_true")
    verify_cmd.set_defaults(func=_cmd_verify)

    badge = subparsers.add_parser("badge", help="render the current badge line")
    badge.add_argument("--log", required=True)
    badge.add_argument("--system", required=True)
    badge.set_defaults(func=_cmd_badge)

    mcp = subparsers.add_parser(
        "mcp",
        help="run the MCP server over stdio (read and check only; it cannot "
             "submit evidence, sign or publish)",
    )
    mcp.set_defaults(func=_cmd_mcp)

    export = subparsers.add_parser(
        "export", help="export to OSCAL for GRC and FedRAMP pipelines"
    )
    export.add_argument("what", choices=["assessment-results", "component-definition"])
    export.add_argument("--context", help="required for assessment-results")
    export.add_argument("--evidence", help="required for assessment-results")
    export.add_argument("--tier", default="T2", choices=["T1", "T2", "T3", "T4"])
    export.add_argument(
        "--keyring",
        help="directory of producer public keys named <key_id>.pem; required "
             "from T3, where an unverifiable signature is treated as absent",
    )
    export.set_defaults(func=_cmd_export)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 2

    try:
        return args.func(args)
    except SpecError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
