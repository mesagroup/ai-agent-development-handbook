---
id: deps/licenses
domain: deps
locality: global
evidence: >-
  The evidence is a licence per dependency, mapped to SPDX ids, with
  `UNKNOWN` flagged. An empty license field is missing metadata, which is a
  finding in its own right here; reporting it as a permissive license is how
  this check returns a clean result for a graph nobody resolved. On a target
  where none of the routes below are available - no tree and no network - the
  check is `no-evidence`, never clean.
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
routes:
  - lang: python
    kind: command
    tool: pip-licenses
    argv: [pip-licenses]
    in_env: true
    needs: target-execution
    note: >-
      Reads resolved package metadata, so it needs the dependencies
      materialized - an installed environment - and answers nothing on a
      read-only clone; it starts the partition's interpreter, which is why it
      needs `target-execution`. No style it offers emits SPDX identifiers, in this form
      or the `--format json` one below, so mapping the names it reports onto
      the SPDX ids `evidence` asks for stays the reader's own step. That is a
      fact about the tool rather than about either form, and it is stated on
      both because an agent taking the default route reads only this one.
  - lang: python
    kind: command
    tool: pip-licenses
    argv: [pip-licenses, "--format", json]
    disposition: alternative
    in_env: true
    needs: target-execution
    note: >-
      `pip-licenses`'s `--format` chooses only how the list it prints is
      presented - `pip-licenses --format json` for the same list
      machine-readably - and no style it offers emits SPDX identifiers, so
      mapping the names it reports onto SPDX ids stays the reader's own step.
  - lang: python
    kind: procedure
    needs: resolved-tree
    note: >-
      Read each installed dist's `*.dist-info/METADATA` (`License` +
      `Classifier: License ::`). The record names the files to read rather
      than a command, so there is no argv to declare. It reads the same
      resolved metadata `pip-licenses` does and needs the environment for the
      same reason, but reads the files without starting the interpreter,
      which is why it stays `resolved-tree` where `pip-licenses` needs
      `target-execution`.
  - lang: python
    kind: procedure
    note: >-
      What answers with no environment installed, so a withheld grant leaves
      this check answerable on a Python partition with a lockfile: the licence
      of each pinned release is available from the registry without installing
      it. `https://pypi.org/pypi/<name>/<version>/json` carries the same three
      metadata channels the installed `METADATA` would, and all three must be
      read because none is universally populated - `license_expression` where
      the release declares an SPDX expression, `license` where it does not,
      and the `License ::` classifiers where neither is set. Read `license`
      with care: on older releases it holds the full licence text rather than
      an identifier, so a report echoing it verbatim prints a licence body
      where a name belongs. What the grant buys is the licences of what is
      actually installed, and coverage of any package the lockfile does not
      pin.
  - lang: typescript
    kind: command
    tool: npm sbom
    argv: [npm, sbom, "--package-lock-only", "--sbom-format", cyclonedx]
    note: >-
      npm has no licenses subcommand at all, and on an npm partition that
      does not mean the network fallback below: `package-lock.json` carries a
      `license` per package, so
      `npm sbom --package-lock-only --sbom-format cyclonedx` returns SPDX ids for the whole
      resolved graph off a read-only clone with no tree and no network. Run
      against a real npm target it populated the licence field for
      **944 of 945 components**, every copyleft entry among them, in about a
      second. Prefer it there, and treat the `@cdxgen/cdxgen` route
      below as the fallback for the partitions it cannot serve.
  - lang: typescript
    kind: command
    tool: pnpm licenses list
    argv: [pnpm, licenses, list]
    needs: resolved-tree
    note: >-
      The package manager's own subcommand, which is what to prefer where the
      manager has one. It reads resolved package metadata, so it needs
      `node_modules` present and answers nothing on a read-only clone.
  - lang: typescript
    kind: command
    tool: yarn licenses list
    argv: [yarn, licenses, list]
    needs: resolved-tree
    applies_when: >-
      The partition is on Yarn Classic. Yarn Berry's CLI reference documents
      no licenses subcommand, so treat Berry as having no built-in rather than
      assuming a command that will not run.
    note: >-
      The package manager's own subcommand, which is what to prefer where the
      manager has one. It reads resolved package metadata, so it needs
      `node_modules` present and answers nothing on a read-only clone.
  - lang: typescript
    kind: procedure
    tool: "@cdxgen/cdxgen"
    note: >-
      The fallback for the partitions the `npm sbom` route cannot serve: a
      registry package a one-shot runner can fetch, which reads
      `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock`. **Run it with
      `FETCH_LICENSE=true`**, because license resolution is off by default and
      an SBOM generated without it comes back with empty license fields. With
      `FETCH_LICENSE=true` it resolves licences from the lockfile over the
      network rather than from an installed tree, so it is the option that
      answers on a read-only clone - what it needs is network, not the tree,
      which is why this route carries no tier. Its docs warn that
      unauthenticated GitHub lookups get rate-limited; set `GITHUB_TOKEN` to
      avoid that. The record names the tool and the environment it needs and
      prescribes no command line, so there is no argv to declare and a
      `kind: command` route would have to invent one.
---

# License compatibility

Each dependency's license vs the project's license/policy: copyleft (GPL/AGPL/LGPL) pulled into a permissive project, "unknown"/missing license metadata, non-OSI or source-available licenses, license *changes* across a version bump.

## Severity

**Critical** - a disallowed/incompatible license in a dependency that is actually shipped/distributed; a dependency with no resolvable license in a published library.

**Important** - copyleft in a distributed artifact pending legal review.

## Fix

Replace or remove a disallowed-license dependency; update imports; re-test.

## Review lens

**License-verdict correctness** - is each verdict right for the project's own license and distribution model? (copyleft nuance, LGPL dynamic-linking, dual licenses)
