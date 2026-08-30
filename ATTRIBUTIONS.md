# Attributions and intellectual property position

**OpenAISF — created by Maarten Loose.**

This document records the licence terms of every external regime OpenAISF maps
to, the basis on which OpenAISF references each one, and the actions still
required before commercial launch.

---

## 1. The governing principle

**OpenAISF references external regimes. It does not reproduce them.**

A crosswalk needs to answer one question: *does OpenAISF control D07-C03 address
the requirement that regime R labels X?* Answering it needs the identifier `X`.
It does not need R's words. Everything normative in OpenAISF is written by
OpenAISF.

This is not a workaround. It is the correct design for a conformance framework,
and it happens to sit on the safest ground available:

- **Identifiers are not protectable expression.** The US Copyright Office does
  not register words and short phrases including names and titles. A clause
  designation such as `A.6.2.6` or `LLM01` is a label, not authorship.
- **Exhaustive enumeration embodies no original selection.** Under *Feist
  Publications v. Rural Telephone Service* (499 U.S. 340), a factual compilation
  is protected only in its original selection or arrangement. Listing *every*
  clause of a standard involves no selection at all, and ordering them by the
  source's own numbering is functional rather than creative.
- **Merger.** Where a designation can be expressed in only one way, expression
  merges with idea and is unprotectable.
- **Referential use.** Stating "this control addresses ISO/IEC 42001 A.6.2.6" is
  a factual claim about a relationship. It is the same act as a citation.

Coverage accounting is unaffected by any of this. The engine counts identifiers.
Removing every word of third-party text from the inventories changed the
coverage report by exactly zero requirements.

---

## 2. Per-regime position

Each inventory carries machine-readable `licence`, `attribution` and
`reproduction` fields. `reproduction` is one of:

- **reference-only** — identifiers and factual designations only; no
  source-authored text of any kind
- **descriptive** — short source-authored names reproduced under a licence that
  expressly permits it
- **authored** — descriptors written by OpenAISF

| Regime | Licence | Reproduction | Basis |
|---|---|---|---|
| NIST AI RMF 1.0 | Public domain (17 U.S.C. §105) | authored | Works of NIST employees are not subject to US copyright |
| EU AI Act 2024/1689 | Free reuse | authored | EU legislation is reusable commercially subject to source acknowledgement (Commission Decision 2011/833/EU) |
| MITRE ATLAS | Apache-2.0 | descriptive | Licence expressly permits reproduction and distribution with attribution |
| MCP-38 | CC BY-4.0 | descriptive | arXiv submission licensed CC BY 4.0 |
| OWASP LLM Top 10 2025 | CC BY-SA-4.0 | authored | See §3 |
| ISO/IEC 42001:2023 | ISO copyright, all rights reserved | **reference-only** | See §4 |
| ISO/IEC 23894:2023 | ISO copyright, all rights reserved | **reference-only** | See §4 |
| CSA AICM v1.1.1 | CSA proprietary | **reference-only** | See §4 |

### Required notices

**MITRE ATLAS** — MITRE ATLAS, Copyright 2021–2026 MITRE, licensed under the
Apache License, Version 2.0. Technique identifiers and names are reproduced
under that licence. MITRE does not endorse OpenAISF.

**MCP-38** — *MCP-38: A Comprehensive Threat Taxonomy for Model Context Protocol
Systems (v1.0)*, Yi Ting Shen, Kentaroh Toyoda and Alex Leung, arXiv:2603.18063,
licensed CC BY 4.0.

**NIST** — Subcategory identifiers refer to the NIST AI Risk Management Framework
1.0 (NIST AI 100-1). NIST does not endorse OpenAISF. This material may be subject
to copyright in jurisdictions outside the United States.

**EU** — Article references are to Regulation (EU) 2024/1689. Source: EUR-Lex,
© European Union.

**OWASP** — Risk identifiers refer to the OWASP Top 10 for Large Language Model
Applications 2025, OWASP GenAI Security Project, licensed CC BY-SA 4.0.

**ISO** — Clause identifiers refer to ISO/IEC 42001:2023 and ISO/IEC 23894:2023,
copyright ISO/IEC. No ISO text is reproduced. Obtain the standard from ISO.

**CSA** — Control identifiers refer to the CSA AI Controls Matrix v1.1.1,
copyright Cloud Security Alliance. No CSA text is reproduced. Obtain the AICM
from CSA.

---

## 3. OWASP and the ShareAlike problem

OWASP GenAI Security Project material is licensed **CC BY-SA 4.0**. ShareAlike
propagates to *Adapted Material*: a derivative built on BY-SA content must itself
be licensed BY-SA or a compatible licence. The OpenAISF specification is
CC-BY-4.0, which is **not** compatible in that direction — BY-SA content cannot
be relicensed as BY.

