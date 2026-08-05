---
id: deps/freshness
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [uv, pip]
  typescript: ["npm outdated", "pnpm outdated", npm-check-updates]
---

# Freshness

Outdated (a newer release exists), yanked, or EOL versions; unpinned/floating direct dependencies (reproducibility + drift risk).

## Severity

**Important** - an unpinned *direct* runtime dependency; a yanked resolved version.

**Minor** - outdated-but-safe versions.

## Tooling fallback

**Python** - `uv pip list --outdated` / `pip list --outdated`; check the lockfile for floating direct pins; check PyPI for yanked releases.

**JavaScript/TypeScript** - prefer the package manager's own subcommand, already installed and already pointed at the lockfile that is present: `npm outdated`, `pnpm outdated`, `yarn outdated` on Yarn Classic. Yarn Berry dropped `yarn outdated` and offers only the interactive `yarn upgrade-interactive`, which an unattended audit cannot drive, so for a Berry partition - and as the package-manager-neutral option generally - use `npm-check-updates`, which is a registry package a one-shot runner can fetch and which selects the ecosystem with `--packageManager`. Read the partition's *own* lockfile for floating direct pins, whichever of `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock` or `bun.lock` that is; check the registry for deprecated/yanked releases.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.

## Review lens

**Dependency attribution** - direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
