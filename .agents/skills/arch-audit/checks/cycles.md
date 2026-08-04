---
id: arch/cycles
domain: arch
locality: global
handbook:
  - codebase-structure/order-the-tiers-by-reuse
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [import-linter, pydeps, grimp]
  typescript: [madge, dependency-cruiser]
---

# Cycles

Import cycles between modules or packages (they defeat isolation and make the graph un-orderable).

## Severity

**Critical** - an import cycle across package boundaries. These break the architecture the team committed to.

**Important** - a cycle within a package.

## Tooling fallback

**Python** - `import-linter`'s cycle contract, `pydeps --show-cycles`, or `grimp`'s cycle detection on the built graph.

**TypeScript** - `madge --circular`, or `dependency-cruiser`'s `no-circular` rule on the built graph.

**With none of them installed** - the edge set built for layering is all a cycle needs: walk it depth-first and record every back edge, or collapse it into strongly-connected components and report each component of size greater than one. Report the participating modules in cycle order, so the fix has a seam to cut.

## Fix

Break a cycle: extract the shared piece into a new lower module, or convert an import-time dependency into a lazy/local import only when extraction genuinely doesn't fit (note the trade-off).

## Review lens

**Cycle-fix adequacy** - a cycle "fix" doesn't just relocate the cycle.
