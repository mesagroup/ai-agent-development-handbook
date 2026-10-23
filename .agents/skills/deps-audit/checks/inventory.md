---
id: deps/inventory
domain: deps
locality: global
optin: true
evidence: >-
  None of the file-parsing Python routes named here - `requirements`,
  `pipenv`, or the uv export - populates a licence field on any component, on
  any partition where it runs, so do not read an empty or absent licence
  field on an SBOM those produce as a permissive or unlicensed finding. That
  is a claim about those three forms rather than about this record: the
  `npm sbom` route below does populate licences, and so does
  `cyclonedx-py environment <path-to-venv-python>`, from the installed
  packages' metadata: on the seeded uv partition 6 of its 7 components
  carried one, the fixture's own editable package being the one without.
  The `cdxgen` route below populates them only from what it reads: on the seeded npm fixture all 78
  of its components carried one, from `package-lock.json`; on a read-only
  copy of the seeded pnpm fixture none of its 78 did, because
  `pnpm-lock.yaml` records no licence; and with that workspace installed,
  53 of the 78 did, read from `node_modules`. Licence *findings* are
  `deps/licenses`' and `deps/transitive-licenses`' to make, whatever produced
  the document.
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
    package: cyclonedx-bom
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
      partition is named nowhere above: none of these file-parsing commands
      reads a PEP 751 lock file, and this record points none at one it cannot
      read. The environment route below answers such a partition once step 1
      has materialized it under `target-execution`, and answers a PEP 621
      poetry partition the same way, because it reads what is installed rather
      than the manifest: measured on the seeded pylock partition it listed the
      7 installed components, and on the seeded poetry partition 8, pip
      included.
  - lang: python
    kind: command
    tool: cyclonedx-py
    package: cyclonedx-bom
    argv: [cyclonedx-py, environment, "<path-to-venv-python>"]
    disposition: alternative
    needs: target-execution
    note: >-
      `cyclonedx-py environment` reads the installed environment instead, and
      is the more accurate of the two where the run holds `target-execution`
      and step 1 materialized the tree, but it answers nothing on a read-only
      clone, so the file-parsing subcommands
      above are what this record prescribes by default.

      `<path-to-venv-python>` is the interpreter of the environment step 1
      materialized, and naming it is what points the tool at the target
      rather than at whatever environment the tool itself runs in. The
      package is `cyclonedx-bom`, whose command is `cyclonedx-py`, so the
      one-shot runner fetches it by that name and the tool runs isolated,
      reading the venv through the interpreter it is given. Bare, the
      command reports the runner's own sandbox: measured on the seeded uv
      partition, `uvx --from cyclonedx-bom cyclonedx-py environment` listed
      32 components, all of them the tool's own dependencies and none of the
      fixture's. Run inside the environment instead, with the tool layered
      on top by `uv run --with cyclonedx-bom`, it listed 37: the fixture's
      seven installed packages and the overlay's thirty beside them, with
      `packaging` twice, the fixture's 20.9 and the tool's 26.3, so the SBOM
      describes neither environment. Given the venv's interpreter it listed
      the seven, at the fixture's versions. The route needs
      `target-execution`, not `resolved-tree`: the tool starts that
      interpreter to read its path, which runs the `.pth` files in its
      `site-packages`, and a marker-writing `.pth` planted in the scratch
      venv was written on every run, in both forms. `-S`, the tool's flag
      for not importing `site` during that step, is no way round it: it
      keeps the venv's `site-packages` off the path altogether, and on the
      seeded uv and pip partitions it wrote no marker and emitted a document
      with no components at exit 0. Where the target's own package is
      installed editable, the document can list it twice: measured on the
      seeded pip and pipenv partitions, once with a purl and once as a
      distribution with a generated `bom-ref`, so a component count read off
      it counts that package twice.
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
    kind: command
    tool: "@cdxgen/cdxgen"
    argv: [cdxgen, "-t", js, "--no-install-deps", "-o", "-", .]
    note: >-
      The route for every partition `npm sbom` cannot serve: npm has the
      lockfile-only subcommand above, which comes first on an npm partition
      because it needs nothing fetched, and the other package managers have
      none this record can prescribe. `pnpm sbom` exists only from pnpm 11,
      and on a partition pinned below that it is not a command at all: on the
      seeded pnpm fixture, pinned to 9.15.9, pnpm switches itself to the pin
      and answers `Command "sbom" not found`. `@cdxgen/cdxgen` reads
      `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock`, whatever version
      of the manager wrote them. The package is the one cdxgen's own README
      names from v13 on. `@cyclonedx/cdxgen` is not a placeholder but the v12
      line, which its maintainers still patch on a release branch and which
      receives no v13 features, so a runner fetching it gets an older cdxgen
      rather than nothing. The command's bin is `cdxgen`, which is not the
      package name, so a runner names the package. In
      `cdxgen -t js --no-install-deps -o - .` each flag is load-bearing.
      `-t js` scans only JavaScript manifests, from the partition root.
      `--no-install-deps` because cdxgen installs dependencies by default,
      which writes `node_modules` into the target. `-o -` because the default
      output is a `bom.json` written into the working directory; `-` sends
      the document to stdout, and the progress lines go to stderr. Recursion
      is cdxgen's default, and it is what reaches a workspace's members: on
      the seeded pnpm workspace the document carried all seven seeded pins,
      the ones declared only in `apps/api` and `packages/core` included,
      is-number 6.0.0 through is-odd, and both member packages under the root
      component, 78 components in all. Measured with cdxgen's `--dry-run`
      report over the same tree, the only commands it executes are
      `ldd --version` and `pnpm root -g` and its only write is the stdout
      document, and the partition's `git status --porcelain --ignored` was
      empty after the run. Do not add `--dry-run` itself: it blocks the
      stdout write, so the run produces no document. Nothing has measured
      this command at workspace scale: the one run against a large pnpm
      workspace was the v12 package with `FETCH_LICENSE=true`, which this
      command does not set.
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
