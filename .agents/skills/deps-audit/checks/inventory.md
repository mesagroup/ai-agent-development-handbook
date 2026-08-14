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

**Python** - `cyclonedx-py`'s `requirements`, `poetry` or `pipenv` subcommand, matching the partition's own dependency file, or the tool's native SBOM export. `cyclonedx-py` has no uv subcommand, so on a uv-locked partition the native export is `uv export --format=cyclonedx1.5 --frozen`: it produces a CycloneDX 1.5 document that validates cleanly against `cyclonedx-python-lib`'s own `JsonStrictValidator`. `cyclonedx-py poetry` reads the project name from `[tool.poetry]` and fails outright - `CRITICAL | CDX > 'name'`, exit 1, no SBOM written - against a manifest that declares its metadata under PEP 621's `[project]` instead, which is the layout poetry 2 pushes projects toward and which raises no deprecation warning, so this is the ordinary modern poetry manifest rather than an edge case, and this record has no route through `cyclonedx-py poetry` for it. `cyclonedx-py environment` reads the installed environment instead, and is the more accurate of the two where a tree is available, but it answers nothing on a read-only clone, so prescribe the file-parsing subcommand as the default.

No route this record offers - `requirements`, `pipenv`, or the uv export - populates a licence field on any component, on any partition where it runs. `deps/licenses` is the only source of licence evidence in this family: do not read an empty or absent licence field on an SBOM component as a permissive or unlicensed finding, and do not expect this check to surface one.

**JavaScript/TypeScript** - on an npm partition, `npm sbom --package-lock-only --sbom-format cyclonedx` reads the lockfile and needs nothing fetched. Without `--package-lock-only`, `npm sbom` loads the installed tree instead, and where that tree doesn't fully resolve it throws `ESBOMPROBLEMS` rather than emitting a partial SBOM - so this record prescribes the lockfile-only mode, not the default one. There is no equivalent subcommand for the other package managers, so use `@cyclonedx/cdxgen`, which a one-shot runner can fetch and which reads `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock`. The npm-specific CycloneDX generator is `@cyclonedx/cyclonedx-npm`, and it requires npm and `package-lock.json`, so it is not an option on a pnpm or yarn partition and `npm sbom` already covers the case where it would apply. **Do not reach for the unscoped `cyclonedx-npm`**: that name on the npm registry is a 1 kB placeholder published by a third party to prevent dependency confusion, not the generator. It is the clearest example of why a `tooling` entry has to name something checked rather than something plausible - a one-shot runner resolves it, executes it, and produces no SBOM, which reads as a tool that ran and found nothing.
