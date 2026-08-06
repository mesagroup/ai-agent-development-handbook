---
id: arch/over-decomposition
domain: arch
locality: global
handbook: []
handbook_note: >-
  The handbook's structural-decay list names hub modules and grab-bag utils -
  coupling that is too coarse - and no equivalent signal for the opposite
  fault, so no clause grounds this check. Mapping it to that clause would be a
  near miss the matrix's own rule forbids: the section would pass a codebase
  that is fragmented rather than tangled.
tooling:
  python: [grimp]
  typescript: [madge, dependency-cruiser]
needs:
  resolved-tree: [dependency-cruiser]
---

# Over-decomposition

Too **fine - over-decomposition** ("ravioli code", the nanoservice anti-pattern): so many trivial single-responsibility units that the dependency graph, not any one component, is the thing you can't hold in your head. The tell is a graph-level shape - a high edge-to-node ratio, many modules carrying one public symbol / a handful of lines, and long call chains threading through pass-through units that only forward (the "poltergeist" / "middle man"). This is distinct from the over-abstraction axis (a *single* abstraction with no second consumer) and from a god-module (too *few* nodes doing too much) - here the fault is the aggregate shape of the whole graph.

## Severity

**Important** - **over-decomposition severe enough that a routine change is shotgun surgery** - one logical edit scatters across many trivial units and the dependency graph is the barrier to understanding.

**Minor** - a handful of over-decomposed pass-through modules that should be merged - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - from the same edge set, compute graph-level shape, not per-module counts. Flag a high **edge-to-node ratio** (many dependencies relative to the number of modules), the distribution of **public-symbols-per-module** and **LOC-per-module** (a long tail of one-symbol / few-line modules), and **call chains that thread through pass-through units** - modules whose functions only forward to another module (the same one-caller detection `arch/over-abstraction` uses: for each single-function module or one-method wrapper class, count call sites with `grimp` refs or a scoped grep, and **one** is the trigger). Record the ratio / the count of trivial nodes / the offending chain as the evidence. A finding needs a **read** confirming the units are genuinely trivial and merging them raises cohesion (files that change together) - a fine-grained split that maps onto real, independently-changing responsibilities is correct design, not a finding.

**TypeScript** - the same graph-level shape from `madge`'s or `dependency-cruiser`'s dependency map: the edge-to-node ratio, the distribution of exports-per-module and LOC-per-module, and the call chains threading through pass-through modules. The same read requirement applies - a fine-grained split that maps onto real, independently-changing responsibilities is correct design, not a finding. `madge` excludes installed dependencies and carries its own TypeScript, so it is the one to reach for first on an unresolved partition - but **only where that partition's `tsconfig` does not `extend` a base that lives in `node_modules`**, since it resolves the `tsconfig` through the TypeScript API like anything else, so the same lost `extends` chain takes `paths` from it and the edge-to-node ratio it returns is computed over a graph the aliased imports dropped out of, at exit 0. **Give `madge` that `tsconfig` explicitly with `--ts-config`, on every partition.** Its `tsConfig` option is documented with a default of `null` and it discovers no config on its own - only a `.madgerc` or a `madge` key in the partition's `package.json` supplies one otherwise - so an invocation without the flag resolves no `paths` at all, and the ratio comes back computed over a graph every aliased import has dropped out of, on a partition whose `tsconfig` extends nothing at all. The `extends` condition above is what remains once the flag is passed, not an alternative to passing it. Read the partition's `tsconfig` for that `extends` before trusting either tool: where it is there, neither has a complete first-party graph without the tree, and the check is `no-evidence (not-permitted)` rather than a graph-shape result. Both claims about `madge` are reasoned from documented behaviour - TypeScript's `extends` resolution and `madge`'s own `tsConfig` default - and neither is reproduced on a fixture here. `dependency-cruiser` needs the target's own dependencies present for its own reason: where the `tsconfig` extends a base config living in `node_modules`, an uninstalled tree loses that `extends` chain and `paths` falls back to nothing, so first-party aliased imports stop resolving and the graph-shape metrics this check rests on - the edge-to-node ratio, the pass-through chains - go wrong rather than merely sparse. Feed it the compiler through a one-shot runner instead of relying on it being present (`npx -p typescript -p dependency-cruiser`, or the pnpm/yarn `dlx` equivalent) - skip that and it reports zero modules cruised at exit 0, an empty graph that looks like a clean, undecomposed project rather than an unanalysed one.

## Fix

Merge over-decomposed units (the inverse): collapse trivial pass-through modules and poltergeists back into the unit they serve, so a responsibility that always changes together lives together and the graph loses the hops that carried no work. Merge along the same cohesion seam a split would follow - combine only units that change together; do not fuse genuinely independent responsibilities just to shrink the node count.

## Review lens

**Merge-fix adequacy** - a merge fix combined only units that actually change together (it didn't fuse independent responsibilities into a new god-module just to shrink the node count).
