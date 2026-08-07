# OpenAISF

**An open conformance framework for AI safety and security.**

Created by **Maarten Loose**.
**Specification** CC-BY-4.0 
**Tooling** Apache-2.0
**Status:** Request for Comments, August 2026

---

## 1. What OpenAISF is

A control catalog, an applicability model, an evidence format and a conformance
tool. It defines what an organisation must do to operate AI systems safely, and
it decides mechanically whether the organisation is doing it.

The conformance model is the distinguishing property:

> An AI system is OpenAISF-conformant at tier T **for as long as** it keeps
> producing signed evidence that satisfies tier T's applicable controls.

Conformance is a state, not an event. It has a duration and it expires. A
certificate issued today stops asserting anything once the evidence behind it
stops arriving, without any party deciding that it should.

**Scope.** 20 domains, 112 controls, four assurance tiers from prototype to
frontier. Covers large language models, agents, and classical machine learning
including credit scoring, medical imaging, computer vision and biometrics.

---

## 2. Why conformance expires

Existing assurance regimes are retrospective. SOC 2 Type II examines operating
effectiveness across a review period of three to twelve months and issues a
report after that period closes. ISO/IEC 42001 certifies on a three-year cycle
with annual surveillance audits. Both sample the period rather than observing
all of it.

The interval between the end of an examination period and the moment a report is
read is covered, in practice, by a **bridge letter**: an unaudited statement from
management asserting that nothing material has changed. That instrument exists
because the gap is real and universally acknowledged.

AI systems change faster than the assurance interval. A prompt edit, an upstream
model version change, or a new tool granted to an agent can invalidate a control
within hours. OpenAISF replaces the bridge letter with a signed evidence stream
and an expiry date.

Four specific differences from incumbent assurance:

| | Incumbent | OpenAISF |
|---|---|---|
| Sampling | An assessor tests a sample of the period | Population-level: every request crossing the enforcement point |
| Latency | Report issued after the period closes; the gap is bridged by unaudited assertion | Freshness declared per control; lapse is automatic |
| Verifier | The relying party requests the report and trusts it | The relying party verifies the log without contacting the subject |
| Post-market monitoring | EU AI Act Art. 72 requires it but produces no third-party-checkable artefact | The monitoring is the conformance evidence, signed |

---

## 3. How conformance is decided

Three rules determine every result.

### 3.1 A missing signal is a failure

A control whose required evidence was not produced fails. It does not pass by
absence of contradiction.

A compliant system and a non-functioning evidence pipeline produce identical
silence. Treating silence as an absence of findings passes both.

### 3.2 Declared configuration is checked against observed enforcement

Evidence has two planes:

- **Control plane** — the policy is configured. Declared, signed, versioned.
- **Data plane** — the policy was enforced. Counters and decisions drawn from
  live traffic.

Tier 3 and above require both. Where a control plane record declares a policy
enabled and the corresponding data plane record shows live traffic with zero
enforcement decisions, the control fails:

```
D07-C01  [fail]  declared enabled, but 184203 requests crossed the enforcement
                 point with 0 decisions recorded. A policy that never fired
                 under live traffic was not operating.

lease: revoked
```

This determination requires no assessor. A contradiction between the two planes
is **not resolvable by attestation**: a signed statement from an accountable
person does not override telemetry.

Contradiction is classified as a **disqualifying failure**. It blocks conformance
even where the control is only recommended at that tier, and it revokes the lease
rather than degrading it. Obligation level governs whether a shortfall affects
conformance. It does not govern the treatment of a false statement.

### 3.3 Freshness expires

Each control declares a freshness window, capped by tier. Past the window a
control is stale; past the grace period the lease expires.

No lease outlives its tier ceiling — 365 days at tier 1, 30 days at tier 4 —
regardless of evidence freshness. A subject cannot construct a statement that
never requires renewal.

---

## 4. Verification without the subject's cooperation

Conformance statements are signed and published to an append-only,
hash-chained transparency log.

```bash
openaisf verify --log <log> --system <system-id> --key <public-key>
```

Verification requires the statement, the signer's public key, and a clock. It
does not require an account, a relationship with the subject, or a central
registry. The statement carries its own `stale_after` and `expires_at`, so the
lease state is computed against the verifier's clock at the moment of reading:

```
✗ TruCert · OpenAISF-T2 · expired

This badge no longer asserts conformance. Nobody revoked it;
the lease simply ran out.
```

Log entries are hash-chained. Modifying a past entry invalidates every entry
after it and verification fails. The log operator cannot forge history or make an
expired statement appear current. Refusal to publish is the operator's only
available action and it is externally visible.

**Assurance decay propagates downstream.** A control recorded as inherited from
an upstream component resolves against that component's lease. A stale upstream
lease makes the dependent control stale; an expired or revoked one fails it.
Assurance cannot be inherited above the upstream's verified tier.

---

## 5. What the framework provides, by role

### 5.1 Executive and board

A single portfolio view of lease state across every AI system in scope, computed
from the same evidence the engineering check consumes. The board view and the
conformance run are the same query, so the board view cannot report conformance
while the check fails.

