"""An MCP server exposing OpenAISF to agents.

WHY THIS EXISTS. The framework governs agents, and agents are increasingly the
thing doing the engineering work. An agent that can read the catalog, resolve
its own applicability and check its own conformance while it builds is worth
more than one that discovers the requirements in review.

WHAT IT DELIBERATELY CANNOT DO. An agent that can submit evidence about its own
conformance is the model reporting on the model, which is the exact failure D19
exists to prevent. So this server is read-and-check only:

    exposed          catalog, controls, coverage, scoping, conformance checks,
                     badge verification
    NOT exposed      evidence submission, statement signing, log publication

Every tool here is a pure function of inputs the agent already has. None of them
writes anything. Evidence reaches the framework through producer-attested
adapters at the enforcement point (D19-C01, D19-C02) and through no other route,
because an agent asserting its own compliance is not evidence, it is a claim.

Architecture section 15.2 lists a submit_evidence tool and then forbids exactly
that in its next paragraph. The prohibition is correct and the tool list was
wrong; this implementation follows the prohibition.

PROTOCOL. Implements MCP 2026-07-28: stateless, no initialize handshake, every
request carrying its protocol version in _meta, and a mandatory server/discover.
The 2025-11-25 initialize handshake is accepted as a backward-compatibility
probe. Transport is stdio with newline-delimited JSON-RPC, so stdout carries the
protocol and every diagnostic goes to stderr.

Standard library only. No MCP SDK dependency.

OpenAISF — created by Maarten Loose. Licensed under Apache-2.0.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from openaisf.check import evaluate
from openaisf.coverage import (
    compute_coverage,
    compute_provenance,
    load_exclusions,
    threat_regimes,
)
from openaisf.errors import SpecError
from openaisf.evidence import index_evidence, load_evidence
from openaisf.loader import load_catalog, load_inventories
from openaisf.log import TransparencyLog
from openaisf.soa import resolve_soa, to_document
from openaisf.statement import ConformanceStatement

import yaml

from openaisf.applicability import SystemContext

SERVER_NAME = "openaisf"
SERVER_VERSION = "1.0.0a2"
ATTRIBUTION = "OpenAISF — created by Maarten Loose."

SUPPORTED_VERSIONS = ("2026-07-28", "2025-11-25")
LATEST_VERSION = SUPPORTED_VERSIONS[0]

META_PROTOCOL = "io.modelcontextprotocol/protocolVersion"
META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"

# JSON-RPC and MCP error codes. -32020..-32099 is reserved for the MCP
# specification; -32000..-32019 stays implementation-defined.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
UNSUPPORTED_PROTOCOL_VERSION = -32022

LIST_TTL_MS = 300_000

ROOT = Path(__file__).resolve().parents[2]
CATALOG_DIR = ROOT / "spec" / "catalog"
INVENTORY_DIR = ROOT / "spec" / "crosswalk" / "inventories"
EXCLUSIONS_FILE = ROOT / "spec" / "crosswalk" / "exclusions.yaml"

PRINCIPLES = """OpenAISF design principles.

P1 Falsifiability. Every control states a condition under which it fails.
P2 No unachievable normativity. No control may require an outcome the field has
   not achieved. Prompt injection is unsolved at the model layer, so controls
   bound consequence, require detection and require containment. They never
   claim prevention.
P3 Evidence is a byproduct. Anything a control requires must be producible by a
   system that is running correctly, without a compliance activity.
