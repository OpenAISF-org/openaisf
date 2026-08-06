# Contributing to OpenAISF

Thank you for your interest in OpenAISF. The standard is being developed in
the open, and we welcome contributions of all kinds.

## Status

We are currently in **Draft v0.1 — Request for Comments**. The most valuable
contributions right now are:

1. **Comments on the RFC.** Read [rfc/RFC-OpenAISF-v0.1.md](rfc/RFC-OpenAISF-v0.1.md)
   and respond to the specific questions in §6 via issues.
2. **Crosswalk corrections and additions.** If a mapping in
   `spec/openaisf-crosswalk.yaml` is wrong or missing a regime, open a PR.
3. **Control improvements.** Better predicates, evidence requirements, or
   tier placement for any control in `spec/openaisf-controls.yaml`.
4. **CLI checks.** Implement additional `auto-static` or `auto-runtime`
   checks in `cli/openaisf.py` (see the `STATIC_CHECKS` registry).

## How to contribute

- **Small fixes:** open a pull request directly.
- **Substantive spec changes** (new/changed controls, tier redefinitions,
  crosswalk additions): open an issue first to discuss scope and approach.
- **New domains or first-class changes:** follow the RFC process — propose
  an RFC document in `rfc/` and seek community comment before implementation.

## Conformance contributions

If you are a vendor of a runtime-defense tool (AI firewall, red-team
platform, gateway), we are especially interested in:

- Mapping your product's capabilities to specific OpenAISF controls.
- Proposing new controls where you see gaps the standard doesn't cover.
- Becoming a reference implementation that certifies against OpenAISF.

## Style

- YAML must be valid and conform to the structure of the existing spec files.
- Python must pass `python -m py_compile` and avoid new hard dependencies
  beyond PyYAML for the reference CLI.
- Prefer machine-readable, testable predicates over prose.

## Licensing

By contributing, you agree your contributions are licensed under the
project's licenses (CC-BY-4.0 for the spec, Apache-2.0 for code). See
[LICENSE](LICENSE).

## Code of Conduct

All participants must adhere to the [Code of Conduct](CODE_OF_CONDUCT.md).
