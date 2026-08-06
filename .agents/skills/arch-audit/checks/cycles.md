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
needs:
  resolved-tree: [pydeps, dependency-cruiser]
---

# Cycles

Import cycles between modules or packages (they defeat isolation and make the graph un-orderable).

## Severity

**Critical** - an import cycle across package boundaries. These break the architecture the team committed to.

**Important** - a cycle within a package.

## Tooling fallback

**Python** - `import-linter`'s cycle contract, `pydeps --show-cycles`, or `grimp`'s cycle detection on the built graph. `pydeps` doesn't execute the target - it reads import opcodes from compiled bytecode - but it only sees modules the import machinery can find, so an uninstalled dependency drops out of the graph and a cycle running through it goes silently unreported rather than erroring.

**TypeScript** - `madge --circular`, or `dependency-cruiser`'s `no-circular` rule on the built graph. `madge` excludes installed dependencies and brings its own TypeScript, so it needs no install and is the one to reach for first on an unresolved partition. `dependency-cruiser` needs the target's own dependencies present for its own reason: where the `tsconfig` extends a base config living in `node_modules`, an uninstalled tree loses that `extends` chain and `paths` falls back to nothing, so a first-party aliased import stops resolving and a cycle running through it goes undetected rather than merely unreported. Feed it the compiler through a one-shot runner instead of relying on it being present (`npx -p typescript -p dependency-cruiser`, or the pnpm/yarn `dlx` equivalent) - skip that and it reports zero modules cruised at exit 0, which reads as a clean cycle-free project rather than as nothing having been analysed.

**With none of them installed** - the edge set built for layering is all a cycle needs: walk it depth-first and record every back edge, or collapse it into strongly-connected components and report each component of size greater than one. Report the participating modules in cycle order, so the fix has a seam to cut.

## Fix

Break a cycle: extract the shared piece into a new lower module, or convert an import-time dependency into a lazy/local import only when extraction genuinely doesn't fit (note the trade-off).

## Review lens

**Cycle-fix adequacy** - a cycle "fix" doesn't just relocate the cycle.
