---
id: deps/freshness
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [uv, pip]
  typescript: ["npm outdated", "pnpm outdated", npm-check-updates]
needs:
  resolved-tree: [uv, pip, npm outdated, pnpm outdated]
---

# Freshness

Outdated (a newer release exists), yanked, or EOL versions; unpinned/floating direct dependencies (reproducibility + drift risk).

## Severity

**Important** - an unpinned *direct* runtime dependency; a yanked resolved version.

**Minor** - outdated-but-safe versions.

## Tooling fallback

**Python** - `uv pip list --outdated` / `pip list --outdated`, both of which read the installed environment rather than the lockfile, so they need the tree resolved; the lockfile scan for floating direct pins is the part that survives without one. Check PyPI for yanked releases.

**JavaScript/TypeScript** - default to `npm-check-updates`, a registry package a one-shot runner can fetch and which selects the ecosystem with `--packageManager`; it reads `package.json` against the registry rather than any installed state, so it is the option that answers on a read-only clone and the default on any partition the audit has not been granted a tree for. Where the tree is present, prefer the package manager's own subcommand instead: `npm outdated`, `pnpm outdated`, `yarn outdated` on Yarn Classic. Both `npm outdated` and `pnpm outdated` read *installed* state, not the lockfile that happens to be present - `npm outdated` on a tree with no `node_modules` reports every production dependency as `MISSING`, and its own source drops any non-production dependency that is missing from the output entirely, so devDependencies vanish rather than being reported as outdated; `pnpm outdated` hard-errors with no lockfile at all, and with a lockfile but no install it reports every dependency as outdated because the installed version is undefined. Neither is a fallback for the untreed case, only a preference once the tree exists. Yarn Berry dropped `yarn outdated` and offers only the interactive `yarn upgrade-interactive`, which an unattended audit cannot drive, so use `npm-check-updates` for a Berry partition too. Read the partition's *own* lockfile for floating direct pins, whichever of `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock` or `bun.lock` that is; check the registry for deprecated/yanked releases.

## Fix

Bump/pin to a fixed version; regenerate the lock (`uv lock` / equivalent) and re-run tests.

## Review lens

**Dependency attribution** - direct vs transitive attribution is right; a transitive-only finding isn't pinned as if it were direct.
