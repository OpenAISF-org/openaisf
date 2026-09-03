# OpenAISF — A Practical Manual

**For people who run systems, not for engineers who wrote them.**

This manual explains how to install the OpenAISF tooling, use it day to day,
understand what it tells you, keep it healthy, update it, and connect it to the
rest of your organisation. It assumes you can run commands in a terminal but
does not assume you are a developer.

> **OpenAISF, created by Maarten Loose.** The specification is CC-BY-4.0, the
> tooling is Apache-2.0. Every report, badge and log entry the tooling produces
> carries the attribution line above; keep it when you pass those outputs on.

---

## 1. What you are working with

OpenAISF is an open standard for proving that an AI system is safe and secure —
and, just as important, proving *for how long* it stayed that way. Think of it
as an MOT for AI agents rather than a one-off certification.

Four ideas do all the work:

- **Controls.** 118 concrete requirements across 20 domains. Each one names the
  real-world failure it prevents (a leak, an uncontainable agent, a system that
  keeps acting after it was told to stop). A control is either satisfied or it
  is not — there is no "mostly".
- **Not everything applies to you.** Each control says what kind of system it
  covers (an app, an agent, how much autonomy, what data it touches). The
  tooling decides what applies; you do not have to.
- **Evidence, in two layers.** The *control plane* says what is configured.
  The *data plane* says what actually happened to live traffic. Tier 3 and
  above need both, because the pair is how false claims get caught.
- **A lease, not a certificate.** Every control has a freshness window. Miss
  it and the control goes *stale*, then *expired*. Nobody needs to be told —
  the badge just reads as lapsed against the reader's clock.

### The tiers at a glance

| Tier | Who it is for | How much assurance | How long evidence stays fresh |
|---|---|---|---|
| **T1** | Prototypes, research, no real users | Self-asserted; a handful of controls | Up to 365 days |
| **T2** | Production traffic, ordinary risk | Self-asserted; live data where a gateway exists | Days to months |
| **T3** | Regulated sectors, EU AI Act high-risk, public sector | Control **and** live data; an independent certifier in practice | Short windows |
| **T4** | Frontier labs, systemic-risk models, high-autonomy agents at scale | Continuous, independently witnessed | As little as 30 days |

Every tier can be reached self-assessed with no fee. The commercial layer —
TruCert — exists only for the independent assurance that genuinely costs money:
someone else signing that they watched you produce the evidence.

---

## 2. Part A — Installing the tooling

### What you need

- **Python 3.10 or newer.** On a Mac, Python usually comes with the command line
  tools. On Windows, install it from python.org and tick *"Add python to PATH"*.
  On Linux, use your package manager.
- **git** (the tool that downloads the software). On a Mac it is included with
  Xcode command line tools; on Windows it comes from git-scm.com.
- Internet access for the one-time download.

### Step 1 — Download the software

Open a terminal and run:

```bash
git clone https://github.com/OpenAISF-org/openaisf
cd openaisf
```

This creates a folder called `openaisf` with everything inside it. From now on,
every command in this manual assumes you are inside that folder.

### Step 2 — Create a private, isolated workspace (recommended)

The tooling lives in a "virtual environment" so it cannot interfere with other
software on your computer.

```bash
python -m venv .venv
```

On Windows the folder is used the same way, but the commands inside it are
`.venv\Scripts\...` instead of `./.venv/bin/...`.

### Step 3 — Install the tooling into that workspace

```bash
./.venv/bin/pip install -e '.[dev]'
```

On Windows:

```
.venv\Scripts\pip install -e '.[dev]'
```

This installs the tool and everything it needs. The complete list of required
extras is deliberately tiny — two helper libraries (`pyyaml` and `jsonschema`).
Signing keys are handled by an *optional* add-on; if you will be publishing
signed statements (T3 and above), also install:

```bash
./.venv/bin/pip install -e '.[dev,signing]'
```

### Step 4 — Check the installation

```bash
./.venv/bin/python -m openaisf.cli scope --help
```

If you see a list of options (look for `--context`, `--tier`), the installation
works. If you instead see `No module named openaisf`, the install in Step 3 did
not complete — see the troubleshooting section at the end of this manual.

> **If the install hangs (slows down forever on some computers, especially
> external drives):** the tool still works. Run commands with a prefix instead:
> `PYTHONPATH=src ./.venv/bin/python -m openaisf.cli scope --help`. That tells
> Python where the code lives without a full install.

