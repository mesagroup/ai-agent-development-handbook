---
id: deps/inventory
domain: deps
locality: global
optin: true
evidence: >-
  No route this record offers - `requirements`, `pipenv`, or the uv export -
  populates a licence field on any component, on any partition where it runs.
  `deps/licenses` is the only source of licence evidence in this family: do
  not read an empty or absent licence field on an SBOM component as a
  permissive or unlicensed finding, and do not expect this check to surface
  one.
handbook: []
handbook_note: >-
  The handbook's dependency-accounting clause is satisfied by pinning direct
  dependencies and committing the lockfile as the record of what actually ran;
  it never asks for a generated SBOM artifact, so no clause grounds an
  SBOM-completeness check specifically.
routes:
  - lang: python
    kind: command
    tool: cyclonedx-py
    argv_by_partition:
      uv: [uv, export, "--format=cyclonedx1.5", "--frozen"]
      pip: [cyclonedx-py, requirements]
      poetry: [cyclonedx-py, poetry]
      pipenv: [cyclonedx-py, pipenv]
    own_runner: [uv]
    note: >-
      One subcommand per partition, matching the partition's own dependency
      file, or the tool's native SBOM export where there is no subcommand for
      it. `cyclonedx-py` has no uv subcommand, so on a uv-locked partition
      the native export is
      `uv export --format=cyclonedx1.5 --frozen`: it produces a well-formed
      CycloneDX 1.5 document (6 components, `specVersion` 1.5, no `licenses`
      field). That it also validates cleanly against `cyclonedx-python-lib`'s
      own `JsonStrictValidator` is a scratch-copy measurement, not an
      artifact of the python lens smoke run, whose harness never ran that
      validator. That command is `uv`'s own export rather than this route's
      tool, which is why the uv partition names its own runner: a fetch in
      front of it would report the fetched package's version as the one that
      answered. `cyclonedx-py poetry` reads the project name from
      `[tool.poetry]` and fails outright - `CRITICAL | CDX > 'name'`, exit 1,
      no SBOM written - against a manifest that declares its metadata under
      PEP 621's `[project]` instead, which is the layout poetry 2 pushes
      projects toward and which raises no deprecation warning, so this is the
      ordinary modern poetry manifest rather than an edge case, and this
      record has no route through `cyclonedx-py poetry` for it. The PEP 751
      partition is named nowhere above, which is this record prescribing
      nothing for a PEP 751 lock file rather than pointing a subcommand at
      one it cannot read.
  - lang: python
    kind: command
    tool: cyclonedx-py
    argv: [cyclonedx-py, environment]
    disposition: alternative
    note: >-
      `cyclonedx-py environment` reads the installed environment instead, and
      is the more accurate of the two where a tree is available, but it
      answers nothing on a read-only clone, so the file-parsing subcommands
      above are what this record prescribes by default.
  - lang: typescript
    kind: command
    tool: npm sbom
    argv: [npm, sbom, "--package-lock-only", "--sbom-format", cyclonedx]
    note: >-
      On an npm partition,
      `npm sbom --package-lock-only --sbom-format cyclonedx` reads the
      lockfile and needs nothing fetched. Without `--package-lock-only`,
      `npm sbom` loads the installed tree instead, and where that tree
      doesn't fully resolve it throws `ESBOMPROBLEMS` rather than emitting a
      partial SBOM - so this record prescribes the lockfile-only mode, not
      the default one. The npm-specific CycloneDX generator is
      `@cyclonedx/cyclonedx-npm`, and it requires npm and
      `package-lock.json`, so it is not an option on a pnpm or yarn partition
      and this command already covers the case where it would apply.
  - lang: typescript
    kind: procedure
    tool: "@cyclonedx/cdxgen"
    note: >-
      There is no equivalent subcommand for the other package managers, so
      use `@cyclonedx/cdxgen`, which a one-shot runner can fetch and which
      reads `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock`. The record
      names the tool and prescribes no command line, so there is no argv to
      declare and a `kind: command` route would have to invent one.
  - lang: typescript
    kind: command
    tool: cyclonedx-npm
    argv: [dlx, cyclonedx-npm]
    disposition: forbidden
    note: >-
      **Do not reach for the unscoped `cyclonedx-npm`**: that name on the npm
      registry is a 1 kB placeholder published by a third party to prevent
      dependency confusion, not the generator. It is the clearest example of
      why the tooling a record names has to be something checked rather than
      something plausible - a one-shot runner resolves it, executes it, and
      produces no SBOM, which reads as a tool that ran and found nothing.
---

# Inventory (SBOM completeness)

SBOM completeness.

## Severity

**Minor** - missing SBOM.
