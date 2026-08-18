---
id: deps/licenses
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [pip-licenses]
  typescript: ["npm sbom", "pnpm licenses list", "yarn licenses list", "@cyclonedx/cdxgen"]
needs:
  resolved-tree: [pip-licenses, pnpm licenses list, yarn licenses list]
ungranted_note: >-
  On a Python partition with a lockfile, the licence of each pinned release is available
  from the registry without installing it: `https://pypi.org/pypi/<name>/<version>/json`
  carries the same three metadata channels the installed `METADATA` would, and all
  three must be read because none is universally populated - `license_expression` where
  the release declares an SPDX expression, `license` where it does not, and the
  `License ::` classifiers where neither is set. Read `license` with care: on older
  releases it holds the full licence text rather than an identifier, so a report
  echoing it verbatim prints a licence body where a name belongs. What the grant buys
  is the licences of what is actually installed, and coverage of any package the
  lockfile does not pin.
---

# License compatibility

Each dependency's license vs the project's license/policy: copyleft (GPL/AGPL/LGPL) pulled into a permissive project, "unknown"/missing license metadata, non-OSI or source-available licenses, license *changes* across a version bump.

## Severity

**Critical** - a disallowed/incompatible license in a dependency that is actually shipped/distributed; a dependency with no resolvable license in a published library.

**Important** - copyleft in a distributed artifact pending legal review.

## Tooling fallback

**Python** - `pip-licenses` (with `--format` for SPDX-ish output), or read each installed dist's `*.dist-info/METADATA` (`License` + `Classifier: License ::`). `pip-licenses`'s `--format` chooses only how the list it prints is presented - `pip-licenses --format json` for the same list machine-readably - and no style it offers emits SPDX identifiers, so mapping the names it reports onto SPDX ids stays the reader's own step. Map to SPDX ids; flag `UNKNOWN`.

**JavaScript/TypeScript** - prefer the package manager's own subcommand where it has one: `pnpm licenses list`, and `yarn licenses list` on Yarn Classic. npm has no licenses subcommand at all, and Yarn Berry's CLI reference documents none, so treat both as having no built-in rather than assuming a command that will not run. On an npm partition that does not mean the network fallback: `package-lock.json` carries a `license` per package, so `npm sbom --package-lock-only --sbom-format cyclonedx` - the command `deps/inventory` already prescribes - returns SPDX ids for the whole resolved graph off a read-only clone with no tree and no network. Run against a real npm target it populated the licence field for **944 of 945 components**, every copyleft entry among them, in about a second. Prefer it there, and treat what follows as the fallback for the partitions it cannot serve. The fallback is `@cyclonedx/cdxgen`, which a one-shot runner can fetch and which reads `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock` - **run it with `FETCH_LICENSE=true`**, because license resolution is off by default and an SBOM generated without it comes back with empty license fields. An empty license field is missing metadata, which is a finding in its own right here; reporting it as a permissive license is how this check returns a clean result for a graph nobody resolved. Map to SPDX ids; flag `UNKNOWN`.

`pip-licenses`, `pnpm licenses list` and `yarn licenses list` each read resolved package metadata, so they need the dependencies materialized - an installed environment for `pip-licenses`, `node_modules` for the pnpm/yarn subcommands - and answer nothing on a read-only clone. `@cyclonedx/cdxgen` is the exception: with `FETCH_LICENSE=true` it resolves licences from the lockfile over the network rather than from an installed tree, so it is the option that answers on a read-only clone - what it needs is network, not the tree. Its docs warn that unauthenticated GitHub lookups get rate-limited; set `GITHUB_TOKEN` to avoid that. On a target where none of these are available - no tree and no network - the check is `no-evidence`, never clean.

## Fix

Replace or remove a disallowed-license dependency; update imports; re-test.

## Review lens

**License-verdict correctness** - is each verdict right for the project's own license and distribution model? (copyleft nuance, LGPL dynamic-linking, dual licenses)
