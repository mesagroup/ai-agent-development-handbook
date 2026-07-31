---
id: deps/freshness
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [uv, pip]
---

# Freshness

Outdated (a newer release exists), yanked, or EOL versions; unpinned/floating direct dependencies (reproducibility + drift risk).

## Severity

**Important** - an unpinned *direct* runtime dependency; a yanked resolved version.

**Minor** - outdated-but-safe versions.

## Tooling fallback

**Python** - `uv pip list --outdated` / `pip list --outdated`; check the lockfile for floating direct pins; check PyPI for yanked releases.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.
