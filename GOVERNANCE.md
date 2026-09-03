# Governance

**OpenAISF — created by Maarten Loose.**

## Current state: single maintainer

OpenAISF is at RFC stage with one maintainer. Decisions are made by the creator,
in public, with reasons recorded in commit messages and in the specification.

The intended sequence is adoption first, then transfer of the standard to a
neutral foundation with the commercial layers remaining separate. This document
will be replaced at that point rather than amended.

## What is deliberately hard to change

Some decisions are load-bearing and changing them silently breaks things people
have relied on.

**Control identifiers are permanent.** A control is never renumbered and never
has its tier applicability changed. Altering what an existing identifier requires
invalidates every badge that referenced it. Deprecate and supersede instead.

**Coverage must stay at zero gaps.** Every external requirement is covered by
named controls or excluded with a written reason. Adding a regime is additive: it
widens the denominator and reopens the gap list. `openaisf coverage` exits
non-zero while any gap remains, and that is a release gate rather than a report.

**Originality is computed, never asserted.** A hand-written `provenance` that
disagrees with the computation is an error, not an override.

**No control may claim prevention of the unpreventable** (principle P2).

**The standard names no vendor as required** (principle P7). Adapters are
out-of-tree and replaceable. The Certifier is a role, not a company.

## Changing a control

| Change | Route |
|---|---|
| Fixing a typo or clarifying rationale | Pull request |
| New control | Pull request with crosswalk and a stated failure mode |
| Changing what an existing control requires | Not permitted. Supersede it |
| Changing tier applicability | Not permitted. New control identifier |
| Adding an exclusion | Pull request; the reason is the substance of the review |
| Adding a regime | Pull request including the inventory and its licence position |

## The Certifier role

The standard defines a Certifier by obligation — independence, key management,
mandatory log participation, public disclosure of every certification issued,
suspended, expired and revoked — aligned to ISO/IEC 42006 so that accreditation
is a path rather than a claim.

A system can reach any tier, including T4, with no money changing hands and no
certifier involved.
