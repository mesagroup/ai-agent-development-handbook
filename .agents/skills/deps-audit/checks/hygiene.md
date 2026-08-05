---
id: deps/hygiene
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [deptry]
  typescript: [depcheck, knip]
---

# Hygiene

Declared-but-unused dependencies, used-but-undeclared (relying on a transitive), duplicate/conflicting pins, dev deps leaking into runtime.

## Severity

**Important** - a used-but-undeclared dependency.

**Minor** - unused declared deps.

## Tooling fallback

**Python** - `deptry` (unused / missing / transitive / misplaced) or an import-vs-declared cross-check.

**JavaScript/TypeScript** - `depcheck`, or `knip` where the question extends to unused exports and files. Both are registry packages a one-shot runner can fetch, and both answer from `package.json` plus the source rather than from a lockfile, so this check does not branch on which package manager the partition uses. They differ in what they need present: `depcheck` runs against the source alone, while `knip` takes `typescript` and `@types/node` as peer dependencies and its own docs say that under `npx` or `dlx` both are expected to be installed already. So on a partition whose dependencies are not installed, `depcheck` is the one that answers, and a `knip` failure there is a missing precondition rather than a finding about the target.

## Fix

Replace or remove an unused dependency; update imports; re-test.
