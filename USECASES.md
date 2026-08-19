# OpenAISF — Where it works, and where it does not

> **OpenAISF, created by Maarten Loose.**

This document is the honest counterpart to the hype. It states, plainly and
without overclaim, which jobs OpenAISF actually does, which jobs it does only
under conditions, and which jobs it does not do at all — and why. Use it to
decide, before you build anything, whether OpenAISF is the right tool for the
job you have in mind.

---

## 1. The one question OpenAISF answers

OpenAISF is a conformance framework, and conformance is a narrow, specific
claim:

> **Is this AI system holding to its declared controls — and for how long?**

Everything the tooling does serves that single question:

- It decides **which controls apply** to a given system (not you, the reader).
- It judges, from **evidence**, whether those controls hold.
- It attaches a **lease** — evidence goes stale, then expires, against the
  reader's clock. A badge that is not renewed lapses by itself.
- It publishes the result to an **append-only log anyone can verify** without
  your cooperation.

Three facts follow that predict almost every "will it work?" answer:

1. **It is per-system, not per-company.** You describe one system at a time.
   Company-wide coverage is the sum of the systems you scope.
2. **It is evidence-based.** It can only judge what it is given records for.
   It measures; it does not enforce.
3. **It governs deployments, not models.** It checks whether the controls
   around a deployment hold. It does not judge the model's capabilities.

---

## 2. The three preconditions — will it work for you?

Before reading the personas, run this test. If any precondition is missing, the
answer for your use case is "works only with conditions" or "does not work".

**Precondition 1 — the system can be scoped.**
You can say what it is: an LLM app, an agent, how much autonomy it has, what
data it touches, its EU AI Act classification. If you cannot describe the
system (it is vague, unnamed, or you do not actually know what it is), you
cannot assess it.

**Precondition 2 — the system can produce attributable evidence.**
There is *something* that can emit records about what is configured (control
plane) and, at T3+, what happened to live traffic (data plane) — a gateway, an
observability platform, CI. Records are signed at the producer. A system with
no evidence source at all can only be self-asserted at the lowest tiers.

**Precondition 3 — the question is "does the deployment hold over time?"**
If your real question is "is this model inherently safe?", "block this attack
right now?", or "is my whole company fully compliant today?", you are asking a
question this framework was deliberately not built to answer. It will tell you
whether declared controls are holding and how long that has been true — not
whether the world is safe.

---

## 3. Personas — the three you named

### 3.1 An AI provider keeping its own AI app compliant — **WORKS**

This is the core use case and the one OpenAISF is built for end to end.

You describe the app once (`system.yaml`), the tooling resolves what applies at
your tier, an adapter emits evidence from your gateway, `check` judges it, you
`publish` a signed statement, and anyone can `verify` the badge. The lease
model is exactly what "constantly in compliance" means in practice: if you stop
producing evidence, the badge lapses by itself — you cannot forget your way
into a perpetual certificate.

Concretely:

```bash
openaisf scope    --context system.yaml --tier T2
openaisf check    --context system.yaml --evidence ./evidence --tier T2
openaisf publish  --context system.yaml --evidence ./evidence \
                  --log openaisf-log.jsonl --key signer.key
openaisf badge    --log openaisf-log.jsonl --system urn:…
```

The word "constantly" is honoured by **automation**, not by intent. If you only
produce evidence monthly and your tier's windows are days, you are
non-conformant most of the time — which is the framework working, not a bug.

### 3.2 A CISO monitoring AI use across the company — **WORKS, with an inventory**

A CISO wants the question answered company-wide: "where is AI used, and is it
under control?" OpenAISF answers the second half *for each system you scope*.
It does not answer the first half at all — it cannot discover systems.

So the pattern that works is:

1. Keep an **inventory of AI systems** — one `system.yaml` per system. This
   inventory is yours; the tooling has no discovery.
2. Run `check` for every system **on a schedule** (CI or a cron job), and feed
   the results into your dashboard.
3. Use **badge expiry as the tripwire**: a system whose badge lapses is a
   system you know about, with a date attached. The badge verifies against the
   reader's clock, so lapse is visible even if your monitoring misses it.
4. Treat a failed `check` as an **operational incident**, not a report to file.

What the CISO gets: a continuously-current, evidence-backed view of every
scoped system, plus honest gaps — every system with no gateway produces only
low-tier assurance, and every *unscoped* system is invisible by design.

What the CISO must remember: **OpenAISF does not find shadow AI.** Its
coverage is exactly as complete as your inventory and your evidence pipelines.

### 3.3 A system administrator verifying all AI use is compliant — **WORKS, as a monitoring loop**

