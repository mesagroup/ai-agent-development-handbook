---
id: deps/freshness
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [uv, pip]
  typescript: [npm]
---

# Freshness

Outdated (a newer release exists), yanked, or EOL versions; unpinned/floating direct dependencies (reproducibility + drift risk).

## Severity

**Important** - an unpinned *direct* runtime dependency; a yanked resolved version.

**Minor** - outdated-but-safe versions.

## Tooling fallback

**Python** - `uv pip list --outdated` / `pip list --outdated`; check the lockfile for floating direct pins; check PyPI for yanked releases.

**TypeScript** - `npm outdated`; check `package-lock.json` for floating direct pins; check the registry for deprecated/yanked releases.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.

## Review lens

Direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
