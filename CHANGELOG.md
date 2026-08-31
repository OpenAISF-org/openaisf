# Changelog

**OpenAISF — created by Maarten Loose.**

## Unreleased

### Added

- **ISO/IEC 23894:2023 added to the coverage engine.** The AI risk-management
  guidance is inventoried as a ninth regime — its 13 substantive body clauses
  (framework 5.2–5.7, process 6.1–6.7), with clauses 1–3 and the annexes not
  inventoried as they carry no obligation. Because 23894 is guidance rather
  than certifiable requirements, every item is non-atomic and every mapping to
  it is partial strength: 13 clauses covered by 15 controls across governance
  (D01), risk (D02), monitoring (D14), incident (D16), change (D18) and
  evidence (D19), zero exclusions, provenance unchanged. The inventory is
  reference-only like ISO 42001's: clause identifiers only, no ISO text, with
  the clause enumeration attested by the official NIST crosswalk rather than
  reproduced from the standard.

- **ISO/IEC 23894:2023 carried through the documentation.** The regime is now
  named wherever the other eight are: the MANUAL and USECASES regime lists,
  the ATTRIBUTIONS per-regime table with its own §4 restricted-regime analysis,
  and the RFC §9 note on its guidance position.

### Fixed

- **README overstated the MCP server's independence.** It said the server is
  "standard library only"; it imports `pyyaml` (a runtime dependency, so
  always present) and the OpenAISF package itself. The claim is now the true
  one: the server adds nothing beyond the two runtime dependencies, speaking
  plain stdio JSON-RPC by hand.

## v1.0.0a2 — 7 August 2026

### Added

- **Six original AI data governance controls.** Existing data governance was
  written for records in databases; an AI system creates stores nobody
  inventories and derives artefacts that silently lose their classification.
  `D03-C11` prompts and completions inventoried as a data store rather than as
  logs. `D03-C12` derived artefacts inherit source classification and residency.
  `D03-C13` deletion proven by attempted retrieval including semantic queries,
  not by a deletion record. `D03-X01` context assembly may not combine data
  classes without recorded authority. `D03-X02` operational data may not be
  reused for training outside its collection purpose. `D03-X03` tenant isolation
  in shared retrieval and cache layers verified by attempted cross-boundary
  retrieval.

All six compute as OpenAISF-original. The catalog is now 118 controls, 36 of
them with no incumbent equivalent, and data governance is 16 controls of which
7 are original. Coverage remains at zero gaps and the applicability ceilings
still hold: a typical tier-2 system resolves to 35 controls against a limit of
40.

### Changed

- README and website now lead with what OpenAISF requires that nothing else
  does. Both previously opened with the crosswalk coverage table, which framed a
  framework with 36 original controls as a mapping exercise.

## v1.0.0a1 — 7 August 2026

A rewrite rather than an upgrade. The following section records the v0.1 claims
that were incorrect.

### Corrections to v0.1

**The headline claim had expired.** v0.1 said that nobody publishes a standard as
a machine-readable artefact with an executable conformance tool. That was
defensible in early 2026 and is not any more. OSCAL is on its way to being
mandatory for FedRAMP providers; there is published work proposing OSCAL as the
interchange format for AI compliance evidence with a working SDK; Policy Cards
claims to be the first machine-readable governance format combining ISO 42001
with runtime enforcement; AIP addresses verifiable agent delegation; DEMM-Bench
benchmarks agent-runtime evidence sufficiency. All are now cited as prior art.
The remaining defensible claim is narrower: a conformance state that expires
without intervention.

**The crosswalk claimed coverage it could not demonstrate.** 59 controls cannot
be a superset of a surface containing 38 ISO Annex A controls, 72 NIST
subcategories, 247 CSA control objectives and the operative articles of the EU AI
Act. Mapping outward from your own controls shows what you found, never what you
missed. The direction is now inverted and the gap count is a release gate.

**The originality figure was maintained by hand and was published incorrectly on
two occasions.** It is now computed from the crosswalk.

### What v1.0 is

| | v0.1 | v1.0 |
|---|---|---|
| Domains | 9 | 20 |
| Controls | 59 | 112 |
| External requirements tracked | asserted | **677, resolved to zero gaps** |
| Conformance model | an event | **a state with a heartbeat** |
| Evidence | files exist | **two planes, signed at the producer** |
| Badge | static | **expires on its own; verifiable by a stranger** |
| Inheritance | none | **assurance decay propagates downstream** |
| Tooling | one command | `scope · check · publish · verify · badge · coverage · export · mcp` |
| Tests | none | 170 |

### Added

- **The conformance lease.** Statements carry their own `stale_after` and
  `expires_at`. A badge is rendered from the reader's clock, so it goes stale in
  somebody else's README with nobody notified. No lease outlives its tier ceiling.
- **Two-plane evidence.** A declared policy contradicted by its own telemetry
  fails, and an attestation cannot resolve it. Fabrication is disqualifying: it
  blocks even where the control is only recommended, and revokes rather than
  degrades.
- **Computed applicability.** Controls declare their own scope, so a typical
  tier-2 system resolves to 34 controls out of 112 and tier 1 to four. There is a
  test that fails the build if those numbers creep up.
- **The rogue-agent control chain** across D07, D15 and D16 — bound, detect,
  contain, recover, prove — with detection and containment proven by drill and
  recorded as MTTD and MTTC.
- **Detection that only agents make possible**: intent–action divergence,
  business-purpose divergence, swarm and velocity signatures, provenance breaks.
- **Hash-chained transparency log** and `openaisf verify`, which needs no account
  and no relationship with the subject.
- **Assurance inheritance** that degrades when the upstream lease does, and
  refuses to let assurance be laundered upward through a dependency.
- **MCP server**, deliberately read-and-check only. An agent that submits
  evidence about its own conformance is a claim, not evidence.
- **OSCAL 1.1.2 export** for Assessment Results and Component Definition.
- **Pluggable signing** where the difference between schemes is enforced:
  a digest proves a record is intact and not who produced it, so publishing at
  tier 3 refuses it.
- **The intellectual property position**, in `ATTRIBUTIONS.md`. OpenAISF
  references other standards by identifier and reproduces none of their text.

### Changed

- Control identifiers were renumbered once, here, and are permanent from now on.
  A control is never renumbered again and never has its tier applicability
  changed, because badges reference them. Deprecate and supersede instead.
- Originality is computed from mapping strength rather than asserted. Threat
  catalogues — OWASP, ATLAS, MCP-38 — describe attacks and impose no
  requirements, so a mapping to one can never establish that something is
  already required. 30 of 112 controls are original by that computation.
- The OWASP LLM Top 10 2026 edition is tracked as a **separate regime**, because
  it reuses `LLM01`–`LLM10` for a re-ranked set of risks. Merging the editions
  would silently change the meaning of every existing crosswalk entry.

### Removed

- The v0.1 catalog, crosswalk and CLI. Replaced wholesale.
- `LICENSE` as a single file, split into the specification and tooling licences
  it always should have been.
- `site/`. The website moved to its own repository,
  [openaisf/website](https://github.com/openaisf/website), so that it has one
  source rather than two copies drifting apart. This repository is the standard;
  that one is the site.

### Known gaps

- The reference adapter signs with an integrity digest by default. That is honest
  for local development and inadmissible from tier 3, which the tooling enforces.
- Freshness windows, grace periods and tier ceilings are set from judgement, not
  measurement. Operational data should move them.
- Intent–action divergence detection is the most original control here and the
  most likely to be noisy. It needs a measured baseline before it goes normative
  below tier 3.

## v0.1 — August 2026

Initial public draft. Superseded.