The administrator's job is the daily loop: "did anything change, and is it
still compliant?" This maps directly onto the tooling.

- Each system has a `system.yaml` and an evidence pipeline that emits on its
  own schedule (not monthly reports — live records).
- A scheduled job runs `check` for every system. **Exit code 1 is a pager.**
  The failure message names a real defect ("policy declared enabled, but
  184203 requests crossed the enforcement point with 0 decisions recorded"),
  which routes to the right team.
- `--json` feeds results into existing dashboards and ticketing.

The condition: this works only if the evidence is **automated**. A manual
process that assembles records by hand degrades into self-attestation, which is
precisely the assurance the framework exists to improve on.

---

## 4. Use cases that work

| Use case | Why it works |
|---|---|
| An AI app owner certifying its own deployment (T1–T4) | The core loop; self-assessment is free at every tier |
| An AI provider publishing a badge for customers to verify | `verify` needs only the log, a public key and a clock — no account, no relationship |
| Procurement / supplier assurance | Inherit already-certified controls from upstream components via `inherits:`; a T3 build on a T1-certified component inherits T1 assurance — never more |
| Regulated sectors, EU AI Act high-risk, public sector (T3/T4) | Control + data plane, signed, with an independent certifier (TruCert) adding the counter-signature |
| GRC / FedRAMP-style pipelines | `export assessment-results` and `export component-definition` emit OSCAL 1.1.2 |
| Continuous monitoring of scoped systems | Leases expire against the reader's clock; stale badges lapse by themselves |
| Catching fabricated evidence | Two-plane contradiction checks (e.g. `D19-C03`) fail a control even where it was only recommended; attestation cannot override telemetry |
| Agents assisting with review (read/check only) | The MCP server exposes catalog, applicability, checking and verification — and **no** tool that writes, signs or publishes |
| Crosswalking to external regimes | Coverage is walked against the requirements of EU AI Act, ISO/IEC 42001, NIST AI RMF, CSA AICM, OWASP LLM 2025/2026, MITRE ATLAS, MCP-38 |

---

## 5. Use cases that work only under conditions

These are real jobs, but they require you to bring something OpenAISF does not
provide.

| Use case | The condition | What you must bring |
|---|---|---|
| Company-wide "is all AI compliant?" | Coverage = your inventory × your evidence | An asset inventory; the tool cannot discover systems |
| "Continuously compliant" | Leases enforce freshness, but only if evidence keeps flowing | Automated evidence production; manual cadence fails the lease |
| High-assurance claims (T3/T4) | Data-plane evidence requires an enforcement point | A gateway or equivalent that actually sees live traffic |
| Regime compliance in the gap | Only the crosswalk regimes are mapped | For GDPR/HIPAA/SOC 2/PCI-DSS you need your own mapping on top |
| Agents doing the monitoring | MCP is read/check only by design | A human or separate pipeline that signs and publishes |

---

## 6. Use cases that do **not** work — and the reason why

Each of these is a "no" for a structural reason, not an implementation gap.
Treat the reason as architectural and plan accordingly.

### 6.1 Preventing prompt injection, or guaranteeing a model cannot be manipulated — **NO**

This is the framework's most visible boundary. Prompt injection is unsolved at
the model layer; a control reading "the system shall prevent prompt injection"
cannot be satisfied, and a standard full of unsatisfiable controls is a
worthless standard. OpenAISF therefore **bounds what a successful injection
can reach, requires detection proven by drill to fire, and requires containment
that has been exercised and timed** (principle **P2**).

Consequence: if your goal is "make injection impossible," OpenAISF will not
claim that — and will refuse to let you claim it either. It will instead prove
that when injection happens, the blast radius is contained.

### 6.2 Judging whether a model is safe, good, or unbiased — **NO**

Conformance is a statement about the *deployment's controls*, not about the
model's capabilities or behaviour. A conformant system can still be biased,
wrong, or incompetent in ways no control names. OpenAISF does not red-team the
model, benchmark it, or score its quality. Pair it with model evaluation if
that is your question.

### 6.3 Real-time enforcement, blocking, or runtime guardrails — **NO**

OpenAISF is a measurement and verification framework. It tells you that an
enforcement point *fired* (data-plane decisions) and that a policy was
*configured* (control plane). It does not sit in the request path; it does not
block anything; it does not slow down traffic. If you need to stop a
non-compliant action at runtime, you need a runtime guardrail *plus* OpenAISF
to prove the guardrail is actually working.

### 6.4 Discovering unknown AI systems (shadow AI) — **NO**

There is no network scan, no agent-based discovery, nothing that finds systems
you have not named. Every system must be scoped in a `system.yaml`. For a CISO
worried about shadow AI, OpenAISF makes the *known* surface honest and lapsed
badges visible, but the *unknown* surface is outside its view entirely. You
need an asset-discovery process first.

### 6.5 Compliance with regimes outside the crosswalk — **NO**

The crosswalk maps exactly these regimes: EU AI Act, ISO/IEC 42001, NIST AI
RMF, CSA AICM, OWASP LLM 2025/2026, MITRE ATLAS, MCP-38. GDPR, HIPAA,
PCI-DSS and SOC 2 are **not** among them. The OSCAL export feeds your GRC tools,
and the coverage engine proves no mapped requirement is uncovered — but
OpenAISF is not a GDPR or HIPAA framework and makes no claim to be one.

### 6.6 High-assurance claims with no evidence capability — **NO**

Tier 3 requires the data plane: evidence of what happened to live traffic.
If your system has no gateway, no telemetry, no enforcement point — nothing
that can witness live behaviour — then **no amount of configuration paperwork
reaches T3**. A T3 claim without data-plane evidence is treated as a failure.
The tier ladder is a ladder, not an aspiration.

### 6.7 Systems you do not operate — **NO, except by inheritance**

You cannot produce data-plane evidence for infrastructure you do not control —
a SaaS model endpoint, a third-party platform. OpenAISF handles this in exactly
one way: if the upstream publishes verifiable evidence or a badge, you *inherit*
their certified controls in your scoping file. If they publish nothing, you
cannot claim their assurance, and a T3 system built on an unevidenced component
inherits nothing.

### 6.8 Absolute guarantees against manipulation — **NO**

The log is tamper-evident, not tamper-proof. Modifying a past entry invalidates
every entry after it — but the framework presupposes that the evidence pipeline
itself is honest. A determined insider who controls the gateway, the producer
keys and the publisher can still produce verifiable-but-false records. OpenAISF
catches specific contradictions (two-plane mismatches, decisions without
traffic, traffic without decisions) and treats fabrication as disqualifying;
it does not make an organisation honest.

### 6.9 "Set and forget" compliance — **NO**

The lease model is the opposite of set-and-forget. Evidence goes stale against
the reader's clock, so a deployment that stops producing evidence becomes
non-conformant silently. This is a feature, but it means OpenAISF *demands*
ongoing automation. If your organisation will not run scheduled evidence
production and checks, you will spend most of your time non-conformant — which
is the framework working as designed.

---

## 7. Quick decision matrix

| Scenario | Verdict |
|---|---|
| Certify my own AI app, keep it fresh, show a badge | ✅ Works |
| Publish a badge customers can verify without asking me | ✅ Works |
| Monitor every system I scope, on a schedule, in CI | ✅ Works |
| Prove my T3 controls with live, signed data-plane evidence | ✅ Works (needs a gateway) |
| Feed results to my GRC tooling (OSCAL) | ✅ Works |
| CISO dashboard across all scoped systems | ⚠️ Works + your inventory |
| Catch shadow AI I don't know about | ❌ Does not work |
| Prevent prompt injection from ever succeeding | ❌ Does not work |
| Judge whether the model is safe/quality/unbiased | ❌ Does not work |
| Block a non-compliant action in real time | ❌ Does not work |
| GDPR / HIPAA / SOC 2 / PCI-DSS compliance | ❌ Not mapped (OSCAL helps ingestion) |
| T3 on a system with no live traffic telemetry | ❌ Does not work |
| Guarantee no insider can forge evidence | ❌ Tamper-evident, not tamper-proof |
| Set it up once and ignore it | ❌ Leases expire by design |

---

## 8. Preconditions checklist — before you commit

If you are about to deploy OpenAISF, confirm each line:

- [ ] The systems you care about are named and describable (system class,
      autonomy, data class, EU risk) — or you are building that inventory now.
- [ ] Each system has at least one evidence source (gateway, observability,
      CI) — or you accept the tier ceiling that implies.
- [ ] Producers can sign (key management exists) — needed for attribution and
      for any T3+ claim.
- [ ] Evidence production is on a schedule, not manual.
- [ ] `check` runs automatically and its exit codes page people.
- [ ] You publish to a log you back up and treat as append-only.
- [ ] Your real question is "is the deployment holding?" — not "is the model
      safe?" or "block it now."

---

## 9. How to read this document

The "no" list is not a list of shortcomings to apologise for. It is the
geometry of a measurement instrument: OpenAISF measures conformance; it does
not enforce, discover, or judge models. The correct way to use it is to put it
beside the tools that do those jobs — a runtime guardrail for enforcement, an
asset inventory for discovery, model evaluation for capability — and let each
instrument do the one thing it is for.