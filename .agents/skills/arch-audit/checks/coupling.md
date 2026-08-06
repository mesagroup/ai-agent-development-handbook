---
id: arch/coupling
domain: arch
locality: global
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [grimp, pydeps]
  typescript: [dependency-cruiser, madge]
needs:
  resolved-tree: [pydeps, dependency-cruiser]
---

# Coupling & cohesion

Too **coarse**: modules with too many afferent/efferent dependencies (a hub everything imports, or a module that reaches into everything), or modules whose contents don't belong together (grab-bag `utils`).

## Severity

**Important** - a god-module with runaway coupling that blocks safe change.

**Minor** - a grab-bag `utils` that should be split - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - compute afferent/efferent counts per module from the same edge set; flag the top hubs. `pydeps` gives a visual; the counts are the evidence. `pydeps` reads import opcodes from compiled bytecode rather than executing the target, so a dependency the import machinery can't find just drops out of the graph - an uninstalled package thins a hub's count instead of flagging its own absence.

**TypeScript** - compute the same afferent/efferent counts from `dependency-cruiser`'s or `madge`'s dependency map; flag the top hubs. The graph render is a visual; the counts are the evidence. `dependency-cruiser` needs the target's own dependencies present for its own reason: where the `tsconfig` extends a base config living in `node_modules`, an uninstalled tree loses that `extends` chain and `paths` falls back to nothing, so first-party aliased imports stop resolving and the hub counts this check rests on go wrong rather than merely thin. Feed it the compiler through a one-shot runner instead of relying on it being present (`npx -p typescript -p dependency-cruiser`, or the pnpm/yarn `dlx` equivalent) - skip that and it reports zero modules cruised at exit 0, a hub count of nothing rather than an error. `madge` is the read-only option **only where the partition's `tsconfig` does not `extend` a base that lives in `node_modules`**: it excludes installed dependencies and carries its own TypeScript, so it needs no install, but it resolves the `tsconfig` through the TypeScript API like anything else, so the same missing `extends` chain costs it `paths` and it returns a thinned graph at exit 0 rather than an error. **Give `madge` that `tsconfig` explicitly with `--ts-config`, on every partition.** Its `tsConfig` option is documented with a default of `null` and it discovers no config on its own - only a `.madgerc` or a `madge` key in the partition's `package.json` supplies one otherwise - so an invocation without the flag resolves no `paths` at all, and the hub counts come back computed over a graph every aliased import has dropped out of, on a partition whose `tsconfig` extends nothing at all. The `extends` condition above is what remains once the flag is passed, not an alternative to passing it. Read the partition's `tsconfig` for that `extends` before trusting either tool: where it is there, neither has a complete first-party graph without the tree, and the check is `no-evidence (not-permitted)` rather than a hub count. Both claims about `madge` are reasoned from documented behaviour - TypeScript's `extends` resolution and `madge`'s own `tsConfig` default - and neither is reproduced on a fixture here.

## Fix

Split a god-module along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

**Coupling attribution** - direct vs transitive coupling attributed correctly.

**Split-fix cohesion** - a split fix didn't fragment a cohesive unit into ravioli.