P4 Applicability is computed, not read. Controls declare their own scope.
P5 Inheritance before reimplementation. Duplicated assurance is a defect.
P6 One catalog, many views. No separate executive framework.
P7 Neutrality by construction. No vendor is named as required.
P8 Explain the failure, not the requirement.
P9 Degrade honestly. No state between pass and fail.
"""


class McpError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def _server_info() -> dict:
    return {"name": SERVER_NAME, "version": SERVER_VERSION, "title": "OpenAISF"}


def _meta() -> dict:
    return {META_SERVER_INFO: _server_info()}


def _complete(payload: dict, cacheable: bool = False) -> dict:
    """Every result carries resultType; list results also carry cache hints."""
    result = {"resultType": "complete", "_meta": _meta(), **payload}
    if cacheable:
        result.setdefault("ttlMs", LIST_TTL_MS)
        result.setdefault("cacheScope", "public")
    return result


def _text_result(text: str, structured: Any = None, is_error: bool = False) -> dict:
    payload: dict = {"content": [{"type": "text", "text": text}]}
    if structured is not None:
        payload["structuredContent"] = structured
    if is_error:
        payload["isError"] = True
    return _complete(payload)


# --- catalog access ---------------------------------------------------------


_CACHE: dict[str, Any] = {}


def _catalog() -> list[dict]:
    if "catalog" not in _CACHE:
        _CACHE["catalog"] = load_catalog(CATALOG_DIR)
    return _CACHE["catalog"]


def _context_from(arguments: dict) -> tuple[SystemContext, dict, dict]:
    raw = arguments.get("context")
    if not raw:
        raise McpError(INVALID_PARAMS, "context is required")
    data = yaml.safe_load(raw) if isinstance(raw, str) else dict(raw)
    if not isinstance(data, dict):
        raise McpError(INVALID_PARAMS, "context must be a mapping or YAML mapping")
    inherits = data.pop("inherits", None) or {}
    exclusions = data.pop("exclusions", None) or {}
    known = {"system_id", "roles", "system_class", "autonomy", "data_class",
             "eu_risk", "labels"}
    unknown = set(data) - known
    if unknown:
        raise McpError(
            INVALID_PARAMS, f"unknown scoping keys: {', '.join(sorted(unknown))}"
        )
    try:
        return SystemContext(**data), dict(inherits), dict(exclusions)
    except SpecError as exc:
        raise McpError(INVALID_PARAMS, str(exc)) from exc


# --- tools ------------------------------------------------------------------


def _tool_explain_control(arguments: dict) -> dict:
    control_id = arguments.get("control_id", "")
    control = next((c for c in _catalog() if c["id"] == control_id), None)
    if control is None:
        raise McpError(INVALID_PARAMS, f"no such control: {control_id!r}")

    lines = [
        f"{control['id']} — {control['title']}",
        "",
        f"Normative ({control['rfc2119']}): {control['normative'].strip()}",
        "",
        f"Applies to roles: {', '.join(control['roles'])}",
        f"Lifecycle phases: {', '.join(control['lifecycle'])}",
        f"Tiers: {', '.join(f'{k}={v}' for k, v in sorted(control['tiers'].items()))}",
        f"Verification: {control['verification']['method']}",
    ]
    if control.get("failure_mode"):
        lines += ["", f"What goes wrong: {control['failure_mode'].strip()}"]
    if control.get("rationale"):
        lines += ["", f"Why this control: {control['rationale'].strip()}"]
    return _text_result("\n".join(lines), structured=control)


def _tool_find_controls(arguments: dict) -> dict:
    query = (arguments.get("query") or "").lower()
    domain = arguments.get("domain")
    tier = arguments.get("tier")
    system_class = arguments.get("system_class")

    matches = []
    for control in _catalog():
        if domain and control["domain"] != domain:
            continue
        if tier and control["tiers"].get(tier) not in ("required", "recommended"):
            continue
        if system_class:
            scope = (control.get("applies_when") or {}).get("system_class")
            if scope and system_class not in scope:
                continue
        if query:
            haystack = " ".join([
                control["id"], control["title"], control["normative"],
                control.get("rationale", ""), control.get("failure_mode", ""),
            ]).lower()
            if query not in haystack:
                continue
        matches.append({"id": control["id"], "title": control["title"],
                        "domain": control["domain"],
                        "method": control["verification"]["method"]})

    text = "\n".join(f"{m['id']}  {m['title']}" for m in matches) or "no matches"
    return _text_result(f"{len(matches)} control(s)\n\n{text}", structured=matches)


def _tool_scope(arguments: dict) -> dict:
    context, inherits, exclusions = _context_from(arguments)
    tier = arguments.get("tier", "T2")
    soa = resolve_soa(_catalog(), context, tier, inherits, exclusions)
    document = to_document(soa)
    text = (
        f"Statement of Applicability — {soa.system_id} at {tier}\n"
        f"  in scope        {soa.in_scope}\n"
        f"  applies         {soa.counts['applies']}\n"
        f"  inherited       {soa.counts['inherited']}\n"
        f"  excluded        {soa.counts['excluded']}\n"
        f"  not applicable  {soa.counts['not_applicable']}\n"
        f"  of {len(_catalog())} controls in the catalog"
    )
    return _text_result(text, structured=document)


def _tool_check(arguments: dict) -> dict:
    context, inherits, exclusions = _context_from(arguments)
    tier = arguments.get("tier", "T2")
    evidence_dir = arguments.get("evidence_dir")
    if not evidence_dir:
        raise McpError(INVALID_PARAMS, "evidence_dir is required")

    soa = resolve_soa(_catalog(), context, tier, inherits, exclusions)
    records = load_evidence(Path(evidence_dir))
    foreign = {r.system_id for r in records} - {soa.system_id}
    if foreign:
        raise McpError(
            INVALID_PARAMS,
            f"evidence for other systems found: {', '.join(sorted(foreign))}",
        )
    run = evaluate(_catalog(), soa, index_evidence(records))

    blocking = "\n".join(
        f"  {r.control_id}  [{r.status}]  {r.detail}"
        for r in sorted(run.blocking, key=lambda r: r.control_id)
    )
    text = (
        f"{'CONFORMANT' if run.conformant else 'NOT CONFORMANT'} — "
        f"{run.system_id} at {tier}\n"
        f"lease: {run.lease_state}\n"
        + (f"\nBlocking:\n{blocking}" if blocking else "")
    )
    return _text_result(text, structured={
        "conformant": run.conformant,
        "lease_state": run.lease_state,
        "counts": run.counts,
        "blocking": [r.control_id for r in run.blocking],
    })


def _tool_coverage(_arguments: dict) -> dict:
    controls = _catalog()
    inventories = load_inventories(INVENTORY_DIR)
    regimes, _ = compute_coverage(controls, inventories, load_exclusions(EXCLUSIONS_FILE))
    provenance = compute_provenance(controls, threat_regimes(inventories))
    originals = sum(1 for v in provenance.values() if v == "OpenAISF-original")

    rows = "\n".join(
        f"  {r.regime:<20}{r.total:>6}{r.covered:>9}{r.excluded:>10}"
        f"{len(r.uncovered):>6}"
        for r in regimes
    )
    complete = all(r.is_complete for r in regimes)
    text = (
        f"{'regime':<22}{'total':>6}{'covered':>9}{'excluded':>10}{'gap':>6}\n{rows}\n\n"
        f"{'complete' if complete else 'INCOMPLETE'} — "
        f"{originals} of {len(controls)} controls are OpenAISF-original"
    )
    return _text_result(text, structured={
        "complete": complete,
        "controls": len(controls),
        "openaisf_original": originals,
        "regimes": [{"regime": r.regime, "total": r.total, "covered": r.covered,
                     "excluded": r.excluded, "gap": len(r.uncovered)}
                    for r in regimes],
    })


def _tool_verify_badge(arguments: dict) -> dict:
    log_path = arguments.get("log")
    system_id = arguments.get("system_id")
    if not log_path or not system_id:
        raise McpError(INVALID_PARAMS, "log and system_id are required")

    log = TransparencyLog(Path(log_path))
    log.verify_chain()
    entry = log.latest_for(system_id)
    if entry is None:
        raise McpError(INVALID_PARAMS, f"no log entry for {system_id}")

    statement = ConformanceStatement.from_dict(entry.statement)
    now = datetime.now(timezone.utc)
    state = statement.state_at(now)
    authenticated = bool(
        statement.signature and statement.signature.provides_authenticity
    )
    text = (
        f"{system_id}\n"
        f"  tier          {statement.tier}\n"
        f"  state         {state.upper()}\n"
        f"  authenticated {authenticated}\n"
        f"  expires       {statement.expires_at.isoformat()}\n"
        f"  checked at    {now.isoformat()}"
    )
    return _text_result(text, structured={
        "system_id": system_id, "tier": statement.tier, "state": state,
        "authenticated": authenticated,
        "expires_at": statement.expires_at.isoformat(),
        "checked_at": now.isoformat(),
    })


_SCOPE_SCHEMA = {
    "type": "object",
    "properties": {
        "context": {
            "type": "string",
            "description": "Scoping file contents as YAML: system_id, roles, "
                           "system_class, autonomy, data_class, eu_risk, and "
                           "optionally inherits and exclusions.",
        },
        "tier": {"enum": ["T1", "T2", "T3", "T4"], "default": "T2"},
    },
    "required": ["context"],
}

TOOLS: list[tuple[str, str, dict, Callable[[dict], dict]]] = [
    (
        "openaisf_explain_control",
        "Explain one OpenAISF control: what it requires, which tiers and roles "
        "it binds, how it is verified, the real failure it exists to prevent, "
        "and why it is written the way it is.",
        {
            "type": "object",
            "properties": {"control_id": {"type": "string",
                                          "description": "e.g. D07-C01"}},
            "required": ["control_id"],
        },
        _tool_explain_control,
    ),
    (
        "openaisf_find_controls",
        "Search the control catalog by free text, domain, tier or system class. "
        "Use this to find which controls bear on a change before making it.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "domain": {"type": "string", "description": "e.g. D07"},
                "tier": {"enum": ["T1", "T2", "T3", "T4"]},
                "system_class": {"type": "string",
                                 "description": "e.g. agentic, llm, classical_ml"},
            },
        },
        _tool_find_controls,
    ),
    (
        "openaisf_scope",
        "Resolve a Statement of Applicability: which controls actually apply to "
        "a described system at a tier. Read-only; writes nothing.",
        _SCOPE_SCHEMA,
        _tool_scope,
    ),
    (
        "openaisf_check",
        "Evaluate conformance against already-collected evidence. Reads evidence "
        "produced by adapters; it cannot create or modify evidence.",
        {
            "type": "object",
            "properties": {
                **_SCOPE_SCHEMA["properties"],
                "evidence_dir": {
                    "type": "string",
                    "description": "Directory of evidence records emitted by adapters.",
                },
            },
            "required": ["context", "evidence_dir"],
        },
        _tool_check,
    ),
    (
        "openaisf_coverage",
        "Report crosswalk coverage against ISO 42001, NIST AI RMF, the EU AI Act, "
        "OWASP, MITRE ATLAS, CSA AICM and MCP-38.",
        {"type": "object", "properties": {}},
        _tool_coverage,
    ),
    (
        "openaisf_verify_badge",
        "Verify a conformance badge from a transparency log, including whether "
        "its lease is still current at this moment. Works on anyone's badge.",
        {
            "type": "object",
            "properties": {
                "log": {"type": "string"},
                "system_id": {"type": "string"},
            },
            "required": ["log", "system_id"],
        },
        _tool_verify_badge,
    ),
]

TOOL_HANDLERS = {name: handler for name, _d, _s, handler in TOOLS}


# --- resources --------------------------------------------------------------


def _resource_catalog() -> str:
    return json.dumps(_catalog(), indent=2)


def _resource_domains() -> str:
    domains: dict[str, list[str]] = {}
    for control in _catalog():
        domains.setdefault(control["domain"], []).append(control["id"])
    return json.dumps(domains, indent=2, sort_keys=True)


RESOURCES: list[tuple[str, str, str, str, Callable[[], str]]] = [
    ("openaisf://principles", "Design principles",
     "The nine constitutional principles a control must obey.",
     "text/plain", lambda: PRINCIPLES),
    ("openaisf://catalog", "Control catalog",
     "Every OpenAISF control with its normative text, scope and crosswalk.",
     "application/json", _resource_catalog),
    ("openaisf://catalog/domains", "Domain index",
     "Control identifiers grouped by domain.",
     "application/json", _resource_domains),
]

RESOURCE_HANDLERS = {uri: handler for uri, _n, _d, _m, handler in RESOURCES}
RESOURCE_TYPES = {uri: mime for uri, _n, _d, mime, _h in RESOURCES}


# --- prompts ----------------------------------------------------------------

PROMPTS: list[tuple[str, str, list[dict], Callable[[dict], str]]] = [
    (
        "openaisf_scope_interview",
        "Work out the scoping facts for a system so its Statement of "
        "Applicability can be resolved.",
        [{"name": "system_description", "description": "What the system does",
          "required": True}],
        lambda a: (
            "Establish the OpenAISF scoping facts for this system, asking only "
            "what you cannot infer:\n\n"
            f"System: {a.get('system_description', '')}\n\n"
            "Determine: system_id; roles held (provider, deployer, supplier, "
            "operator); system_class (llm, agentic, classical_ml, cv, biometric, "
            "generative_media, recommender, rl); autonomy (none, tool_use, "
            "planning, self_directed, multi_agent); data_class touched; and "
            "eu_risk classification.\n\n"
            "Autonomy and data class do most of the work in reducing scope, so "
            "be precise about them. Then call openaisf_scope with the result."
        ),
    ),
    (
        "openaisf_remediate_control",
        "Work out what to change so a failing control passes.",
        [{"name": "control_id", "description": "e.g. D07-C01", "required": True},
         {"name": "failure", "description": "What the check reported",
          "required": False}],
        lambda a: (
            f"Control {a.get('control_id', '')} is not satisfied.\n"
            f"Reported: {a.get('failure', 'not stated')}\n\n"
            "Call openaisf_explain_control first and read the failure_mode: it "
            "names the real incident the control prevents, which usually makes "
            "the right fix obvious.\n\n"
            "Then propose a change to the system, not to the evidence. If the "
            "control is emitted, the fix is that the enforcement point starts "
            "doing the thing and reporting it — never that a record is written "
            "saying it did."
        ),
    ),
    (
        "openaisf_incident_triage",
        "Triage a suspected agent incident against the containment chain.",
        [{"name": "symptoms", "description": "What was observed", "required": True}],
        lambda a: (
            f"Observed: {a.get('symptoms', '')}\n\n"
            "Triage against the rogue-agent control chain in order.\n\n"
            "Bound: what authority did the agent hold — capability manifest, "
            "action budget, delegation depth, egress allowlist, credential "
            "lifetime?\n"
            "Detect: which detectors should have fired and did they — "
            "intent-action divergence, manifest violation, swarm and velocity "
            "signature, egress anomaly, canary, business-purpose divergence?\n"
            "Contain: which containment layers are available and have they been "
            "exercised? Terminating a session leaves credentials it minted "
            "valid unless they are revoked separately.\n"
            "Recover: can you restore a pinned state, and what is the rotation "
            "scope?\n"
            "Prove: is the retained trace sufficient to reconstruct why the "
            "agent acted?\n\n"
            "Then check reporting thresholds under D16-C05."
        ),
    ),
]

PROMPT_HANDLERS = {name: handler for name, _d, _a, handler in PROMPTS}


# --- dispatch ---------------------------------------------------------------


def _check_protocol_version(request: dict) -> None:
    meta = (request.get("params") or {}).get("_meta") or {}
    requested = meta.get(META_PROTOCOL)
    if requested and requested not in SUPPORTED_VERSIONS:
        raise McpError(
            UNSUPPORTED_PROTOCOL_VERSION,
            f"unsupported protocol version {requested!r}",
            {"supported": list(SUPPORTED_VERSIONS)},
        )


def handle(request: dict) -> dict | None:
    """Handle one JSON-RPC request. Returns None for notifications."""
    method = request.get("method")
    params = request.get("params") or {}

    if method is None:
        raise McpError(INVALID_REQUEST, "missing method")

    if method.startswith("notifications/"):
        return None

    _check_protocol_version(request)

    if method == "server/discover":
        return _complete({
            "protocolVersions": list(SUPPORTED_VERSIONS),
            "serverInfo": _server_info(),
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            "instructions": (
                "OpenAISF conformance. Read the catalog, resolve applicability, "
                "check conformance and verify badges. This server cannot submit "
                "evidence, sign statements or publish: an agent asserting its own "
                "conformance is a claim, not evidence."
            ),
        })

    if method == "initialize":
        # Backward-compatibility probe for 2025-11-25 clients.
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_VERSIONS else "2025-11-25"
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            "serverInfo": _server_info(),
        }

    if method == "tools/list":
        return _complete({
            "tools": [
                {"name": name, "description": description, "inputSchema": schema}
                for name, description, schema, _h in TOOLS
            ]
        }, cacheable=True)

    if method == "tools/call":
        name = params.get("name")
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            raise McpError(INVALID_PARAMS, f"no such tool: {name!r}")
        try:
            return handler(params.get("arguments") or {})
        except McpError:
            raise
        except SpecError as exc:
            return _text_result(f"error: {exc}", is_error=True)

    if method == "resources/list":
        return _complete({
            "resources": [
                {"uri": uri, "name": name, "description": description,
                 "mimeType": mime}
                for uri, name, description, mime, _h in RESOURCES
            ]
        }, cacheable=True)

    if method == "resources/read":
        uri = params.get("uri")
        handler = RESOURCE_HANDLERS.get(uri)
        if handler is None:
            raise McpError(INVALID_PARAMS, f"no such resource: {uri!r}")
        return _complete({
            "contents": [{"uri": uri, "mimeType": RESOURCE_TYPES[uri],
                          "text": handler()}]
        }, cacheable=True)

    if method == "prompts/list":
        return _complete({
            "prompts": [
                {"name": name, "description": description, "arguments": arguments}
                for name, description, arguments, _h in PROMPTS
            ]
        }, cacheable=True)

    if method == "prompts/get":
        name = params.get("name")
        handler = PROMPT_HANDLERS.get(name)
        if handler is None:
            raise McpError(INVALID_PARAMS, f"no such prompt: {name!r}")
        text = handler(params.get("arguments") or {})
        return _complete({
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}]
        })

    raise McpError(METHOD_NOT_FOUND, f"unknown method: {method!r}")


def _response(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, exc: McpError) -> dict:
    error: dict = {"code": exc.code, "message": exc.message}
    if exc.data is not None:
        error["data"] = exc.data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def serve(stdin=None, stdout=None) -> int:
    """Newline-delimited JSON-RPC over stdio.

    stdout carries the protocol and nothing else. Diagnostics go to stderr,
    which is also where the specification now directs logging on stdio.
    """
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout

    for line in stdin:
        line = line.strip()
        if not line:
            continue

        request_id = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            result = handle(request)
            if result is None:
                continue
            message = _response(request_id, result)
        except json.JSONDecodeError as exc:
            message = _error(None, McpError(PARSE_ERROR, f"parse error: {exc}"))
        except McpError as exc:
            message = _error(request_id, exc)
        except Exception as exc:  # noqa: BLE001 - the loop must survive
            print(f"openaisf-mcp: {type(exc).__name__}: {exc}", file=sys.stderr)
            message = _error(request_id, McpError(INTERNAL_ERROR, str(exc)))

        stdout.write(json.dumps(message) + "\n")
        stdout.flush()

    return 0
