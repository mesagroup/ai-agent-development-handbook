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

**TypeScript** - compute the same afferent/efferent counts from `dependency-cruiser`'s or `madge`'s dependency map; flag the top hubs. The graph render is a visual; the counts are the evidence. `dependency-cruiser` needs its own TypeScript compiler resolvable beside it just to produce a map at all - without it, it reports zero modules cruised at exit 0, a hub count of nothing rather than an error; `madge` needs no install, since it excludes installed dependencies and carries its own TypeScript, so reach for it first on an unresolved partition.

## Fix

Split a god-module along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

**Coupling attribution** - direct vs transitive coupling attributed correctly.

**Split-fix cohesion** - a split fix didn't fragment a cohesive unit into ravioli.
