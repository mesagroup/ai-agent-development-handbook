---
id: deps/licenses
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [pip-licenses]
  typescript: ["pnpm licenses list", "yarn licenses list", "@cyclonedx/cdxgen"]
needs:
  resolved-tree: [pip-licenses, pnpm licenses list, yarn licenses list]
---

# License compatibility

Each dependency's license vs the project's license/policy: copyleft (GPL/AGPL/LGPL) pulled into a permissive project, "unknown"/missing license metadata, non-OSI or source-available licenses, license *changes* across a version bump.

## Severity

**Critical** - a disallowed/incompatible license in a dependency that is actually shipped/distributed; a dependency with no resolvable license in a published library.

**Important** - copyleft in a distributed artifact pending legal review.

## Tooling fallback

**Python** - `pip-licenses` (with `--format` for SPDX-ish output), or read each installed dist's `*.dist-info/METADATA` (`License` + `Classifier: License ::`). Map to SPDX ids; flag `UNKNOWN`.

**JavaScript/TypeScript** - prefer the package manager's own subcommand where it has one: `pnpm licenses list`, and `yarn licenses list` on Yarn Classic. npm has no licenses subcommand at all, and Yarn Berry's CLI reference documents none, so treat both as having no built-in and go to the fallback rather than assuming a command that will not run. The fallback is `@cyclonedx/cdxgen`, which a one-shot runner can fetch and which reads `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock` - **run it with `FETCH_LICENSE=true`**, because license resolution is off by default and an SBOM generated without it comes back with empty license fields. An empty license field is missing metadata, which is a finding in its own right here; reporting it as a permissive license is how this check returns a clean result for a graph nobody resolved. Map to SPDX ids; flag `UNKNOWN`.

`pip-licenses`, `pnpm licenses list` and `yarn licenses list` each read resolved package metadata, so they need the dependencies materialized - an installed environment for `pip-licenses`, `node_modules` for the pnpm/yarn subcommands - and answer nothing on a read-only clone. `@cyclonedx/cdxgen` is the exception: with `FETCH_LICENSE=true` it resolves licences from the lockfile over the network rather than from an installed tree, so it is the option that answers on a read-only clone - what it needs is network, not the tree. Its docs warn that unauthenticated GitHub lookups get rate-limited; set `GITHUB_TOKEN` to avoid that. On a target where none of these are available - no tree and no network - the check is `no-evidence`, never clean.

## Fix

Replace or remove a disallowed-license dependency; update imports; re-test.

## Review lens

**License-verdict correctness** - is each verdict right for the project's own license and distribution model? (copyleft nuance, LGPL dynamic-linking, dual licenses)