### What you now have

Eight commands, each doing one job:

| Command | What it does |
|---|---|
| `scope` | Works out which controls apply to your system |
| `check` | Judges whether your evidence satisfies those controls |
| `publish` | Signs your conformance statement and appends it to a public log |
| `verify` | Checks anyone's badge without their cooperation |
| `badge` | Renders the current status line for your system |
| `export` | Turns results into a format your governance tools understand |
| `coverage` | Reports how the standard covers external regimes (maintainers) |
| `mcp` | Lets AI agents read and check (never write) your conformance data |

---

## 3. Part B — Using it day to day

The daily cycle has six steps. Do them in order the first time; afterwards you
will mostly repeat steps 3–5.

### Step 1 — Describe your system, once

Create a file named `system.yaml` in your project folder. It is a short
questionnaire about the AI system you are assessing. Copy this and edit the
values:

```yaml
system_id: urn:openaisf:system:acme-support-agent
roles: [deployer]
system_class: [llm, agentic]
autonomy: tool_use
data_class: [internal, personal]
eu_risk: [limited]

inherits: {}     # controls an already-certified component proves for you
exclusions: {}   # controls that apply but you deliberately do not implement
```

What each line means:

- **system_id** — a unique name for this system. Use the `urn:...` format;
  it travels with every report and badge.
- **roles** — who you are in the chain. `deployer` is right for most users.
- **system_class** — what the system is. `llm` for a language model,
  `agentic` if it acts on its own, or both.
- **autonomy** — how much freedom it has: `tool_use`, `auto` and similar.
- **data_class** — what kind of data it touches: `internal`, `personal`,
  `public` and so on.
- **eu_risk** — its classification under the EU AI Act: `minimal`,
  `limited`, `high` or `unacceptable`.
- **inherits** — if a part of your system is already certified by someone
  upstream (for example your model provider), list those control IDs here and
  you do not re-prove them.
- **exclusions** — controls that apply to you but that you choose not to
  implement. This is allowed, but you must give a reason, and it is recorded —
  it is not a way to quietly skip work.

### Step 2 — Find out what applies to you

```bash
./.venv/bin/python -m openaisf.cli scope --context system.yaml --tier T2
```

You will see a table like this:

```
Statement of Applicability — urn:openaisf:system:acme-support-agent at T2

  applies            51
  inherited           0
  excluded            0
  not applicable     67
  ---------------------
  in scope           51  of 118 in the catalog
```

Read it as follows:

- **applies** — controls you must satisfy at this tier.
- **inherited** — controls you import from certified upstream components.
- **excluded** — controls you opted out of, with reasons.
- **not applicable** — controls that this kind of system is not covered by.
- **in scope** — what you actually have to demonstrate. This table **is** your
  work plan; the next step executes it.

Save the result for later (`--out openaisf-soa.yaml` puts it in a file).

> **The tiers compose downward.** If you build a T3 system on a T1-certified
> component, you inherit only T1 assurance from that component. You cannot pump
> a weak component up to a strong tier by building a strong system around it.

### Step 3 — Collect evidence

Evidence is the material that shows a control is satisfied. It comes from
infrastructure you already run: your AI gateway, your observability platform,
your CI pipeline. A small program called an *adapter* reads from one of those
systems and writes evidence records into a folder.

The rules that matter:

1. **One record per control, per layer, per time window.** Never guess one
   layer from the other — the whole point is having both.
2. **Sign at the source.** The producer of the data signs it before it is
   aggregated or sent. A signature from an aggregator only proves the
   aggregator received *something*.
3. **Never invent an observation.** If your gateway cannot answer a question,
   leave the record out and let the control fail as a missing signal. Making
   up a plausible zero is fabrication, and the standard has a control
   (`D19-C03`) built to catch exactly that. Fabrication is disqualifying even
   where the control would only have been recommended.

A reference adapter ships with the tooling. Point it at a gateway summary file:

```bash
python tools/adapters/gateway_adapter.py summary.json ./evidence \
    --key producer.pem --key-id gateway-prod
```

Your own adapters can be written by your engineering team following the same
contract. The standard names no vendor as required.

**From tier 3 upward, an unsigned record counts as no record at all.** The
check will tell you which of three things went wrong: no signature, a signature
that proves integrity but not who wrote it, or a signature that does not verify.
You will need a folder of public keys (`--keyring`) so the check can recognise
your producers.