Evidence covers a continuous period rather than a sampled one, which is the form
in which a regulator or customer request is answerable. EU AI Act market
surveillance and GPAI penalty powers became applicable on 2 August 2026;
Annex III high-risk obligations apply from 2 December 2027.

**Limitation.** The framework establishes that controls are operating. It does
not establish that the selected controls are the correct ones for the risk. That
determination remains a management judgement.

### 5.2 Security and risk

The agentic controls are structured as a five-stage chain across domains D07, D15
and D16: bound the authority an agent holds, detect departure from those bounds,
contain, recover, and prove that the first four work.

The proving stage is not optional. Simulated rogue-agent behaviour is injected on
a declared cadence; detectors must fire; the framework records **mean time to
detect** and **mean time to contain** as measured values. Drills that fail are
recorded as failures rather than repeated until they pass.

This addresses a measured gap: approximately 58–59% of enterprises report
monitoring their AI agents and only 37–40% report containment capability.

Domain D15 specifies detection methods that have no classical equivalent,
because an agent declares intent before acting:

- **Intent–action divergence** — declared plan compared against actions taken.
- **Business-purpose divergence** — activity outside the authorised purpose
  recorded under D01-C03, independent of whether it was permitted.
- **Manifest violation** at the attempt, not at the success.
- **Swarm and velocity signatures** — agent identity creation and call rates
  outside human-plausible bounds.
- **Egress anomaly**, explicitly covering reputable public services.
- **Canaries and honeytokens** — near-zero false positive rate, binary in
  evidence.
- **Provenance break** — untrusted content reaching a privileged context, the
  precondition for injection, detectable when the injection is not.
- **Replay sufficiency** — whether the retained trace can reconstruct why an
  agent acted.

### 5.3 Procurement and third-party risk

`openaisf verify` operates on any published badge without the vendor's
involvement. The result reflects the vendor's current lease state rather than
their state at the time a document was issued.

Inherited assurance is the cost mechanism. A control proven by an upstream
certified component is imported by reference and only the delta is assessed. A
deployer building on a certified model inherits most of the model-layer catalog.

Downstream degradation creates the corresponding incentive: a provider whose
badge lapses degrades every dependent within one freshness window.

### 5.4 Engineering

Controls carry a machine-evaluable scope predicate. Applicability is computed
rather than read.

| System | T1 | T2 | T3 |
|---|---:|---:|---:|
| Internal non-agentic LLM application | 4 | 34 | — |
| Agentic, tool-using, handling personal data | 4 | 49 | 77 |

112 controls exist; a typical tier-2 system resolves to 34 and tier 1 to four, of
which one is mandatory. These figures are asserted by tests that fail the build
if they increase.

Evidence originates from infrastructure already in use — AI gateways,
observability platforms, guardrail services, CI — through out-of-tree adapters.
The specification names no vendor as required.

Two constraints that affect implementation:

**No control requires prevention of prompt injection.** Prompt injection is
unsolved at the model layer; adaptive attacks defeat published defences at rates
above 85–90%, a position stated by OpenAI, Anthropic and Google DeepMind.
Controls bound consequence, require detection, and require containment.

**Remediation means changing the system, not the evidence.** The MCP server
cannot write evidence, sign statements or publish, for this reason.

### 5.5 Audit, assessment and policy

The crosswalk is constructed in the inverse of the usual direction. Mapping
outward from a framework's own controls demonstrates what was found and cannot
demonstrate what was missed.

Each in-scope regime is inventoried to its atomic requirements. The coverage
engine walks that inventory and requires every requirement to be either covered
by named controls or excluded with a stated reason. There is no third state, and
an unresolved requirement fails the build.

| Regime | Requirements | Covered | Excluded |
|---|---:|---:|---:|
| CSA AI Controls Matrix v1.1.1 | 247 | 156 | 91 |
| MITRE ATLAS 2026.07 | 178 | 136 | 42 |
| EU AI Act 2024/1689 | 84 | 84 | — |
| NIST AI RMF 1.0 | 72 | 72 | — |
| ISO/IEC 42001:2023 Annex A | 38 | 38 | — |
| MCP-38 threat taxonomy | 38 | 38 | — |
| OWASP Top 10 for LLM Applications 2025 | 10 | 10 | — |
| OWASP Top 10 for LLM Applications 2026 | 10 | 10 | — |
| **Total** | **677** | **544** | **133** |

The 133 exclusions divide into two groups, each entry carrying a written reason:

- **91 CSA AICM entries** — datacentre security, endpoint management,
  cryptography and human resources security. The AICM extends the Cloud Controls
  Matrix and restates a general cloud security baseline. These are satisfied
  through the organisation's existing information security regime and imported as
  inherited assurance under D17-C02.
- **42 MITRE ATLAS techniques** — adversary reconnaissance and resource
  development performed outside the defender's systems, plus six entries that
  describe impacts rather than techniques. No implementable control prevents an
  adversary reading public research or acquiring infrastructure.

Control D19-C05 fails the conformance run where an exclusion is contradicted by
the subject's own telemetry.

