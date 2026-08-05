---
id: deps/inventory
domain: deps
locality: global
optin: true
handbook: []
handbook_note: >-
  The handbook's dependency-accounting clause is satisfied by pinning direct
  dependencies and committing the lockfile as the record of what actually ran;
  it never asks for a generated SBOM artifact, so no clause grounds an
  SBOM-completeness check specifically.
tooling:
  python: [cyclonedx-py]
  typescript: ["npm sbom", "@cyclonedx/cdxgen"]
---

# Inventory (SBOM completeness)

SBOM completeness.

## Severity

**Minor** - missing SBOM.

## Tooling fallback

**Python** - `cyclonedx-py` or the tool's native SBOM export.

**JavaScript/TypeScript** - on an npm partition, `npm sbom --sbom-format cyclonedx` is built in and needs nothing fetched. There is no equivalent subcommand for the other package managers, so use `@cyclonedx/cdxgen`, which a one-shot runner can fetch and which reads `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock`. `cyclonedx-npm` is the npm-specific CycloneDX generator and is a real package, but it requires npm and `package-lock.json`, so it is not an option on a pnpm or yarn partition and `npm sbom` already covers the case where it would apply.
