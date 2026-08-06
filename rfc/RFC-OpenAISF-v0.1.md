# RFC: OpenAISF — The Open AI Safety Framework
**Status:** Request for Comments — Draft v0.1
**Author:** [You]
**Published:** August 2026
**Repo:** openaisf.org (to be published)

> Comments, issues, and pull requests welcome. This RFC proposes a new,
> open, machine-readable AI safety standard and asks the community whether
> the structure and scope described below should become OpenAISF v1.0.

---

## 1. TL;DR

OpenAISF is a **free, open, machine-readable AI safety standard** whose
conformance is a **test that passes or fails**: an AI system is
OpenAISF-conformant at tier T when `trucert check` exits 0.

**TruCert** is the conformance mark of OpenAISF — the verifiable badge buyers
and regulators see ("TruCert-Certified at OpenAISF Tier N"). The standard
itself (OpenAISF) is open and neutral; TruCert is the badge that signals a
system has passed it.

It exists because every existing standard is either **prose + paperwork**
(ISO 42001, NIST RMF — heavy, vague, expensive, no developer path) or a
**threat list with no controls** (OWASP, MITRE ATLAS). None of them govern
the **runtime/inference-gateway layer** that every production AI team
actually depends on (LiteLLM, Portkey, Langfuse, Lakera, MCP).

OpenAISF fills that gap. It is:

- **Machine-readable** — the standard ships as `openaisf-controls.yaml`.
- **Executable** — a free CLI grades any repo in minutes.
- **Tiered** — T1 solo → T4 frontier, so a 15-person startup and a
  hyperscaler live in the same standard at different depths.
- **Crosswalked** — conform once, auto-satisfy ISO 42001 / NIST RMF /
  OWASP / ATLAS / EU AI Act / CSA AICM coverage statements.
- **Original** — 25 of 59 controls have no incumbent equivalent.

---

## 2. The problem

The AI-safety standards field is bifurcated into two altitudes with a
**one-layer-wide blind spot** between them:

```
  ORGANIZATIONAL POLICY     ← ISO 42001, NIST RMF (process, paperwork)
            ↓
  RUNTIME / GATEWAY LAYER   ← NOBODY GOVERNS THIS
            ↓
  APPLICATION / MODEL RISK  ← OWASP Top 10, MITRE ATLAS (threats, not controls)
```

The runtime layer — model routing, failover, cost caps, guardrails,
telemetry, substitution, rollback, tool/MCP calls — is where every
enterprise actually enforces safety. It is the de facto control plane.
And it has **zero corresponding controls in any standard.**

Meanwhile:

- ISO 42001 costs **$85k–$650k**, takes 3–12 months, and engineers
  openly prefer NIST RMF (which has no certification).
- NIST RMF describes outcomes without controls or measurements, and
  has no cert — so buyers can't distinguish real compliance from
  AI-washing.
- EU AI Act demands post-market monitoring (Art. 72) and logging
  (Art. 12) with **zero technical specification** of what that looks like.
- OWASP and ATLAS give long threat lists but no control objectives or
  maturity ladder.
- The MCP ecosystem (late 2024) and agentic AI are completely
  ungoverned by any framework published before them.

---

## 3. The proposal

OpenAISF v1.0-draft defines:

1. **11 control domains, 59 controls (54 core + 5 expansion)** (see `openaisf-controls.yaml`),
   each a testable predicate with a tier, a check kind, required evidence,
   and crosswalk references.
2. **4 tiers** (T1 solo → T4 frontier) so the same standard serves a
   hobbyist and a frontier lab.
3. **A machine-readable crosswalk** (`openaisf-crosswalk.yaml`) mapping
   every control to ISO 42001 / NIST RMF / OWASP / ATLAS / EU AI Act /
   CSA AICM / SAIF / OSAA SAFE.
4. **A reference CLI** (`trucert`) that evaluates a repo at a tier and
   emits a badge + JSON report. Prototype exists and runs. The badge carries
   the **TruCert** conformance mark.
5. **Sector Profile extensions** (healthcare, finance, public-sector,
  frontier) so the core stays lean (54 core + 5 expansion) while coverage is exhaustive.

### The three lead claims

Three control areas where OpenAISF is **first-of-kind** and intends to
*own* the category:

- **D10 — Tool & MCP Security.** The MCP governance standard. MCP
  shipped after every framework; OpenAISF is first to govern it.
