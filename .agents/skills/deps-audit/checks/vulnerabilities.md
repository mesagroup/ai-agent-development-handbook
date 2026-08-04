---
id: deps/vulnerabilities
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [pip-audit, safety]
  typescript: ["npm audit", osv-scanner]
---

# Known vulnerabilities

CVEs / advisories affecting the *pinned/resolved* versions, with the fixed version if one exists.

## Severity

**Critical** - a High/Critical CVE with a fix available.

**Important** - a Medium CVE.

**Minor** - a dev-only CVE not shipped to users.

## Tooling fallback

**Python** - `pip-audit` (PyPA, reads the environment or a requirements/lock file) or `safety`. Capture advisory id, affected range, and fixed version.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.

## Review lens

**Advisory accuracy** - correct advisory id, affected range, and fixed version; no stale or false-positive advisories.

**Dependency attribution** - direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
