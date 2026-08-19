# OpenAISF

**An open conformance framework for AI safety and security.**

**Specification** CC-BY-4.0<br>
**Tooling** Apache-2.0<br>
**Status:** Request for Comments, August 2026

> **This document is the why and the how.** For the numbers, the differentiator
> and the case for adopting it, see **[openaisf.org](https://openaisf.org)**.
> For the normative specification, see
> [rfc/RFC-OpenAISF-v1.0.md](rfc/RFC-OpenAISF-v1.0.md).

---

## Part I — Why

### 1. The three gaps

Every AI governance framework in wide use was designed before agents shipped in
production. Three consequences follow, and they are why organisations pass
audits and are harmed anyway.

**They govern models. Organisations run agents.** An agent holds credentials,
calls tools, and acts. Nothing in ISO/IEC 42001, NIST AI RMF or the EU AI Act
asks what an agent is permitted to reach, how you would notice it going outside
that, or whether anyone has ever verified you can stop it. The measured
consequence: 58–59% of enterprises report monitoring their AI agents and only
37–40% report containment capability.

**They govern databases. AI creates new data.** Prompt logs, embeddings,
semantic caches, fine-tuning corpora. These are stores of sensitive data that
appear on no data map, inherited a logging retention policy because an
engineering team created them as telemetry, and are not reached by any deletion
process. Data governance was written for records that are *copied*; an embedding
is *computed*, and classification is lost at the moment of derivation.

**They certify a moment. Systems change hourly.** A prompt edit, an upstream
model version change, or a new tool granted to an agent can invalidate a control
within the hour. The certificate remains valid for a year. The industry knows
this and papers over it with a **bridge letter** — an unaudited management
statement that nothing material has changed since the audit closed.

### 2. What follows from that

Two design commitments. Everything else in the framework is machinery for them.

**Conformance has to be a state, not an event.**

> An AI system is OpenAISF-conformant at tier T for as long as it keeps
> producing signed evidence that satisfies tier T's applicable controls.

Stop producing evidence and the badge goes stale, then expires. Nobody decides
this. A conformance statement carries its own `stale_after` and `expires_at`, so
the state is computed against the *reader's* clock — which means a lapsed badge
reads as lapsed in somebody else's README, with nobody notified and nobody able
to prevent it.

**The framework has to cover risks the incumbents miss, or it is a mapping
exercise.** 36 of 118 controls have no incumbent equivalent. The full table of
what they cover is on [the website](https://openaisf.org/#gaps); the reasoning
behind several of them is in §4.

### 3. Why it is free

The specification is CC-BY-4.0 and the tooling Apache-2.0, and any tier —
including tier 4 — is reachable self-assessed, with no certifier and no fee.

That is not generosity. A conformance standard is worth something only when
relying parties recognise it, and nothing gates recognition faster than a
paywall between an engineer and the control text. The commercial layer sits
where independent assurance genuinely costs money to produce: **TruCert**,
TruSecure's implementation of the Certifier role, sells a counter-signature and
the work of running the evidence machinery. It sells nothing that gates access
to the standard.

**Declared interest.** The creator holds a commercial interest in TruSecure. The
mitigation is structural rather than a promise: the catalog, crosswalk, SoA
schema, evidence schemas, log format and CLI contain no reference to TruSecure
other than attribution. A dependency of any specification artefact on TruSecure
is a defect and should be filed as one.

### 4. Decisions worth arguing with

The choices below are the ones most likely to be contested. Each is stated with
its reasoning so that disagreement can be specific.

#### No control requires preventing prompt injection

Prompt injection is unsolved at the model layer. Adaptive attacks defeat
published defences at rates above 85–90%, and OpenAI, Anthropic and Google
DeepMind all say so. A control reading *"the system shall prevent prompt
injection"* cannot be satisfied, which makes every conformant system a liar and
the framework worthless.

So controls bound what a successful injection can reach, require detection by
detectors **proven by drill to fire**, and require containment that has been
exercised and timed. This is principle **P2**: no control may require an outcome
the field has not achieved.

#### Originality is computed, never asserted

The count of original controls is a public claim about the framework, and the
pressure on it runs one way. So it is derived from the crosswalk rather than
maintained by hand, and a hand-written `provenance` value that disagrees with
the computation is an **error**, not an override.

Regimes are classified as *requirement* catalogs (ISO, NIST, EU AI Act, CSA
AICM) or *threat* catalogs (OWASP, ATLAS, MCP-38). A threat catalog describes
attacks and imposes no obligations, so a mapping to one can establish relevance
but never that something is already required. Two or more full-strength mappings
means `adopted`; one means `derived`; zero means `OpenAISF-original`. The
default is `full`, so claiming novelty costs an explicit, reviewable edit while
disclaiming it is free.

An earlier version of this rule counted *how many regimes a control touched*,
which conflated breadth of mapping with derivativeness and understated the
original set. That is recorded in [CHANGELOG.md](CHANGELOG.md) rather than
quietly fixed.

#### The crosswalk is built backwards, and the exclusions are published

Mapping outward from your own controls shows what you found. It can never show
what you missed. So each regime is inventoried down to its atomic requirements
and the engine walks *that* list, requiring every requirement to be covered by
named controls or excluded with a written reason. There is no third state, and
an unresolved requirement fails the build.

133 requirements are excluded and every one carries its reason. That is the most
consequential judgement in the framework, and it is published precisely so it
can be attacked. If an exclusion is wrong, that is the most useful thing anyone
can tell us.

#### A missing signal is a failure, not silence

A compliant system and a completely broken evidence pipeline emit identical
silence. Treating silence as an absence of findings passes both, so a control
whose required evidence was never produced fails.

#### Fabrication is disqualifying, whatever the obligation level

Where a control plane record declares a policy enabled and the data plane shows
live traffic with zero enforcement decisions, the control fails — and **an
attestation cannot resolve it**. A signed statement from an accountable person
does not override telemetry.

That failure blocks conformance even where the control is only *recommended* at
that tier, and revokes the lease rather than degrading it. Obligation level
governs whether a shortfall affects conformance. It does not govern the
treatment of a false statement.

#### Agents may read and check, but never assert

The MCP server exposes the catalog, applicability resolution, conformance
checking and badge verification. It exposes **no** tool that writes evidence,
signs a statement or appends to the log, because an agent submitting evidence
about its own conformance is the model reporting on the model. A test fails the
build if a tool name contains a writing verb.

---

## Part II — How it works

### 5. The model in five pieces

**The catalog.** 118 controls across 20 domains. Each carries normative text, a
machine-evaluable scope predicate, a verification method, the evidence it
expects, its crosswalk, and — required, not decorative — the real failure it
exists to prevent, citing a named incident where one exists.

**The Statement of Applicability.** Controls declare their own scope over system
class, autonomy level, data class and risk classification, so the reader never
decides whether a control applies to them. A typical internal non-agentic LLM
application resolves to **35 controls of 118**; tier 1 resolves to **three**, of
which one is mandatory. Both figures are enforced by tests that fail the build
if they rise.

**Evidence, in two planes.** The *control plane* states what is configured. The
*data plane* reports what happened to live traffic. Tier 3 and above require
both, and the pair is what makes a false claim detectable without an assessor.

**The lease.** Each control declares a freshness window, capped by tier. Past the
window a control is stale; past the grace period the lease expires. No lease
outlives its tier ceiling — 365 days at tier 1 down to 30 at tier 4 — so a
subject cannot construct a statement that never needs renewing.

**The transparency log.** Append-only and hash-chained. Verification needs the
statement, a public key and a clock: no account, no relationship with the
subject, no registry that could be captured. Modifying a past entry invalidates
every entry after it.

### 6. Tiers

| | Who | Assurance | Time to first badge |
|---|---|---|---|
| **T1** | Prototypes, research code, no production users | Self-asserted | Minutes |
| **T2** | Production traffic, non-high-risk use | Self-asserted; data plane where a gateway exists | Days |
| **T3** | Regulated sectors, EU AI Act high-risk, public sector | Control **and** data plane; independent certifier | Weeks |
| **T4** | Frontier labs, GPAI with systemic risk, high-autonomy agents at scale | Continuous, independently witnessed | Months |

Tiers compose downward: a T3 system built on a T1-conformant component inherits
only T1 assurance for that component. Assurance cannot be laundered upward
through a dependency.

---

## Part III — How to use it

### 7. Install

```bash
git clone https://github.com/OpenAISF-org/openaisf && cd openaisf
python -m venv .venv && ./.venv/bin/pip install -e '.[dev]'
```

Runtime dependencies are `pyyaml` and `jsonschema`. That is the entire list,
deliberately, because this runs inside other organisations' CI. Signing is an
optional extra; the MCP server is standard library only.

### 8. Work out what applies to you

Describe the system once, in a scoping file:

```yaml
# system.yaml
system_id: urn:openaisf:system:acme-support-agent
roles: [deployer]
system_class: [llm, agentic]
autonomy: tool_use
data_class: [internal, personal]
eu_risk: [limited]

inherits: {}     # controls an upstream certified component already proves
exclusions: {}   # controls that apply but are deliberately not implemented
```

```bash
openaisf scope --context system.yaml --tier T2
```

```
Statement of Applicability — urn:openaisf:system:acme-support-agent at T2

  applies            51
  inherited           0
  excluded            0
  not applicable     67
  ---------------------
  in scope           51  of 118 in the catalog
```

The SoA is not a document written for an auditor. It **is** the check plan, and
the next command executes it.

### 9. Collect evidence

Evidence comes from infrastructure you already run — AI gateways, observability
platforms, guardrail services, CI — through out-of-tree adapters. The
specification names no vendor as required.

`tools/adapters/gateway_adapter.py` is the reference implementation and
documents the contract by example:

1. Read from an enforcement point you do not control; emit records validating
   against `schema/evidence.schema.json`.
2. One record per (control, plane, window). Never infer one plane from the other
   — having two is the entire point.
3. **Sign at the producer**, before transmission or aggregation. An aggregator
   signature attests only that the aggregator received something.
4. **Never invent an observation.** If the source cannot answer, omit the record
   and let the control fail as a missing signal. Emitting a plausible zero is
   fabrication, and `D19-C03` exists to catch exactly that.

```bash
python tools/adapters/gateway_adapter.py summary.json ./evidence \
    --key producer.pem --key-id gateway-prod
```

From tier 3 upward an unsigned record is treated as absent, and the check states
which of three things went wrong: unsigned, signed with a scheme that proves
integrity but not authorship, or a signature that does not verify.

### 10. Check, publish, verify

```bash
openaisf check --context system.yaml --evidence ./evidence --tier T2
```

Exit code 0 means conformant. When it is not, the output says why in terms of
the system rather than the paperwork:

```
D07-C01  [fail]  declared enabled, but 184203 requests crossed the enforcement
                 point with 0 decisions recorded. A policy that never fired
                 under live traffic was not operating.

lease: revoked
```

Then sign a statement, append it to a log, and let anyone verify it:

```bash
openaisf publish --context system.yaml --evidence ./evidence \
                 --log openaisf-log.jsonl --key signer.key
openaisf verify  --log openaisf-log.jsonl --system urn:… --key signer.pub
openaisf badge   --log openaisf-log.jsonl --system urn:…
```

Every command accepts `--json` for CI. `openaisf export assessment-results`
emits OSCAL 1.1.2 for GRC pipelines, and `openaisf mcp` runs the MCP server.

### 11. Adopting it in an organisation

A staged path that produces something useful at every step.

1. **Scope one real system at T1.** Three controls, one mandatory. This exists to
   prove the loop runs end to end, not to produce assurance.
2. **Point one adapter at your gateway.** Whatever is already in the request
   path. This is where evidence stops being a document.
3. **Run `check` in CI at T2 and let it fail.** The failures are the work queue,
   and they are stated as system defects rather than as missing paperwork.
4. **Publish, and hand a customer the verify command.** The procurement
   conversation changes here, because they stop asking you for a PDF.
5. **Ask your model provider for their badge.** Inherited controls are the cost
   lever: you import what they already proved instead of re-proving it.

### 12. Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first — it states what makes a good
control and what will be refused. Two gates are hard:

```bash
python -m pytest                      # 172 tests
openaisf coverage                     # must exit 0 — no unresolved requirement
```

The most valuable contributions, in order:

1. An exclusion in the crosswalk that should not be excluded.
2. A control that requires an unachievable outcome, or that is not falsifiable.
3. A factual error in any published figure.

Arguing that the framework is too strict is welcome. Bring the system you are
trying to certify.

---

## Documents

| | |
|---|---|
| **[openaisf.org](https://openaisf.org)** | The case for adopting it, with the numbers |
| [rfc/RFC-OpenAISF-v1.0.md](rfc/RFC-OpenAISF-v1.0.md) | The normative specification |
| [spec/catalog/](spec/catalog/) | 118 controls, one file per domain |
| [CHANGELOG.md](CHANGELOG.md) | What changed, including which v0.1 claims were wrong |
| [ATTRIBUTIONS.md](ATTRIBUTIONS.md) | How this references other standards without reproducing them |
| [GOVERNANCE.md](GOVERNANCE.md) | Who decides, and what is deliberately immutable |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Control authoring requirements and rejection criteria |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | |

The website is a separate repository:
[openaisf/website](https://github.com/openaisf/website).

## Attribution

Specification (`schema/`, `spec/`, `rfc/`) — **CC-BY-4.0**.
Tooling (`src/`, `tools/`, `tests/`) — **Apache-2.0**.

Attribution is a licence condition, not a courtesy. Derivative works must carry:

> Based on OpenAISF, created by Maarten Loose.

Every conformance report, badge and log entry the reference implementation
produces carries that line.

[LinkedIn](https://www.linkedin.com/in/mloose/) · [TruSecure](https://www.trusecure.co)

OpenAISF references external regimes by identifier and reproduces none of their
normative text. See [ATTRIBUTIONS.md](ATTRIBUTIONS.md) for the per-regime
position and required notices.