**Originality is computed, not asserted.** Regimes are classified as requirement
catalogs (ISO, NIST, EU AI Act, CSA AICM) or threat catalogs (OWASP, ATLAS,
MCP-38). A mapping to a threat catalog establishes relevance to a known attack
and cannot establish that a requirement already exists. Two or more full-strength
mappings classify a control as adopted; one as derived; zero as
OpenAISF-original. **30 of 112 controls are OpenAISF-original** by that
computation.

OSCAL 1.1.2 Assessment Results and Component Definition are exported for GRC and
FedRAMP pipelines.

---

## 6. What the framework does not claim

**It does not guarantee that no AI agent behaves adversarially.** No framework
can. It requires that agent authority is bounded, that departure from those
bounds is detected by detectors proven by drill to fire, that a departure can be
contained by an exercised and timed kill-switch, that damage is recoverable, and
that all four capabilities are proven on a defined cadence.

**It is not the first machine-readable AI compliance work.** OSCAL, the OSCAL AI
compliance evidence proposal, Policy Cards, AIP and DEMM-Bench are prior art and
are cited in the RFC. The distinguishing property is a conformance state that
expires without intervention.

**It does not characterise incumbent assurance as inadequate in general.** SOC 2
Type II, ISO/IEC 42001 and the EU AI Act's post-market monitoring obligations are
substantive. The differences are the four in §2.

---

## 7. Installation and use

```bash
pip install -e .
```

```
openaisf scope    --context <file> --tier T2                    resolve applicability
openaisf check    --context <file> --evidence <dir> --tier T2   evaluate conformance
openaisf publish  --context <file> --evidence <dir> --log <f>   sign and append
openaisf verify   --log <f> --system <id> --key <pub>           verify any badge
openaisf badge    --log <f> --system <id>                       render badge state
openaisf coverage                                               crosswalk coverage
openaisf export   assessment-results | component-definition     OSCAL output
openaisf mcp                                                    MCP server (stdio)
```

Exit code 0 indicates conformance. Every command accepts `--json`.

`examples/` contains a working end-to-end example, including a variant
constructed to trigger the two-plane contradiction rule.

**Dependencies.** Runtime dependencies are `pyyaml` and `jsonschema`. Signing is
an optional extra. The MCP server uses the standard library only. The dependency
list is deliberately minimal because the tooling runs inside other
organisations' CI.

**Tests.** 170. `python -m pytest`.

---

## 8. Framework architecture: three roles

| Name | Definition | Held by |
|---|---|---|
| **OpenAISF** | The open standard: catalog, applicability model, evidence interface, lease format, crosswalk | Open. Created by Maarten Loose |
| **Certifier** | A role defined by the standard: independence requirements, signing duties, mandatory log participation, public disclosure of every certification issued, suspended, expired and revoked. Aligned to ISO/IEC 42006 | Any party meeting the requirements |
| **TruCert** | TruSecure's implementation of the Certifier role, and its commercial assurance product | TruSecure |

A system can reach any tier, including tier 4, self-assessed, with no certifier
involved and no fee. The Certifier requirements are published before any
certifier operates, so the role precedes its first occupant.

**Declared interest.** The creator holds a commercial interest in TruSecure. The
structural mitigation is that the catalog, crosswalk, SoA schema, evidence
schemas, log format and CLI contain no reference to TruSecure other than
attribution. A dependency of any specification artefact on TruSecure would be a
defect.

---

## 9. Attribution and licence

**Specification** (`schema/`, `spec/`, `rfc/`) — CC-BY-4.0.
**Tooling** (`src/`, `tools/`, `tests/`) — Apache-2.0.

Attribution is a licence condition. Derivative works must carry:

> Based on OpenAISF, created by Maarten Loose.

Every conformance report, badge and transparency log entry produced by the
reference implementation carries the attribution line.

**Creator.** Maarten Loose — [LinkedIn](https://www.linkedin.com/) ·
[TruSecure](https://www.trusecure.co)

**Third-party material.** OpenAISF references external regimes by identifier and
reproduces none of their normative text. The ISO/IEC 42001 and CSA AICM
inventories contain no source-authored text. See
[ATTRIBUTIONS.md](ATTRIBUTIONS.md) for the per-regime position, the required
notices, and the open legal actions.

---

## 10. Documents

| | |
|---|---|
| [rfc/RFC-OpenAISF-v1.0.md](rfc/RFC-OpenAISF-v1.0.md) | The specification |
| [spec/catalog/](spec/catalog/) | 112 controls, one file per domain |
| [CHANGELOG.md](CHANGELOG.md) | Changes from v0.1, including which v0.1 claims were incorrect |
| [ATTRIBUTIONS.md](ATTRIBUTIONS.md) | Intellectual property position and required notices |
| [GOVERNANCE.md](GOVERNANCE.md) | Decision-making, and what is deliberately immutable |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Control authoring requirements and rejection criteria |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | |

## 11. Comments

This is a Request for Comments. Open an issue. The most useful submissions, in
order of value:

1. An exclusion in §5.5 that should not be excluded.
2. A control that requires an unachievable outcome, or that is not falsifiable.
3. A factual error in any figure published here.

---

*OpenAISF — created by Maarten Loose.*
