# OpenAISF — The Open AI Safety Framework

> **The controls layer for the AI runtime stack.**
> Free. Open. Machine-readable. Conformance is a test that passes or fails.

[![Status: Draft v0.1](https://img.shields.io/badge/status-draft%20v0.1-orange)](rfc/RFC-OpenAISF-v0.1.md)
[![License: CC-BY-4.0 (spec)](https://img.shields.io/badge/spec-CC--BY--4.0-blue)](LICENSE)
[![License: Apache-2.0 (code)](https://img.shields.io/badge/code-Apache--2.0-green)](LICENSE)

---

## What is OpenAISF?

OpenAISF is a **free, open, machine-readable AI safety standard**. The standard
is published as a versioned YAML catalog of controls, and conformance is
checked by an open CLI:

```bash
$ openaisf check --tier T1
✓ OpenAISF-T1: CONFORMANT (3 controls passed)     # exit code 0
```

**An AI system is OpenAISF-conformant at tier T when `openaisf check` exits 0.**

## Why does it exist?

Every existing AI safety standard is either **prose + paperwork** (ISO 42001,
NIST RMF — heavy, vague, expensive, no developer path) or a **threat list with
no controls** (OWASP Top 10, MITRE ATLAS). None of them govern the
**runtime / inference-gateway layer** that every production AI team actually
depends on — model routing, failover, cost caps, guardrails, telemetry,
substitution, rollback, tool/MCP calls (the LiteLLM / Portkey / Langfuse /
Lakera / MCP layer). That is a one-layer-wide blind spot across the entire
field. OpenAISF fills it.

| Coverage | ISO 42001 | NIST RMF | OWASP | ATLAS | CSA AICM | **OpenAISF** |
|---|---|---|---|---|---|---|
| Organizational governance | ✅ | ✅ | — | — | partial | ✅ |
| Application/dev risk | partial | partial | ✅ | ✅ | ✅ | ✅ |
| **Runtime / gateway layer** | — | — | — | — | — | **✅** |
| **Tool / MCP security** | — | — | — | — | — | **✅** |
| **Model substitution safety** | — | — | — | — | — | **✅** |
| **Live evals / telemetry spec** | — | vague | — | — | — | **✅** |
| **Cost-as-governance** | — | — | vuln only | — | — | **✅** |
| Machine-readable + executable | — | — | — | — | partial | ✅ |
| SME tier (free, instant) | — | free, no cert | free | free | — | ✅ |

## The three first-of-kind lead claims

- **D10 — Tool & MCP Security.** *The MCP governance standard.* MCP shipped
  after every framework; OpenAISF is first to govern it.
- **D4-MPE — Model Port Equivalence.** *Substitution safety.* Swapping
  GPT-4 → Claude silently breaks certified properties; OpenAISF makes the
  substitution a controlled, re-validated event.
- **D9-LTE — LLM Telemetry & Live Evaluation.** The canonical inference-event
  log + online evals that EU AI Act Art. 72 demands but doesn't specify.

**25 of 54 controls are OpenAISF-original** — no incumbent equivalent.

## The four tiers

| Tier | Who | Philosophy | Time to conform |
|---|---|---|---|
| **T1 — Solo/Indie** | Individual devs, prototypes, research | "Don't be reckless." | Hours |
| **T2 — Startup/SME** | Seed–Series B, non-high-risk AI | "Demonstrable care." | 1–4 weeks |
| **T3 — Enterprise** | Established companies, higher-risk use | "Evidence and accountability." | 1–3 months |
| **T4 — Frontier** | Frontier labs, safety-critical, GPAI providers | "Prove it, repeatedly." | 3–6 months |

Tiers compose: a Tier-3 system using a Tier-1 component inherits that
component's Tier-1 obligations.

## Quick start

```bash
# Requires Python 3.9+ and PyYAML
pip install pyyaml

# Scaffold an OpenAISF project
python cli/openaisf.py init --project ./my-ai-system
cd my-ai-system

# Fill in openaisf.yaml + add a POLICY.md + AI disclosure, then:
python ../cli/openaisf.py check --tier T1

# Badge for your README:
python ../cli/openaisf.py badge --tier T1
```

A conformant project gets a verifiable badge keyed to its tier — the trust
signal NIST RMF refuses to issue, at a fraction of ISO 42001's cost.

## Repository layout

```
spec/
  openaisf-controls.yaml    ← the standard: 54 controls, 11 domains, T1-T4
  openaisf-crosswalk.yaml   ← mappings to ISO 42001 / NIST RMF / OWASP / ATLAS /
                              EU AI Act / CSA AICM / SAIF / OSAA SAFE
cli/
  openaisf.py               ← reference conformance implementation
rfc/
  RFC-OpenAISF-v0.1.md      ← the public Request for Comments
```

## Status

**Draft v0.1 — Request for Comments.** The spec and a working CLI prototype
(T1 checks) exist. We invite framework authors, AI labs, runtime-layer
vendors, GRC providers, insurers, and regulators to comment on the RFC.

See [rfc/RFC-OpenAISF-v0.1.md](rfc/RFC-OpenAISF-v0.1.md) for the specific
questions we're asking the community.

## Governance & licensing

- The **spec** (`spec/`) is licensed **CC-BY-4.0**.
- The **reference CLI** (`cli/`) is licensed **Apache-2.0**.
- OpenAISF is intended to live under **open, neutral governance**.
  See [GOVERNANCE.md](GOVERNANCE.md).

OpenAISF is **complementary, not competitive**, to most incumbents — it
implements NIST RMF principles with actual controls + a cert, operationalizes
ISO 42001's intent at a fraction of the cost, adds the control layer OWASP
and ATLAS lack, specifies what EU AI Act Art. 12/72 leave unspecified, emits
OSAA-SAFE-compatible incident reports, and is the conformance standard the
runtime-defense vendor category (Lakera / Invariant / Prompt Security) can
certify against.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Comments via issues and PRs are welcome.

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