- **D4-C03 — Model Port Equivalence.** Substitution safety: swapping
  GPT-4 → Claude silently breaks certified properties; OpenAISF makes
  the substitution a controlled, re-validated event.
- **D9-C01 — LLM Telemetry & Live Evaluation.** The canonical
  inference-event log + online evals that EU AI Act Art. 72 demands
  but doesn't specify.

### The original footprint

**25 of 59 controls are OpenAISF-original** — no incumbent equivalent.
These include: agent-memory integrity (incl. GDPR Art. 17 erasure in
memory), runtime AI firewalling (WAF vendors : OWASP :: AI-firewall
vendors : OpenAISF), outcome-based policy, prompt-as-code, model
provenance/signing (sigstore-for-models), fine-tune-away-refusals
defense, multi-agent delegation limits, cost-as-governance (D11), and
inference sustainability accounting.

---

## 4. How conformance works

```
$ trucert init            # scaffold openaisf.yaml + POLICY.md + dirs
$ trucert check --tier T1
✓ TruCert-Certified · OpenAISF-T1 (3 controls passed)
$ echo $?                 # 0
```

- **auto-static** checks (file/config inspection) run automatically.
- **auto-runtime** checks (evals, load-time signing) execute the system.
- **attest** controls require a signed YAML attestation + evidence,
  which the CLI consistency-checks (the "honesty layer": claim a control,
  produce the evidence, or fail).
- The result is a **verifiable badge** keyed to a tier — the trust
  signal NIST RMF refuses to issue, at a fraction of ISO 42001's cost.

---

## 5. Governance & licensing

- The **spec** (`openaisf-controls.yaml`, crosswalk, profiles) is
  **CC-BY-4.0** — free to read, implement, and fork.
- The **reference CLI** (`trucert`) is **Apache-2.0**.
- **TruCert** is the conformance mark of OpenAISF. Use of the mark to claim
  conformance is permitted only for systems that have passed the OpenAISF
  conformance checks at the relevant tier; mark governance is described in
  GOVERNANCE.md.
- OpenAISF is intended to live under **open, neutral governance**
  (foundation-transferable). Comments on the governance model are
  explicitly in scope for this RFC.

---

## 6. Questions for the community

We specifically request comment on:

1. **Domain structure.** Are 11 domains / 59 controls (54 core + 5 expansion) the right grain?
   Too few? Too many? (See §3.)
2. **D10 Tool/MCP Security and D11 Resource & Spend Control as
   first-class domains.** Agree they deserve first-class status, or
   should they fold into existing domains?
3. **D4-C03 — Model Port Equivalence (substitution safety).** Is the carrier-eval approach the
   right mechanism, or is there a better substitution gate?
4. **Tiering.** Is T1–T4 the right ladder? Should T1 be even smaller
   (instant, no file requirements)?
5. **Crosswalk scope.** Which additional regimes must we map
   (CoE AI Convention? UK AISI? Singapore Model AI Gov? sector regs)?
6. **Attestation/honesty layer.** Is consistency-checked attestation
   sufficient to deter AI-washing, or do we need independent assessment
   at lower tiers than T3?
7. **Governance home.** Should OpenAISF live in an existing foundation
   (Linux Foundation / OpenSSF / OWASP / CSA) or stand alone?

---

## 7. Relationship to existing work

OpenAISF is **complementary, not competitive**, to most incumbents:

- It **implements** NIST RMF principles with actual controls + a cert.
- It **operationalizes** ISO 42001's intent at a fraction of the cost.
- It **adds the control layer** that OWASP and ATLAS lack.
- It **specifies** what EU AI Act Art. 12/72 leave unspecified.
- It **emits** OSAA-SAFE-compatible incident reports (D9-C04).
- It is the **conformance standard** the runtime-defense vendor
  category (Lakera/Invariant/Prompt Security/neural-aegis-tier) can
  certify against.

---

## 8. Status & timeline

- **Now:** v0.1 draft + working CLI prototype (T1 checks).
- **Next:** incorporate RFC comments → v0.9 → community review.
- **Target:** OpenAISF v1.0 freeze, with full T1–T4 checks and the
  crosswalk publication feed.

We invite framework authors, AI labs, runtime-layer vendors, GRC
providers, insurers, and regulators to comment.

---

*Comment via issues/PRs on the OpenAISF repo, or by email to the author.*