### Step 4 — Check whether you conform

```bash
./.venv/bin/python -m openaisf.cli check \
    --context system.yaml --evidence ./evidence --tier T2
```

Two outcomes:

- **Exit code 0** — conformant at that tier. Done.
- **Exit code 1** — not conformant. The output tells you why, in the language
  of your system, not the language of paperwork:

```
D07-C01  [fail]  declared enabled, but 184203 requests crossed the enforcement
                 point with 0 decisions recorded. A policy that never fired
                 under live traffic was not operating.

lease: revoked
```

- **Exit code 2** — the command could not even run (a missing file, a bad
  setting). Fix the setup and run again.

Add `--json` if you want machine-readable output for scripts or dashboards.
Add `--verbose` to also see the controls that do not apply to you.

### Step 5 — Publish a signed statement

When the check passes, publish it: sign a conformance statement and append it
to an append-only, hash-chained log.

```bash
./.venv/bin/python -m openaisf.cli publish \
    --context system.yaml --evidence ./evidence --tier T2 \
    --log openaisf-log.jsonl --key signer.key
```

Notes for non-technical readers:

- **The log is append-only.** Once an entry is in, changing an old one
  invalidates every entry after it. Treat `openaisf-log.jsonl` as a record, not
  a file to edit.
- **`--key` is your signing key.** If you omit it, the statement is recorded
  but not signed — that is not enough for an external reader to trust it.
  Generate a key with a standard tool (`openssl genpkey -algorithm ed25519`).
- **`--key-id`** names who signed, so the log is traceable.
- Give the private key only to the people authorised to sign. The **public**
  key is safe to share — it is what verifiers use.

### Step 6 — Verify

Anyone — a customer, an auditor, a stranger on the internet — can check your
badge without your cooperation. That is the point. All they need is the log,
your public key and a clock:

```bash
./.venv/bin/python -m openaisf.cli verify \
    --log openaisf-log.jsonl --system urn:... --key signer.pub

./.venv/bin/python -m openaisf.cli badge \
    --log openaisf-log.jsonl --system urn:...
```

The badge line carries its own expiry. When your evidence goes stale, the badge
lapses in *their* copy of the output — no notification, nothing to stop it. That
is by design: a badge that could not lapse would be worthless.

**Integration shortcut:** `publish` and `check` produce the figures your
compliance teams need. `export assessment-results` produces a file your GRC
tools can ingest (see Part F).

---

## 4. Part C — Interpreting what the tooling tells you

### The vocabulary

| Term | Meaning |
|---|---|
| **Control** | One requirement, e.g. "the system can be stopped, and someone proved it by stopping it." |
| **Domain** | A group of related controls (there are 20; the data and agent domains are the ones you will hear about most). |
| **Control plane** | What is *configured* — policies, permissions, guardrails as set. |
| **Data plane** | What *happened* — live requests, decisions, traffic counts. |
| **Tier** | The depth of assurance you are claiming (T1–T4). |
| **Lease** | How long a control's evidence stays valid before it goes stale. |
| **Stale** | Evidence older than its freshness window. The control is no longer good. |
| **Expired** | Past the window plus a grace period. The badge no longer holds. |
| **Provenance** | Where a control came from — copied from an existing standard, derived from several, or original to OpenAISF. It is computed by the tooling, never hand-written. |
| **Contradiction** | Two records that cannot both be true (e.g. traffic flowed but zero decisions were made — or decisions were made but zero traffic flowed). A contradiction fails the control. |

### Reading a check report

For each control in scope you get one of three outcomes:

- **pass** — the evidence satisfies the control, and it is fresh enough.
- **fail** — the evidence does not satisfy it. Read the message: it will name
  the behaviour that is wrong, not the missing document. Common causes:
  - *Missing signal* — no evidence at all. A broken evidence pipeline looks
    exactly like a compliant quiet system, so absence is treated as failure.
  - *Stale or expired* — evidence exists but is older than the window.
  - *Unsigned / not verifiable* — the record cannot be attributed (T3+).
  - *Contradiction* — the control and data planes disagree.
- **not applicable** — only shown with `--verbose`; you are not responsible
  for it at this tier.

### Reading a badge line

The badge states the tier, the system, the date of the last evidence, and the
expiry. Read the *expiry* first. If it is in the past, the system is lapsed
right now, whatever the rest of the line claims.

### Reading the coverage report (maintainers)

