---
id: arch/coupling
domain: arch
locality: global
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [grimp, pydeps]
  typescript: [dependency-cruiser, madge]
---

# Coupling & cohesion

Wrong granularity in *either* direction. Too **coarse**: modules with too many afferent/efferent dependencies (a hub everything imports, or a module that reaches into everything), or modules whose contents don't belong together (grab-bag `utils`).

## Severity

**Important** - a god-module with runaway coupling that blocks safe change.

**Minor** - a grab-bag `utils` that should be split - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - compute afferent/efferent counts per module from the same edge set; flag the top hubs. `pydeps` gives a visual; the counts are the evidence.

**TypeScript** - compute the same afferent/efferent counts from `dependency-cruiser`'s or `madge`'s dependency map; flag the top hubs. The graph render is a visual; the counts are the evidence.

## Fix

Split a god-module along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

Direct vs transitive coupling attributed correctly; a cycle "fix" doesn't just relocate the cycle.

A merge fix combined only units that actually change together (it didn't fuse independent responsibilities into a new god-module just to shrink the node count).
