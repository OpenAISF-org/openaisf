# RFC: OpenAISF v1.0

**An open conformance framework for AI safety and security.**

Created by Maarten Loose.
Status: **Request for Comments** — draft for public review, 7 August 2026.
Creator: Maarten Loose · [linkedin.com/in/mloose](https://www.linkedin.com/in/mloose/) · [trusecure.co](https://www.trusecure.co)
Specification CC-BY-4.0. Reference tooling Apache-2.0.

---

## 1. Abstract

Every AI governance regime in use today answers the question *"were you compliant when somebody looked?"* OpenAISF answers *"are you compliant right now?"*, and makes the answer checkable by a stranger.

> **An AI system is OpenAISF-conformant at tier T for as long as it keeps producing signed evidence that satisfies tier T's applicable controls.**

Conformance is a state with a heartbeat, not an event that produced a document. The engineer-legible form, which is how this is meant to travel: **your compliance has a TTL.**

This RFC specifies 118 controls across 20 domains, 36 of which have no incumbent equivalent, a computed applicability model, a two-plane evidence interface, and a conformance lease that expires on its own. It is accompanied by a reference implementation that runs the whole loop.

Comments are invited on all sections, and specifically on §9.

---

## 2. What this is not

Stated first, because each of the following is a claim OpenAISF does not make and should not be read as making.

**This is not a promise that no agent goes rogue.** Nothing can promise that, and a standard implying otherwise would be destroyed by the first incident. What it requires is that agent authority is bounded, that departure from those bounds is detected by detectors proven to fire, that a departure can be contained by a kill-switch that has been exercised and timed, that damage is recoverable, and that all four are proven on a clock — or the certificate expires.

**This is not the first machine-readable AI compliance work.** By August 2026 that claim is simply false. OSCAL is on its way to being mandatory for FedRAMP providers; published research proposes OSCAL as the interchange format for AI compliance evidence with a working Apache-2.0 SDK; Policy Cards claims to be the first machine-readable governance format combining ISO 42001 with runtime enforcement; AIP addresses verifiable agent delegation across MCP and A2A; DEMM-Bench benchmarks agent-runtime governance-evidence sufficiency. Appendix B cites them. OpenAISF absorbs that work rather than competing with it — it exports OSCAL, and it takes agent-identity and threat-taxonomy work as inputs.

**This is not a claim that incumbent assurance is naïve.** SOC 2 Type II examines operating effectiveness across a review period. ISO/IEC 42001 runs annual surveillance audits inside a three-year cycle. The EU AI Act's Article 72 *requires* post-market monitoring and Article 73 requires serious-incident reporting. Continuous obligation already exists on paper. §3 states precisely where the difference actually lies.

---

## 3. What is different, precisely

Four places, and no others.

| | Incumbent assurance | OpenAISF |
|---|---|---|
| **Sampling** | An auditor tests a sample of the period | Population-level: every request crossing the enforcement point |
| **Latency** | Report issued after the window closes; the gap to today is covered by a **bridge letter, which is unaudited management assertion** | Freshness declared per control; lapse is automatic |
| **Verifier** | The relying party must request the report and trust it | The relying party verifies the log without asking the certified organisation |
| **Post-market monitoring** | AI Act Art. 72 requires it but yields no artefact a third party can check without an inspection | The monitoring *is* the conformance evidence, signed and checkable |

The bridge letter deserves naming. It is the assurance industry conceding that its reports go stale, and covering the gap with an unaudited management claim. OpenAISF replaces it with a signed heartbeat.

---

## 4. Design principles

Constitutional. A control that breaks one does not enter the catalog.

**P1 Falsifiability.** Every control states a condition under which it fails.

**P2 No unachievable normativity.** No control may require an outcome the field has not achieved. Prompt injection is unsolved at the model layer — adaptive attacks defeat published defences at rates above 85–90%, and the major labs concede it. A control saying "the system shall prevent prompt injection" makes every conformant system a liar. Controls bound consequence, require detection and require containment. **None of them claims prevention.**

**P3 Evidence is a byproduct.** Anything a control requires must be producible by a system running correctly, without a compliance activity. If satisfying a control needs a document whose only reader is an auditor, the control is wrong.

**P4 Applicability is computed, not read.** The reader never decides whether a control applies to them.

**P5 Inheritance before reimplementation.** Duplicated assurance is the largest single source of compliance cost and is treated as a defect.

**P6 One catalog, many views.** No separate executive framework.

**P7 Neutrality by construction.** No vendor is named as required.

**P8 Explain the failure, not the requirement.** Every control carries the real failure it prevents, with a named incident where one exists.

**P9 Degrade honestly.** No state between pass and fail.

---

## 5. The catalog

20 domains, 118 controls. Each control carries a machine-evaluable scope predicate, so an exhaustive catalog still produces a short list.

| | Domain | | Domain |
|---|---|---|---|
| D01 | Governance, Accountability & Roles | D11 | Transparency, Disclosure & Output Provenance |
| D02 | Risk, Context & Impact | D12 | Privacy, Rights & Data Protection |
| D03 | Data Governance & Provenance | D13 | Fairness, Non-Discrimination & Societal Impact |
| D04 | Model & Supply-Chain Integrity | D14 | Operations, Monitoring & Drift |
| D05 | Security & Adversarial Resistance | D15 | Detection, Attribution & Forensics |
| D06 | Identity, Access & Delegation | D16 | Incident Response, Containment & Recovery |
| D07 | Agentic Authority & Containment | D17 | Third-Party, Procurement & Inherited Assurance |
| D08 | Evaluation, Red-Teaming & Assurance | D18 | Change, Versioning & Decommissioning |
| D09 | Robustness, Reliability & Fallback | D19 | Conformance & Evidence Integrity |
| D10 | Human Oversight & Intervention | D20 | Resource, Cost & Environmental Impact |

### 5.1 What OpenAISF requires that no incumbent regime does

36 of the 118 controls map to zero requirements at full strength across ISO/IEC
42001, NIST AI RMF, the EU AI Act and the CSA AI Controls Matrix. The figure is
computed by the method in §9 rather than asserted. 15 of the 20 domains contain
at least one. A representative selection:

| Risk | Incumbent requirement | OpenAISF |
|---|---|---|
| An agent doing work nobody authorised, inside its permissions throughout | none | `D15-C07` detect activity outside the recorded business purpose |
| An agent whose actions stop matching the plan it announced | none | `D15-C01` compare declared intent against actions taken |
| A kill switch that has never been exercised | none | `D16-C02` exercise containment on a cadence, record time to contain |
| Detectors that have never fired | none | `D16-C03` inject a simulated rogue agent, measure time to detect |
| Unbounded agent consumption | none | `D07-C02` per-session budget for calls, tokens, spend, egress |
| Privilege escalation on agent spawn | none | `D07-C03` bounded delegation depth, no escalation |
| Irreversible autonomous action | none | `D07-C04` classify by reversibility, gate the irreversible |
| Prompt and completion stores on no data map | none | `D03-C11` inventory them as a data store, not as logs |
| Deletion that leaves the derived embedding | none | `D03-C13` prove deletion by attempted retrieval, semantic queries included |
| Upstream assurance silently lapsing | none | `D17-C02` inherited controls degrade with the upstream lease |
| A declared policy that never executed | none | `D19-C03` check declared configuration against observed enforcement |
| Oversight degrading to rubber-stamping | none | `D10-C03` monitor acceptance rate; near-total is a finding |

### 5.2 Data governance

Existing data governance regimes were written for records that are copied. An AI
system creates stores nobody inventories and derives artefacts that are
*computed*, losing their classification at the moment of derivation. D03 carries
16 controls, 7 of them original:

- `D03-C11` — prompts, completions and tool I/O appear in the data inventory with
  an owner, classification and retention. They MUST NOT be treated as logs.
- `D03-C12` — embeddings, indexes, caches and fine-tuning corpora inherit the
  classification and residency of their most sensitive source.
- `D03-C13` — deletion is proven by attempted retrieval through the system's own
  paths, including semantically equivalent queries.
- `D03-X01` — combining data classes in one model context requires a declared
  policy; output takes the classification of the most sensitive contributor.
- `D03-X02` — operational data MUST NOT be reused for training outside its
  collection purpose without a recorded decision naming the data and the model.
- `D03-X03` — isolation in shared retrieval and cache layers is verified by
  attempting cross-boundary retrieval, which MUST fail.
- `D03-C07` — AI data classification is inherited from the organisation's
  existing scheme rather than invented alongside it.

**Scope is computed.** A control declares `applies_when` over system class, autonomy level, data class and risk classification; the Statement of Applicability resolves it. Measured on the reference implementation:

| System | T1 | T2 | T3 |
|---|---:|---:|---:|
| Internal non-agentic LLM application | 4 | 35 | — |
| Agentic, tool-using, handling personal data | 4 | 51 | 77 |

118 controls exist. Nobody reads more than 77 and most read 35. **T1 is four controls, of which one is required** — the free tier is meant to be minutes, and that is an executable test in the reference implementation rather than an aspiration.

---

## 6. The rogue-agent control chain

D07, D15 and D16 implement five stages. Every stage is evidence-bearing.

**Bound.** Signed capability manifests enforced default-deny; per-session action budgets covering calls, tokens, spend, write operations and egress; delegation depth limits with no privilege escalation on spawn; reversibility classes with human gates on the irreversible; default-deny egress; run-scoped credentials; containment tiers.

**Detect.** This is where an agent differs from every other kind of software: it declares intent before it acts, which makes a class of detection possible that has no classical analogue.

- **Intent–action divergence** — the declared plan against the actions taken. Would have caught GTG-1002, where every individual action was plausible for the stated task and only the relationship between them was not.
- **Manifest violation at the attempt**, not at the success.
- **Swarm and velocity signatures** — the Hugging Face signature exactly.
- **Egress anomaly**, explicitly covering reputable public services, because that is where command and control was staged.
- **Canaries and honeytokens** — near-zero false positives and binary in evidence.
- **Provenance break** — untrusted content reaching a privileged context, the *precondition* for injection, detectable when the injection is not.
- **Business-purpose divergence** — whether the action serves an objective an accountable person authorised. Distinct from the first: an agent can sit inside its manifest, match its declared plan perfectly, and still be doing work the organisation never sanctioned.
- **Replay sufficiency** — whether the retained trace can reconstruct why the agent acted.

**Contain.** Five separately invocable layers: session termination, credential revocation, tool cutoff, network isolation, deactivation. Separately invocable because the common failure is that terminating a session leaves the credentials it minted valid.

**Recover.** Restoration to a pinned state, pre-declared rotation scope, blast-radius recorded, dependents notified.

**Prove.** Detection and containment capability are proven by drill, not declared. Simulated rogue-agent behaviour is injected on a cadence; the evidence is the detector firing with a measured **MTTD**, and the containment exercise with a measured **MTTC**. Failures stay recorded as failures. This attacks a measured gap: around 58–59% of enterprises monitor their agents and only 37–40% can stop one.

---

## 7. Evidence, and how a lie is caught

Evidence has two planes. The **control plane** says a policy is configured. The **data plane** says it was enforced, from live traffic. T3 and above require both.

Three rules decide conformance, each existing because of a specific way it goes wrong.

**Missing signal is failure, not silence.** A perfectly compliant system and a completely broken pipeline emit identical silence, so silence cannot be a pass.

**Declared policy is checked against observed enforcement.** A control plane claiming a policy is enabled, while the data plane shows live traffic and zero decisions, is a contradiction settled by machine:

```
D07-C01  [fail]  declared enabled, but 184203 requests crossed the enforcement
                 point with 0 decisions recorded. A policy that never fired
                 under live traffic was not operating.
lease: revoked
```

No auditor was involved, and **an attestation cannot resolve it**. Fabrication is *disqualifying*: it blocks even where the control is merely recommended at that tier, and revokes rather than degrades. Obligation level governs whether a shortfall matters; it does not govern whether a lie counts as a lie.

**Freshness expires on its own.** Each control declares a window, capped by tier. Past the window a control goes stale; past grace the lease expires.

Adapters are out-of-tree, contributed and replaceable — no vendor is required. The contract's fourth rule is the one that matters: **never invent an observation.** If the source cannot answer, omit the record and let the control fail as a missing signal. Emitting a plausible zero is fabrication.

---

## 8. The lease, the log, and inheritance

A conformance statement carries its own `stale_after` and `expires_at`. A verifier needs the statement, a key and a clock — not the catalog, not the evidence, not the subject's cooperation, and **not a registry that could be captured or pressured**.

**A badge is not a stored value. It is a function of the reader's clock.** A vendor whose lease runs out reads as expired in somebody else's README, with nobody notified and nobody able to prevent it. No lease outlives its tier ceiling (T1 365 days down to T4 30), so a subject cannot construct a statement that never needs renewing.

The log is hash-chained. Rewriting a past entry breaks every hash after it. The operator cannot forge history and cannot make an expired statement look current; at worst they refuse to append, which is visible.

**Assurance decay propagates downstream.** A control inherited from an upstream component resolves against the upstream's lease. Stale upstream, stale dependent; expired or revoked upstream, failed dependent. Assurance cannot be laundered upward — inheriting at T3 from a T2 upstream is refused. This is the property no existing framework models, and it creates the commercial incentive that makes inheritance work: a provider who lets their badge lapse degrades every customer depending on it, and will hear about it.

Signing is pluggable and the difference between schemes is enforced. `sha256-digest` proves only that a payload is intact — anyone can compute one for any payload — so publishing at T3 refuses it outright.

---

## 9. Provable coverage, and honest exclusion

Every framework claims it maps to the others. Mapping *outward* from your own controls can only show what you found; it can never show what you missed.

OpenAISF inverts it. Each regime is inventoried to its atomic requirements, and the engine walks that inventory demanding each one is **covered** by named controls or **excluded** with a stated reason. No third state. A gap fails the build.

| Regime | Requirements | Covered | Excluded |
|---|---:|---:|---:|
| CSA AICM v1.1.1 | 247 | 156 | 91 |
| MITRE ATLAS 2026.07 | 178 | 136 | 42 |
| EU AI Act 2024/1689 | 84 | 84 | 0 |
| NIST AI RMF 1.0 | 72 | 72 | 0 |
| ISO/IEC 42001:2023 Annex A | 38 | 38 | 0 |
| MCP-38 | 38 | 38 | 0 |
| OWASP LLM Top 10 2025 | 10 | 10 | 0 |
| OWASP LLM Top 10 2026 | 10 | 10 | 0 |
| **Total** | **677** | **544** | **133** |

The 133 exclusions are the framework's most consequential judgement and are the primary subject for review. They fall into two groups, each entry carrying a written reason:

- **91 CSA AICM** — datacentre security, endpoint management, cryptography, HR security. The AICM extends the Cloud Controls Matrix and necessarily restates a full cloud security baseline. Restating it inside an AI framework would be the bureaucracy this exists to remove; it is inherited from the organisation's existing regime under D17-C02.
- **42 MITRE ATLAS** — adversary reconnaissance and resource development performed outside the defender's systems, plus six that describe harms rather than techniques. No control prevents an adversary reading public research or acquiring infrastructure.

No requirement was excluded to produce a complete coverage report, and control D19-C05 fails the conformance run where an exclusion is contradicted by the subject's telemetry.

**Originality is computed, never asserted.** Regimes are classified as *requirement* catalogs (ISO, NIST, EU, AICM) or *threat* catalogs (OWASP, ATLAS, MCP-38). A mapping to a threat catalog establishes that a control is relevant to a known attack and can never establish that somebody already requires it, so it can never count as full strength. Two or more full mappings is `adopted`; one is `derived`; zero is `OpenAISF-original`. **36 of 118** controls are original by that computation, and the default is `full` so claiming novelty costs an explicit, reviewable edit while disclaiming it is free.

---

## 10. Governance, licensing and roles

Three names, three jobs, and they must not blur.

| Name | What it is | Who owns it |
|---|---|---|
| **OpenAISF** | The open standard | Open. Created by Maarten Loose |
| **Certifier** | A *role* defined by the standard — obligations, signing duties, independence rules, aligned to ISO/IEC 42006 | Anyone meeting the requirements |
| **TruCert** | TruSecure's implementation of the Certifier role, and its commercial assurance product | TruSecure |

A system can reach **any tier, including T4, with no money changing hands and no certifier involved.** That is not a concession; it is the mechanism by which a standard spreads. The Certifier requirements are published before any certifier launches, so the role demonstrably predates its first occupant.

Specification CC-BY-4.0; tooling Apache-2.0. Derivative works must carry *"Based on OpenAISF, created by Maarten Loose."*

**Intellectual property of the crosswalk.** The regimes referenced are under sharply different terms, and one rule governs: **OpenAISF references external regimes; it never reproduces them.** A crosswalk needs the identifier, not the source's words, because everything normative here is written by OpenAISF. Identifiers are not protectable expression, an exhaustive enumeration embodies no original selection under *Feist*, and citing a clause number to state a mapping is a citation. The ISO and CSA inventories therefore contain no source-authored text at all. `ATTRIBUTIONS.md` holds the per-regime analysis and the open legal actions.

---

## 11. Open questions for reviewers

1. **The 133 exclusions (§9).**
2. **Mapping strength.** Marking a requirement-catalog mapping `partial` is the one human input to the originality figure. Defaults lean against inflation, but review is the only real mitigation.
3. **Intent–action divergence (D15-C01).** The most original detector and the most likely to be noisy. It needs a measured baseline before it can be normative below T3.
4. **Adapter trust.** The evidence model depends on its producers. Producer attestation raises the cost of forgery without eliminating it. A compromised adapter is equivalent in effect to a compromised assessor.
5. **Inheritance cold start.** Inheritance is the cost lever and it only works once upstream providers publish badges. Until a major model provider does, every deployer carries the full model-layer catalog.
6. **Tier thresholds.** Freshness windows, grace periods and tier ceilings are set from judgement rather than measurement. Operational data should revise them.

---

## Appendix A — Incidents referenced

**GTG-1002** (September 2025). A state-sponsored group hijacked agentic coding instances for cyber-espionage against roughly thirty targets. The AI performed 80–90% of tactical operations independently at thousands of requests per second. Operators told the model they were a security firm conducting authorised testing.

**Mexican government breach** (December 2025 – February 2026). A single attacker used commercial models to breach nine agencies; 195 million taxpayer records and 220 million civil records. The model executed roughly 75% of remote commands.

**Hugging Face** (July 2026). The largest AI model repository was breached *by an autonomous agent swarm*. A malicious dataset achieved code execution on a processing worker through a remote code loader and a template injection in a dataset configuration, then escalated to node-level access, collected cloud and cluster credentials and moved laterally over a weekend — via "many thousands of individual actions across a swarm of short-lived sandboxes, with self-migrating command-and-control staged on public services."

**Measured context.** 98% of organisations have employees using unsanctioned AI tools; average shadow-AI breach cost 4.2 million dollars. MCP adoption grew over 400% in 2025 with most deployments outside any security review. Non-human identities outnumber humans 45:1, and 144:1 in cloud-native estates. Only 21% of enterprises report mature agent governance; Gartner expects 40% to decommission agents by 2027 over governance gaps found after incidents.

---

## Appendix B — Prior art

- OSCAL (NIST) — mandatory for FedRAMP providers from September 2026. OpenAISF exports it.
- *Making AI Compliance Evidence Machine-Readable* — OSCAL as the AI compliance interchange format, with an Apache-2.0 SDK.
- *Policy Cards* — machine-readable runtime governance for autonomous agents.
- *AIP: Agent Identity Protocol* — verifiable delegation across MCP and A2A.
- *DEMM-Bench* — agent-runtime governance-evidence sufficiency.
- *MCP-38* (arXiv:2603.18063) — threat taxonomy, inventoried as a regime.
- ISO/IEC 42001, 42005, 42006, 23894; NIST AI RMF 1.0; EU AI Act 2024/1689; OWASP LLM Top 10 2025 and 2026; MITRE ATLAS; CSA AICM v1.1.1.

---

## How to comment

Open an issue in the public repository. Sections 9 and 11 are the primary subjects for review.

*OpenAISF — created by Maarten Loose. Specification CC-BY-4.0, tooling Apache-2.0.*
