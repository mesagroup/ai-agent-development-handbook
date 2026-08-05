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

**JavaScript/TypeScript** - on an npm partition, `npm sbom --sbom-format cyclonedx` is built in and needs nothing fetched. There is no equivalent subcommand for the other package managers, so use `@cyclonedx/cdxgen`, which a one-shot runner can fetch and which reads `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock`. The npm-specific CycloneDX generator is `@cyclonedx/cyclonedx-npm`, and it requires npm and `package-lock.json`, so it is not an option on a pnpm or yarn partition and `npm sbom` already covers the case where it would apply. **Do not reach for the unscoped `cyclonedx-npm`**: that name on the npm registry is a 1 kB placeholder published by a third party to prevent dependency confusion, not the generator. It is the clearest example of why a `tooling` entry has to name something checked rather than something plausible - a one-shot runner resolves it, executes it, and produces no SBOM, which reads as a tool that ran and found nothing.
