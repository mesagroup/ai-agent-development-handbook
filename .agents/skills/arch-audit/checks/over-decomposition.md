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

**TypeScript** - the same graph-level shape from `madge`'s or `dependency-cruiser`'s dependency map: the edge-to-node ratio, the distribution of exports-per-module and LOC-per-module, and the call chains threading through pass-through modules. The same read requirement applies - a fine-grained split that maps onto real, independently-changing responsibilities is correct design, not a finding. `madge` excludes installed dependencies and carries its own TypeScript, so it is the one to reach for first on an unresolved partition; `dependency-cruiser` needs a resolvable compiler just to build the map, and without one it reports zero modules cruised at exit 0 - an empty graph that looks like a clean, undecomposed project rather than an unanalysed one.

## Fix

Merge over-decomposed units (the inverse): collapse trivial pass-through modules and poltergeists back into the unit they serve, so a responsibility that always changes together lives together and the graph loses the hops that carried no work. Merge along the same cohesion seam a split would follow - combine only units that change together; do not fuse genuinely independent responsibilities just to shrink the node count.

## Review lens

**Merge-fix adequacy** - a merge fix combined only units that actually change together (it didn't fuse independent responsibilities into a new god-module just to shrink the node count).
