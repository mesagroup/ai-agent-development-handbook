---
id: deps/hygiene
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [deptry]
  typescript: [depcheck, knip]
needs:
  resolved-tree: [deptry, depcheck]
  target-execution: [knip]
---

# Hygiene

Declared-but-unused dependencies, used-but-undeclared (relying on a transitive), duplicate/conflicting pins, dev deps leaking into runtime.

## Severity

**Important** - a used-but-undeclared dependency.

**Minor** - unused declared deps.

## Tooling fallback

**Python** - `deptry` (unused / missing / transitive / misplaced) or an import-vs-declared cross-check. `deptry` reads installed distribution metadata, so it must run inside the project's own environment.

**JavaScript/TypeScript** - `depcheck`, or `knip` where the question extends to unused exports and files. Both are registry packages a one-shot runner can fetch, and this check does not branch on which package manager the partition uses, but neither answers from `package.json` plus the source alone - both need the tree present. `depcheck`'s `bin` special resolves each dependency's *installed* `package.json` to learn its bin names, and `loadModuleData` swallows a resolution failure and returns null metadata, so a dependency used only as a CLI in `scripts` is silently reported unused when `node_modules` is absent - reproduced on a fixture whose scripts were `eslint .` and `tsc -p .`: with no `node_modules`, `depcheck` reported `eslint` and `typescript` as unused devDependencies, and after an install it reported neither. Its `eslint` special likewise `require`s the resolved shareable config and silently returns nothing on failure. `depcheck` sits at `resolved-tree`; `knip` needs more than that, because it loads and executes the target's own tool configuration (its peer deps `typescript` and `@types/node`, plus whatever the config files declare) to see what is actually exported, so it sits at `target-execution`. On a partition whose dependencies are not installed, neither tool answers correctly, and this check is `no-evidence (not-permitted)` rather than a clean result.

## Fix

Replace or remove an unused dependency; update imports; re-test.
