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

**JavaScript/TypeScript** - prefer the audit subcommand of the package manager the inventory records for the partition, which is already installed and already reads the lockfile that is present, but **read its version first**: npm retired the legacy audit endpoints (`/-/npm/v1/security/audits` and `/-/npm/v1/security/audits/quick`) on 2026-07-15 after brownouts from April, so a client still calling them returns 410 rather than a result. `npm audit` is unaffected, npm having moved its own client to `/-/npm/v1/security/advisories/bulk` first. `pnpm audit` works from **pnpm 11**, which rewired to that endpoint; on pnpm 10 or earlier it fails. `yarn npm audit` is Yarn Berry's maintained path. Yarn Classic's `yarn audit` calls a retired endpoint and Yarn 1 is unmaintained, so it will not be fixed - do not prefer it, and do not read its failure as a finding about the target. Each of these is a subcommand of its own package manager rather than a publishable package, so a one-shot runner cannot fetch any of them, and `npm audit` is not a stand-in for the others even where the `npm` binary happens to be installed: it resolves from `package-lock.json`, which a pnpm or yarn partition does not have.

For a Yarn Classic partition, or pnpm 10 and earlier, `osv-scanner` is the only option that works: it reads `bun.lock`, `package-lock.json`, `pnpm-lock.yaml` and `yarn.lock` directly, so it needs nothing installed in the target and does not depend on a registry audit endpoint at all. It is distributed as a standalone binary rather than a registry package, so a one-shot runner cannot supply it - an audit environment expected to cover those partitions needs it installed in advance. Where it is absent, the check is `no-evidence`, never a clean result. Note which case produced that status: a retired endpoint and a missing scanner are both `no-evidence`, but only the second is fixable by the audit environment.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.

## Review lens

**Advisory accuracy** - correct advisory id, affected range, and fixed version; no stale or false-positive advisories. On the JavaScript side the id is a GHSA and a corresponding CVE may not exist, so report the GHSA rather than inventing a CVE for it or dropping the advisory for want of one. pnpm 11 made this explicit by replacing `auditConfig.ignoreCves` with `ignoreGhsas`.

**Dependency attribution** - direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
