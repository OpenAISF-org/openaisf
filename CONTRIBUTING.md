# Contributing

**OpenAISF — created by Maarten Loose.**

## Build gates

```bash
python -m venv .venv && ./.venv/bin/pip install -e '.[dev]'
./.venv/bin/python -m pytest          # must pass
./.venv/bin/python -m openaisf.cli coverage   # must exit 0
```

Both gates are hard. Coverage exiting non-zero means some external requirement
is neither covered nor excluded, and the release cannot freeze in that state.

## What makes a good control

Read an existing one first — `spec/catalog/d07-agentic-authority.yaml` is
representative. Then:

**State the failure, not only the requirement.** Every control carries a
`failure_mode` describing what goes wrong in practice, citing a named incident
where one exists. A vague `failure_mode` is grounds for rejection.

**Make it falsifiable.** If no observation could fail it, it is a value
statement and belongs in the preamble.

**Do not require an unachievable outcome.** Prompt injection is unsolved at the
model layer. A control requiring its prevention cannot be satisfied. Bound
consequence, require detection, require containment.

**Prefer emitted over attested.** Attestation is a debt. If a running system
could produce the evidence as a byproduct, require that instead.

**Fill in the crosswalk, or say why it is empty.** A control mapping nowhere is
claiming to be first-of-kind, and that claim is computed from this field.

## Dependencies

Runtime dependencies are `pyyaml` and `jsonschema`. That is the whole list, and
it is deliberate — this runs in other people's CI. Signing is behind an optional
extra. Adding a runtime dependency needs an architecture change, not a pull
request.

The MCP server is standard library only, including the JSON-RPC layer.

## Third-party material

**OpenAISF references external regimes; it never reproduces them.** Inventories
carry identifiers and OpenAISF-authored descriptors. The ISO and CSA inventories
carry no source-authored text at all — no titles, no objective or domain names.

`tests/test_licensing.py` fails the build if a restricted regime stops being
reference-only. If you are adding a regime, read `ATTRIBUTIONS.md` first and
include the licence position in the pull request; it is the substance of the
review, not paperwork around it.

## Things that will be refused

- Renumbering a control, or changing its tier applicability. Identifiers are
  permanent because badges reference them.
- Hand-writing a `provenance` value. It is computed.
- Adjusting a threshold to change a published figure. Where the originality
  count or coverage report is unsatisfactory, the remedy is additional control
  work, not a revised constant.
- Naming a vendor as required anywhere in the specification.
- Adding an MCP tool that writes evidence, signs, or publishes. An agent
  asserting its own conformance is a claim rather than evidence. A test fails the
  build where a tool name contains a writing verb.

## Licensing of contributions

Specification contributions are CC-BY-4.0; code is Apache-2.0. By contributing
you agree your work is licensed on those terms and that derivative works carry
*"Based on OpenAISF, created by Maarten Loose."*
