#!/usr/bin/env python3
"""Reference OpenAISF evidence adapter.

Adapters are out-of-tree, contributed and replaceable. The standard defines the
record they emit, not who emits it. This one is deliberately minimal and exists
to document the contract by example.

THE ADAPTER CONTRACT

  1. An adapter reads from an enforcement point it does not control and writes
     OpenAISF evidence records validating against schema/evidence.schema.json.
  2. It emits one record per (control, plane, window). Control-plane records say
     what is configured; data-plane records say what was observed on live
     traffic. Never infer one from the other.
  3. It signs at the producer, before transmission or aggregation — never at an
     aggregator, which could only attest that it received something. Pass a key
     to sign with ed25519; without one the adapter emits an integrity digest,
     which is fine for local development and is treated as absent from T3
     upward, where authorship is the point (D19-C01).
  4. It never invents an observation. If the source cannot answer, the adapter
     omits the record and the control fails as a missing signal, which is the
     correct outcome. Emitting a plausible zero would be fabrication.

Usage:

    python tools/adapters/gateway_adapter.py <input.json> <output-dir> \
        [--key producer.pem --key-id gateway-prod]

Input is a small JSON summary of what a gateway, guardrail or CI system
observed. See examples/gateway-summary.json.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from openaisf.signing import DigestSigner, Ed25519Signer  # noqa: E402

ADAPTER = "openaisf-adapter-reference-gateway"
VERSION = "1.0.0"


def record(system_id, control, plane, observations, window_hours, artefact=None):
    end = datetime.now(timezone.utc).replace(microsecond=0)
    subject = {"system_id": system_id}
    if artefact:
        subject["artefact_digest"] = artefact
    return {
        "openaisf_evidence": "1.0",
        "subject": subject,
        "control": control,
        "plane": plane,
        "window": {
            "from": (end - timedelta(hours=window_hours)).isoformat(),
            "to": end.isoformat(),
        },
        "observations": observations,
        "producer": {"adapter": ADAPTER, "version": VERSION},
    }


def sign(payload: dict, signer) -> dict:
    """Sign the record, then attach. The signature is never part of what it covers."""
    signature = signer.sign(payload)
    return {**payload, "signature": signature.to_dict()}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="gateway_adapter", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("summary")
    parser.add_argument("out_dir")
    parser.add_argument("--key", help="Ed25519 private key PEM for this producer")
    parser.add_argument("--key-id", default="reference-gateway")
    args = parser.parse_args(argv[1:])

    signer = (
        Ed25519Signer(Path(args.key).read_bytes(), args.key_id)
        if args.key else DigestSigner(args.key_id)
    )

    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    system_id = summary["system_id"]
    artefact = summary.get("artefact_digest")
    window_hours = summary.get("window_hours", 24)
    written = 0

    for control, obs in summary["controls"].items():
        # A control-plane claim is only emitted where the source actually
        # reported configuration. Absence is left absent on purpose.
        if "enabled" in obs:
            payload = record(
                system_id, control, "control",
                {"enabled": obs["enabled"], **obs.get("config", {})},
                window_hours, artefact,
            )
            (out_dir / f"{control}-control.json").write_text(
                json.dumps(sign(payload, signer), indent=2) + "\n", encoding="utf-8"
            )
            written += 1

        if "traffic_requests" in obs and "decisions_total" in obs:
            payload = record(
                system_id, control, "data",
                {
                    "traffic_requests": obs["traffic_requests"],
                    "decisions_total": obs["decisions_total"],
                    **obs.get("counters", {}),
                },
                window_hours, artefact,
            )
            (out_dir / f"{control}-data.json").write_text(
                json.dumps(sign(payload, signer), indent=2) + "\n", encoding="utf-8"
            )
            written += 1

    print(f"wrote {written} evidence records to {out_dir}, "
          f"signed with {signer.scheme}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
