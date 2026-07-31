---
id: deps/inventory
domain: deps
locality: global
optin: true
handbook: []
handbook_note: >-
  The handbook's dependency-accounting clause is satisfied by pinning direct dependencies and committing the lockfile as the record of what actually ran; it never asks for a generated SBOM artifact, so no clause grounds an SBOM-completeness check specifically.
tooling:
  python: [cyclonedx-py]
---

# Inventory (SBOM completeness)

SBOM completeness.

## Severity

**Minor** - missing SBOM.

## Tooling fallback

**Python** - `cyclonedx-py` or the tool's native SBOM export.
