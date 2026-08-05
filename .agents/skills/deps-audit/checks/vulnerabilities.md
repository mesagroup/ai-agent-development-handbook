---
id: deps/vulnerabilities
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [pip-audit, safety]
  typescript: ["npm audit", "pnpm audit", "yarn npm audit", osv-scanner]
---

# Known vulnerabilities

CVEs / advisories affecting the *pinned/resolved* versions, with the fixed version if one exists.

## Severity

**Critical** - a High/Critical CVE with a fix available.

**Important** - a Medium CVE.

**Minor** - a dev-only CVE not shipped to users.

## Tooling fallback

**Python** - `pip-audit` (PyPA, reads the environment or a requirements/lock file) or `safety`. Capture advisory id, affected range, and fixed version.

**JavaScript/TypeScript** - prefer the audit subcommand of the package manager the inventory records for the partition, which is already installed and already reads the lockfile that is present: `npm audit`, `pnpm audit`, `yarn npm audit` on Yarn Berry, `yarn audit` on Yarn Classic. Each is a subcommand of its own package manager rather than a publishable package, so a one-shot runner cannot fetch any of them, and `npm audit` is not a stand-in for the others even where the `npm` binary happens to be installed: it resolves from `package-lock.json`, which a pnpm or yarn partition does not have. Where no package-manager subcommand fits, `osv-scanner` is the ecosystem-neutral option - it reads `bun.lock`, `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock` directly, so it needs nothing installed in the target. It is distributed as a standalone binary rather than a registry package, so it is available when the audit environment already carries it and a one-shot runner cannot supply it either. If no path runs, the check is `no-evidence`, never a clean result.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.

## Review lens

**Advisory accuracy** - correct advisory id, affected range, and fixed version; no stale or false-positive advisories.

**Dependency attribution** - direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