`coverage` walks the requirements of external regimes (EU AI Act, ISO/IEC 42001,
ISO/IEC 23894, NIST AI RMF, CSA AICM, OWASP LLM, MITRE ATLAS, MCP-38) and
checks that every
requirement is covered by a control or excluded with a written reason. There is
no third state. The report lists, per regime, how many are covered, excluded,
or a gap. A gap is a release blocker — the standard cannot ship until every
requirement is either covered or explicitly, defensibly excluded.

The 36 controls with no external equivalent are the framework's original
contribution — the risks the incumbents do not cover.

---

## 5. Part D — Maintaining a healthy conformance

### Keep evidence fresh

- Know your windows. T1 evidence can be a year old; T4 evidence expires in
  about a month. Check your SoA for each control's window.
- Automate the re-run. Evidence should be produced by your existing systems
  *on their own schedule*, not by someone remembering. A gateway that emits a
  record every time it makes a decision is better than a monthly report.
- Run `check` on a schedule (a daily job is right for T2+) and treat a fail as
  an operational incident, not an annoyance. The failures **are** the work
  queue: each one names a real defect in the system.

### Guard your keys

- **Private signing keys** are the crown jewels. Two or three authorised people,
  ideally on hardware, and a documented way to rotate them.
- **Rotate on a schedule**, and when a key is retired, publish a statement to
  that effect so the log stays honest.
- The **keyring** folder holds the public keys of your producers. Keep it up to
  date as producers come and go; from T3 an unverifiable signature reads as
  absence.

### Protect the log

- It is append-only and hash-chained. Do not edit old entries; never reorder
  lines; do not let a file editor "save" it into a different encoding.
- Back it up, and keep a copy somewhere off the machine that writes it.
- If you need to withdraw a statement, append a withdrawal entry. You cannot
  delete the past, and the tooling is designed so that trying to would be
  obvious.

### Run the two release gates (if you are maintaining the standard itself)

```bash
./.venv/bin/python -m pytest
./.venv/bin/python -m openaisf.cli coverage
```

Both must pass. Coverage exiting non-zero means some external requirement is
neither covered nor excluded, and the standard cannot be released in that state.

### Rules the tooling enforces — do not fight them

- **Control identifiers are permanent.** Never renumber a control or change
  what tier it applies to — badges reference them. If a control must change,
  deprecate it and supersede it with a new one.
- **Provenance is computed.** A hand-written value that disagrees with the
  calculation is an error, not an override.
- **Threat catalogs impose no obligations.** OWASP, ATLAS and MCP-38 describe
  attacks; mapping a control to one can show relevance but never that the
  requirement already existed elsewhere.
- **Inventories are generated, not typed.** The AICM inventory comes from a
  workbook, the ATLAS inventory from the ATLAS site. Do not hand-edit them.
- **No `print()` in the library; only reports.** Output flows through the
  report layer so every output carries the attribution line.

---

## 6. Part E — Updating

The standard and the tooling move together, and the version consistency is
tested — the package, the spec and the changelog must all report the same
version, or the build fails.

### To update to a new release

```bash
git pull            # bring in the new version
./.venv/bin/pip install -e '.[dev]'   # (or the signing extra if you use it)
```

Then, before you trust a single result:

1. **Read `CHANGELOG.md`.** It lists what changed, including things that were
   previously *wrong*. OpenAISF records its own corrections rather than quietly
   fixing them.
2. **Re-run `check` and `publish`** for every system you assess. New controls
   may now apply to you; thresholds may have moved; a control you used may have
   been superseded.
3. **Expect a fail.** An update can make a system that passed yesterday fail
   today — that is the freshness model working, not a bug. The message will say
   what changed.
4. **Re-verify old badges.** Existing log entries still verify; the tooling is
   backward compatible with the evidence schema version `1.0`. If a future
   version changes that, the changelog will say so and tell you how to migrate.

### When figures on the websites disagree

Every figure on openaisf.org and trucert.ai is *generated output* from this
tooling. If a page figure disagrees with the spec, the page is wrong — the fix
belongs on the website, not in the standard.

---

## 7. Part F — Integrating with your organisation

### Into your CI pipeline (the highest-value integration)

Make `check` a step in your build. The exit codes are designed for this:

- `0` — conformant (build proceeds)
- `1` — not conformant (build fails, with the reason in the output)
- `2` — misconfigured (build fails, fix the setup)