Ignoring this would be a real defect. Anyone could argue the whole catalog had
become BY-SA, which would undermine the licence architecture and the attribution
requirement in §17 of the architecture document.

The resolution is to avoid producing Adapted Material at all. The inventory
carries the `LLM01`–`LLM10` identifiers, which are designations rather than
expression, and descriptors written by OpenAISF. Attribution is given regardless,
as a matter of practice rather than obligation.

**Currency note.** OWASP published a 2026 edition on 4 August 2026. It must be
added as a **separate regime**, not as an overwrite, because existing controls
already reference the 2025 identifiers and identifiers are permanent.

---

## 4. The three restricted regimes

### ISO/IEC 42001:2023

ISO's licence agreement does not grant rights of reproduction, distribution,
adaptation, incorporation or creation of derivative works, in whole or in part.
There is no fair-dealing carve-out broad enough to cover republishing the Annex A
control titles in a commercially leveraged product.

The inventory is therefore reference-only: clause identifiers and the objective
number each falls under, both facts about the standard's own numbering. No ISO
title, objective name or normative text appears anywhere in this repository.

Note for the record that *ASTM v. Public.Resource.Org* (D.C. Cir., 12 September
2023) held that **non-commercial** dissemination of standards incorporated by
reference into law was fair use, while expressly holding that those standards
remain under copyright and do not enter the public domain. That authority runs
*against* a commercial reproducer, which is why OpenAISF does not rely on fair
use for ISO material and reproduces none of it.

### ISO/IEC 23894:2023

Same position as ISO/IEC 42001 above. The inventory is reference-only: 13 clause
identifiers (5.2–5.7, 6.1–6.7) and nothing else — clauses 1–3 and the annexes
carry no substantive obligation and are not inventoried. 23894 is guidance
adapting ISO 31000 to AI systems rather than certifiable requirements, so its
clauses are broad headings and no mapping to one is ever full strength. The
clause enumeration follows the official NIST crosswalk (NIST AI RMF 1.0 to
ISO/IEC 23894:2023, revised edition, airc.nist.gov) rather than the standard
itself, so no memory or unlicensed reproduction is the source of the clause list.

### CSA AICM v1.1.1

CSA publishes the AICM on terms that permit free internal and non-commercial use
but require a CSA licence to customise it, create derivative works, or use it
commercially — including "leveraging it within your products". Fair-use quoting
with attribution is separately permitted.

The generator deliberately reads **column C (Control ID) only**. Column B
(Control Title) and column D (Control Specification) are CSA-authored text and
are never extracted. The inventory holds 247 identifiers and a domain code
derived from each identifier's own prefix.

**This reduces exposure. It does not eliminate it.** See §5.

---

## 5. Actions required before commercial launch

1. **Obtain a CSA commercial licence.** CSA sells one covering commercial use of
   the AICM. OpenAISF is a free open standard, but TruCert is a commercial
   certification product built on it, and a reasonable reading is that AICM
   identifiers are being leveraged within a commercial product. CSA offers the
   licence; buying it is cheap certainty and removes the only structurally
   awkward dependency in the crosswalk. **Owner: Maarten Loose. Blocking for
   TruCert commercial launch, not for publishing the open standard.**

2. **Notify ISO of the crosswalk.** No permission is required to cite clause
   numbers, and none is being sought. A short factual notice describing what
   OpenAISF does and does not reproduce is cheap goodwill and creates a record
   predating any dispute. **Non-blocking.**

3. **Counsel review of this document and the three inventories marked
   reference-only or authored.** Specifically: the ShareAlike analysis in §3, the
   *Feist* argument in §1, and whether the CSA licence in item 1 is required or
   merely prudent. **Blocking for commercial launch.**

4. **Trademark registration** for `OpenAISF` and `TruCert`. Copyright licensing
   does not protect a name; trademark does. This is what actually stops someone
   shipping a fake conformance mark. **Blocking for the badge to mean anything.**

5. **Re-run this analysis whenever a regime is added.** The inventory schema
   makes `licence`, `attribution` and `reproduction` mandatory, and
   `tests/test_licensing.py` fails the build if a restricted regime stops being
   reference-only. Adding a regime to the `RESTRICTED` set in that file is a
   legal decision, not a style choice.

---

## 6. What OpenAISF licenses to others

Specification (`schema/`, `spec/`) — **CC-BY-4.0**.
Tooling (`src/`, `tools/`) — **Apache-2.0**.

Derivative works must carry: *Based on OpenAISF, created by Maarten Loose.*

That attribution requirement is a condition of the licence, and it is the
mechanism by which the creator's name stays attached to anything built on this.
It applies to the OpenAISF-authored material only. It does not and cannot extend
to the third-party identifiers referenced above, which remain the property of
their respective owners.
