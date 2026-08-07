"""Export conformance results as OSCAL.

OSCAL is an output format, not the native one. It has no concept of a lease, a
freshness window or a two-plane evidence pairing, and bending it into one would
cost more than it returns. But OSCAL became mandatory for FedRAMP providers in
September 2026, which makes emitting it free interoperability with every GRC
pipeline that matters — and it is how OpenAISF absorbs the prior art on
machine-readable AI compliance rather than competing with it.

What OSCAL cannot carry, this exporter puts in properties rather than dropping:
the lease state, the two deadlines, and the plane each observation came from.
A consumer that understands only OSCAL sees a normal assessment result; one that
understands OpenAISF sees the lease.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from openaisf.check import EXCLUDED_OK, INHERITED_OK, NA, PASS, ConformanceRun

OSCAL_VERSION = "1.1.2"
NS = "https://openaisf.org/ns/oscal"
ATTRIBUTION = "OpenAISF — created by Maarten Loose."

#: OSCAL findings are satisfied or not. Everything else here is a distinction
#: OSCAL does not model, so it travels as a property alongside.
_SATISFIED = {PASS, INHERITED_OK}


def _uuid(seed: str) -> str:
    """Deterministic UUIDs so re-exporting the same run diffs cleanly."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{NS}/{seed}"))


def _prop(name: str, value: str) -> dict:
    return {"name": name, "ns": NS, "value": value}


def _metadata(title: str, now: datetime) -> dict:
    return {
        "title": title,
        "last-modified": now.isoformat(),
        "version": "1.0",
        "oscal-version": OSCAL_VERSION,
        "props": [_prop("attribution", ATTRIBUTION)],
        "parties": [{
            "uuid": _uuid("party/openaisf"),
            "type": "organization",
            "name": "OpenAISF",
            "remarks": ATTRIBUTION,
        }],
    }


def assessment_results(run: ConformanceRun, statement=None) -> dict:
    """An OSCAL Assessment Results document for one conformance run."""
    now = datetime.now(timezone.utc)
    assessed = [r for r in run.results if r.status != NA]

    observations = []
    findings = []
    for result in assessed:
        observation_uuid = _uuid(f"obs/{run.system_id}/{result.control_id}")
        props = [
            _prop("openaisf-status", result.status),
            _prop("openaisf-control", result.control_id),
        ]
        if result.obligation:
            props.append(_prop("openaisf-obligation", result.obligation))
        if result.planes_present:
            props.append(
                _prop("openaisf-evidence-planes", ",".join(result.planes_present))
            )
        if result.disqualifying:
            props.append(_prop("openaisf-disqualifying", "true"))

        observations.append({
            "uuid": observation_uuid,
            "title": f"{result.control_id} — {result.status}",
            "description": result.detail or result.status,
            "methods": ["TEST"] if result.planes_present else ["EXAMINE"],
            "collected": run.evaluated_at.isoformat(),
            "props": props,
        })

        findings.append({
            "uuid": _uuid(f"finding/{run.system_id}/{result.control_id}"),
            "title": result.control_id,
            "description": result.detail or result.status,
            "target": {
                "type": "objective-id",
                "target-id": result.control_id,
                "status": {
                    "state": "satisfied" if result.status in _SATISFIED
                    else "not-satisfied"
                },
                "props": [_prop("openaisf-status", result.status)],
            },
            "related-observations": [{"observation-uuid": observation_uuid}],
        })

    result_props = [
        _prop("openaisf-tier", run.tier),
        _prop("openaisf-lease-state", run.lease_state),
        _prop("openaisf-conformant", str(run.conformant).lower()),
    ]
    if statement is not None:
        result_props += [
            _prop("openaisf-stale-after", statement.stale_after.isoformat()),
            _prop("openaisf-expires-at", statement.expires_at.isoformat()),
        ]

    return {
        "assessment-results": {
            "uuid": _uuid(f"ar/{run.system_id}/{run.evaluated_at.isoformat()}"),
            "metadata": _metadata(
                f"OpenAISF conformance assessment — {run.system_id}", now
            ),
            "import-ap": {"href": "https://openaisf.org/spec/assessment-plan"},
            "results": [{
                "uuid": _uuid(f"result/{run.system_id}/{run.evaluated_at.isoformat()}"),
                "title": f"OpenAISF {run.tier} conformance",
                "description": (
                    f"Conformance of {run.system_id} against OpenAISF {run.tier}. "
                    f"Lease state {run.lease_state}. Conformance is a state with a "
                    f"heartbeat: this result describes the system as at "
                    f"{run.evaluated_at.isoformat()} and expires on its own."
                ),
                "start": run.evaluated_at.isoformat(),
                "end": run.evaluated_at.isoformat(),
                "props": result_props,
                "reviewed-controls": {
                    "control-selections": [{
                        "include-controls": [
                            {"control-id": r.control_id} for r in assessed
                        ]
                    }]
                },
                "observations": observations,
                "findings": findings,
            }],
        }
    }


def component_definition(controls: list[dict]) -> dict:
    """An OSCAL Component Definition describing the OpenAISF catalog itself."""
    now = datetime.now(timezone.utc)
    implementations = []
    for control in controls:
        implementations.append({
            "uuid": _uuid(f"impl/{control['id']}"),
            "control-id": control["id"],
            "description": control["normative"].strip(),
            "props": [
                _prop("openaisf-domain", control["domain"]),
                _prop("openaisf-level", control["level"]),
                _prop("openaisf-verification", control["verification"]["method"]),
                _prop("openaisf-rfc2119", control["rfc2119"]),
            ] + [
                _prop("openaisf-tier", f"{tier}={obligation}")
                for tier, obligation in sorted(control["tiers"].items())
            ],
        })

    return {
        "component-definition": {
            "uuid": _uuid("cd/openaisf-catalog"),
            "metadata": _metadata("OpenAISF control catalog", now),
            "components": [{
                "uuid": _uuid("component/openaisf"),
                "type": "validation",
                "title": "OpenAISF",
                "description": (
                    "The OpenAISF control catalog. Conformance is a state with a "
                    "heartbeat rather than an event with a certificate."
                ),
                "props": [_prop("attribution", ATTRIBUTION)],
                "control-implementations": [{
                    "uuid": _uuid("ci/openaisf"),
                    "source": "https://openaisf.org/spec/openaisf-controls.yaml",
                    "description": "OpenAISF v1.0 control catalog",
                    "implemented-requirements": implementations,
                }],
            }],
        }
    }