Use `--json` to feed results into dashboards or ticketing. The failure output
names a real defect, so it routes straight to the team that can fix it.

### Into GRC and compliance workflows

```bash
./.venv/bin/python -m openaisf.cli export assessment-results \
    --context system.yaml --evidence ./evidence
```

This produces **OSCAL 1.1.2**, the format governance, risk and compliance tools
(and FedRAMP-style pipelines) natively understand. `export component-definition`
describes a reusable component.

### For AI agents (read-only, by design)

```bash
./.venv/bin/python -m openaisf.cli mcp
```

runs a small server that lets AI agents browse the catalog, resolve what
applies, and run checks and badge verification. It contains **no** tool that
writes evidence, signs or publishes — an agent reporting on its own conformance
is a claim, not evidence, and the build fails if a writing tool is ever added.
Connect it the same way you connect any MCP server to your agent platform.

### Badges in your README

Publish the badge line for your system where customers can see it — your
repository README, your customer portal. Because the badge carries its own
expiry and verifies without your cooperation, a stale badge lapses *by itself*,
which is exactly why relying on it means something.

### Inheriting assurance from suppliers

The cheapest assurance is assurance someone else already produced. When your
model provider (or any upstream component) publishes a badge, add their
certified controls to your scoping file's `inherits:` list instead of
re-proving them. Your `check` then imports what they proved. In procurement
terms, this is the moment the conversation changes from *"send us a PDF"* to
*"hand us the verify command."*

### The independent-assurance path (T3/T4)

When your sector requires an independent certifier, TruCert (TruSecure's
implementation of the Certifier role) provides the counter-signature and runs
the evidence machinery. Nothing in the standard gates access behind them — the
certifier's role is to add independent weight to the same open process. The
catalog, schemas, log format and CLI contain no reference to TruCert other than
attribution, by design; a dependency on a commercial vendor anywhere in the
specification is a defect and should be reported as one.

### A staged adoption path

1. **Scope one real system at T1.** A handful of controls. This exists to prove
   the loop runs end to end, not to produce assurance.
2. **Point one adapter at your gateway.** Whatever is already in the request
   path. Evidence stops being a document here.
3. **Run `check` in CI at T2 and let it fail.** The failures are the work queue,
   and they read as system defects, not missing paperwork.
4. **Publish, and hand a customer the verify command.** Procurement changes when
   they stop asking for a PDF.
5. **Ask your model provider for their badge.** Inherited controls are the cost
   lever.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No module named openaisf` | Install did not finish | Use the `PYTHONPATH=src` prefix, or reinstall (see the slow-volume note in Part A) |
| Install seems to hang forever | Slow disk (external drives, shared folders) | Use `PYTHONPATH=src ./.venv/bin/python -m openaisf.cli ...` instead of a full install |
| `check` exits 2 | A file is missing or the scoping file is malformed | Check the paths in `--context` and `--evidence`; validate the YAML indentation |
| `check` exits 1 and says "signed but not verifiable" | Producer key missing from keyring | Add the producer's public key to `--keyring` |
| Badge says expired right after you published | Evidence is older than the freshness window | Re-collect evidence so the newest record is current |
| A control you did not touch now fails | You updated the tooling and a new control applies | Read the CHANGELOG; the message says what changed |
| The website figure disagrees with the spec | The site figure is generated output that went stale | Fix the website, not the standard |

### The three questions to ask when a check fails

1. **Was evidence produced at all?** No record = fail, on purpose.
2. **Is it fresh and attributable?** Old or unsigned = fail, on purpose.
3. **Do the two layers agree?** Contradiction = fail, and no signed attestation
   can rescue it. A statement from an accountable person does not override
   telemetry.

---

## 9. Glossary

- **Adapter** — a small program that turns data from your existing systems into
  evidence records.
- **Badge** — the current conformance line for a system; it carries its own
  expiry.
- **Crosswalk** — the map between OpenAISF controls and external regimes.
- **Keyring** — a folder of public keys used to verify who produced evidence.
- **Lease** — the validity window of evidence, capped by tier.
- **Log** — the append-only, hash-chained record of published statements.
- **OSCAL** — the machine format that governance tools read.
- **Plane** — one of the two evidence layers (control / data).
- **Provenance** — how original a control is; always computed, never written.
- **Scoping file** — the YAML file that describes your system once.
- **SoA** — Statement of Applicability: the table of what applies to you.
- **Tier** — the assurance depth you claim (T1–T4).