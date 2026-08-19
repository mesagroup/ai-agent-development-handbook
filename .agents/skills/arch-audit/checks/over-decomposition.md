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
routes:
  - lang: python
    kind: library
    tool: grimp
    note: >-
      Graph-level shape - the edge-to-node ratio, the distribution of
      public-symbols-per-module and LOC-per-module, and call chains
      threading through pass-through units - is computed from the same
      edge set built for layering, rather than by a command run for this
      check specifically. A pass-through unit is a module whose functions
      only forward, and the same one-caller count `arch/over-abstraction`
      takes finds it: call sites per single-function module or one-method
      wrapper class, from `grimp` refs or a scoped grep, where one is the
      trigger.
    alone_insufficient: >-
      "A finding needs a read confirming the units are genuinely trivial
      and merging them raises cohesion (files that change together) - a
      fine-grained split that maps onto real, independently-changing
      responsibilities is correct design, not a finding."
  - lang: typescript
    kind: procedure
    tool: madge
    applies_when: >-
      The partition's `tsconfig` does not `extend` a base that lives in
      `node_modules`. Where it does, the `extends` chain and the `paths`
      it carries are unresolvable without the tree, so this route has no
      complete first-party graph. What remains is the sibling
      `dependency-cruiser` route, which carries `resolved-tree` and does have
      the tree under that grant; the record reaches
      `no-evidence (not-permitted)` rather than a graph-shape result only
      once that grant is withheld too.
    note: >-
      The record prescribes no graph-shape command for `madge`; it names
      the tool as the one to reach for first on a partition where the tree
      isn't resolved, since it excludes installed dependencies and carries
      its own TypeScript, and has the reader give it the partition's own
      `tsconfig` explicitly with `--ts-config` - the file that carries
      `paths`, which on a solution-style layout is not `tsconfig.json` -
      before reading the edge-to-node ratio and pass-through chains from
      the dependency map it builds. Passing no flag, or the wrong
      `tsconfig` file, resolves no `paths` at all and the ratio comes back
      computed over a graph every aliased import has dropped out of. Its
      `tsConfig` option is documented with a default of `null` and it
      discovers no config on its own - only a `.madgerc` or a `madge` key
      in the partition's `package.json` supplies one otherwise.
    alone_insufficient: >-
      "The same read requirement applies" as the Python pass - "a
      fine-grained split that maps onto real, independently-changing
      responsibilities is correct design, not a finding."
  - lang: typescript
    kind: command
    tool: dependency-cruiser
    argv: [npx, "--package", "typescript@^5", "--package", dependency-cruiser, "--", depcruise]
    argv_by_manager:
      pnpm: [pnpm, "--package=typescript@^5", "--package=dependency-cruiser", dlx, depcruise]
      yarn: [yarn, dlx, "-p", "typescript@^5", "-p", dependency-cruiser, depcruise]
    needs: resolved-tree
    note: >-
      Needs the target's own dependencies present for the reason the
      record gives: where the `tsconfig` extends a base config living in
      `node_modules`, an uninstalled tree loses that `extends` chain and
      `paths` falls back to nothing, so first-party aliased imports stop
      resolving and the graph-shape metrics this check rests on - the
      edge-to-node ratio, the pass-through chains - go wrong rather than
      merely sparse. Each spelling names the packages rather than leaning
      on the command name, and the three differ structurally: the flags
      precede `dlx` on pnpm, since `pnpm dlx --package=` reads the flag as
      a package spec and fails with
      `ERR_PNPM_SPEC_NOT_SUPPORTED_BY_ANY_RESOLVER`. The `typescript` pin
      is load-bearing: unpinned it resolves to 7.x, outside the
      `>=2.0.0 <7.0.0` this tool declares, and a directory argument then
      cruises `totalCruised: 0` at exit 0. On pnpm the co-package is less
      dependable still, and installing into an audit-owned directory is
      what the record prefers there.
    alone_insufficient: >-
      Each spelling above is the prefix the record writes, not a complete
      invocation. A target with no `.dependency-cruiser` config - the
      record calls this the ordinary case, not the exotic one - exits 1
      with `Can't open a config file`, so this tool answers only once
      given `--config` with an audit-owned config or `--no-config`, and
      that choice is not free: `--no-config` discards `--ts-config` along
      with the rules, and the tree that resolved its first-party graph
      under an audit-owned config came back with 281 unresolvable
      first-party specifiers and an empty cycle set under it, at exit 0.
      Prefer an audit-owned config setting `options.tsConfig` and
      `enhancedResolveOptions.extensions`. The output observed behind the
      config-less exit 1 and the `--no-config` loss is recorded in [the smoke
      run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md).
      Once the graph is complete, "the same read requirement applies" as the
      Python pass - "a fine-grained split that maps onto real,
      independently-changing responsibilities is correct design, not a
      finding."
  - lang: typescript
    kind: command
    tool: depcruise
    argv: [dlx, depcruise]
    disposition: forbidden
    note: >-
      `depcruise` is the command dependency-cruiser documents but not the
      name of the package that provides it, and npm carries an unrelated
      package under that name - a dependency-confusion placeholder whose
      bin prints a misconfiguration notice and exits 0 - so a bare
      `dlx depcruise` comes back with nothing at exit 0, an empty graph
      that looks like a clean, undecomposed project rather than an
      unanalysed one.
---

# Over-decomposition

Too **fine - over-decomposition** ("ravioli code", the nanoservice anti-pattern): so many trivial single-responsibility units that the dependency graph, not any one component, is the thing you can't hold in your head. The tell is a graph-level shape - a high edge-to-node ratio, many modules carrying one public symbol / a handful of lines, and long call chains threading through pass-through units that only forward (the "poltergeist" / "middle man"). This is distinct from the over-abstraction axis (a *single* abstraction with no second consumer) and from a god-module (too *few* nodes doing too much) - here the fault is the aggregate shape of the whole graph.

## Severity

**Important** - **over-decomposition severe enough that a routine change is shotgun surgery** - one logical edit scatters across many trivial units and the dependency graph is the barrier to understanding.

**Minor** - a handful of over-decomposed pass-through modules that should be merged - real but low-cost, fix when touching the area.

## Fix

Merge over-decomposed units (the inverse): collapse trivial pass-through modules and poltergeists back into the unit they serve, so a responsibility that always changes together lives together and the graph loses the hops that carried no work. Merge along the same cohesion seam a split would follow - combine only units that change together; do not fuse genuinely independent responsibilities just to shrink the node count.

## Review lens

**Merge-fix adequacy** - a merge fix combined only units that actually change together (it didn't fuse independent responsibilities into a new god-module just to shrink the node count).
