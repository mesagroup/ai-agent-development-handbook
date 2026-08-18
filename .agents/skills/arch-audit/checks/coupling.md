---
id: arch/coupling
domain: arch
locality: global
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
routes:
  - lang: python
    kind: library
    tool: grimp
    note: >-
      The afferent/efferent counts per module come from a scripted pass over
      the edge set rather than through a command; the record asks for the
      counts to be computed, and the top hubs flagged, from the same edge set
      the other structural checks build.
  - lang: python
    kind: procedure
    tool: pydeps
    needs: resolved-tree
    note: >-
      The record offers `pydeps` for a visual and says the counts are the
      evidence, so it prescribes no `pydeps` command line for this check and a
      `kind: command` route would have to invent one. The tier is the target's
      own dependencies: `pydeps` reads import opcodes from compiled bytecode
      rather than executing the target, so a dependency the import machinery
      cannot find just drops out of the graph, and an uninstalled package
      thins a hub's count instead of flagging its own absence.
  - lang: typescript
    kind: command
    tool: dependency-cruiser
    argv: [npx, "--package", "typescript@^5", "--package", dependency-cruiser, "--", depcruise]
    argv_by_manager:
      pnpm: [pnpm, "--package=typescript@^5", "--package=dependency-cruiser", dlx, depcruise]
      yarn: [yarn, dlx, "-p", "typescript@^5", "-p", dependency-cruiser, depcruise]
    needs: resolved-tree
    note: >-
      The afferent/efferent counts come from the dependency map this builds.
      Each spelling names the packages rather than leaning on the command
      name, and the three differ structurally: the flags precede `dlx` on
      pnpm, since `pnpm dlx --package=` reads the flag as a package spec and
      fails with `ERR_PNPM_SPEC_NOT_SUPPORTED_BY_ANY_RESOLVER`. The
      `typescript` pin is load-bearing: unpinned it resolves to 7.x, outside
      the `>=2.0.0 <7.0.0` this tool declares, and a directory argument then
      cruises `totalCruised: 0` at exit 0 - a hub count of nothing rather than
      an error. The tier is the target's own dependencies rather than the
      tool's: where the partition's `tsconfig` extends a base config living in
      `node_modules`, an uninstalled tree loses that `extends` chain and
      `paths` falls back to nothing, so first-party aliased imports stop
      resolving and the hub counts this check rests on go wrong rather than
      merely thin. On pnpm the co-package is less dependable still, and
      installing into an audit-owned directory is what the record prefers
      there.
    alone_insufficient: >-
      Each spelling above is the prefix the record writes, not a complete
      invocation. A target with no `.dependency-cruiser` config - the ordinary
      case - exits 1 with `Can't open a config file`, so this tool answers
      only once given `--config` with an audit-owned config or `--no-config`,
      and that choice is not free: `--no-config` discards `--ts-config` along
      with the rules, and the tree that resolved its first-party graph under
      an audit-owned config came back with 281 unresolvable first-party
      specifiers and an empty cycle set under it, at exit 0. Prefer an
      audit-owned config setting `options.tsConfig` and
      `enhancedResolveOptions.extensions`.
  - lang: typescript
    kind: command
    tool: depcruise
    argv: [dlx, depcruise]
    disposition: forbidden
    note: >-
      `depcruise` is the command dependency-cruiser documents but not the name
      of the package that provides it, and npm carries an unrelated package
      under that name - a dependency-confusion placeholder whose bin prints a
      misconfiguration notice and exits 0 - so a bare `dlx depcruise` comes
      back with nothing at exit 0, by a different route than a dropped
      co-package, and neither route looks like a tool that failed. The name is
      the tool this form actually fetches, which is not dependency-cruiser
      under another package name.
  - lang: typescript
    kind: procedure
    tool: madge
    applies_when: >-
      The partition's `tsconfig` does not `extend` a base that lives in
      `node_modules`. Where it does, the `extends` chain and the `paths` it
      carries are unresolvable without the tree, so neither TypeScript route
      here has a complete first-party graph and the check is
      `no-evidence (not-permitted)` rather than a hub count.
    note: >-
      The counts come from madge's dependency map. The record names the tool
      and the flag to pass it - give madge the partition's own `tsconfig`
      explicitly with `--ts-config`, on every partition, and give it the file
      that carries `paths`, which on a solution-style layout is not
      `tsconfig.json` - and prescribes no command line, so there is no argv to
      declare and a `kind: command` route would have to invent one. madge
      excludes installed dependencies and carries its own TypeScript, so it
      needs no install and is the read-only option, but its `tsConfig` option
      is documented with a default of `null` and it discovers no config on its
      own - only a `.madgerc` or a `madge` key in the partition's
      `package.json` supplies one otherwise - so an invocation without the
      flag resolves no `paths` at all and the hub counts come back computed
      over a graph every aliased import has dropped out of. A Vite or React
      project commonly ships a `tsconfig.json` holding only `files` and
      `references` with the compiler options in `tsconfig.app.json` beside it,
      and madge does not follow `references`, so pointing at `tsconfig.json`
      there is byte-for-byte the same as passing no flag at all. That operand
      is per partition and the record can name no single value for it.
---

# Coupling & cohesion

Too **coarse**: modules with too many afferent/efferent dependencies (a hub everything imports, or a module that reaches into everything), or modules whose contents don't belong together (grab-bag `utils`).

## Severity

**Important** - a god-module with runaway coupling that blocks safe change.

**Minor** - a grab-bag `utils` that should be split - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - compute afferent/efferent counts per module from the same edge set; flag the top hubs. `pydeps` gives a visual; the counts are the evidence. `pydeps` reads import opcodes from compiled bytecode rather than executing the target, so a dependency the import machinery can't find just drops out of the graph - an uninstalled package thins a hub's count instead of flagging its own absence.

**TypeScript** - compute the same afferent/efferent counts from `dependency-cruiser`'s or `madge`'s dependency map; flag the top hubs. The graph render is a visual; the counts are the evidence. `dependency-cruiser` needs the target's own dependencies present for its own reason: where the `tsconfig` extends a base config living in `node_modules`, an uninstalled tree loses that `extends` chain and `paths` falls back to nothing, so first-party aliased imports stop resolving and the hub counts this check rests on go wrong rather than merely thin. Feed it the compiler through a one-shot runner instead of relying on it being present, and **pin it below the major this tool rejects** (`npx --package 'typescript@^5' --package dependency-cruiser -- depcruise`, `pnpm --package=typescript@^5 --package=dependency-cruiser dlx depcruise` - **note the flags precede `dlx` on pnpm**, since `pnpm dlx --package=...` reads the flag as a package spec and fails with `ERR_PNPM_SPEC_NOT_SUPPORTED_BY_ANY_RESOLVER` - or `yarn dlx -p typescript@^5 -p dependency-cruiser depcruise`) - skip that and it reports zero modules cruised at exit 0, a hub count of nothing rather than an error. All three name the packages rather than leaning on the command name, and none of the three may be left to the reader to reconstruct: `depcruise` is the command this tool documents but not the name of the package that provides it, and npm carries an unrelated package under that name - a dependency-confusion placeholder whose bin prints a misconfiguration notice and exits 0 - so a bare `dlx depcruise` also comes back with nothing at exit 0, by a different route than a dropped co-package, and neither route looks like a tool that failed. Run against a real npm target at dependency-cruiser 18.2.0, three further routes each returned an unusable answer, and the version pin above is the first of them: an unpinned `typescript` co-package resolves to 7.x, outside the `>=2.0.0 <7.0.0` this tool declares, so `depcruise --info` reports no TypeScript transpiler and enables only `.js .cjs .mjs .jsx` - whereupon a **directory** argument cruises `totalCruised: 0` at exit 0, and the same invocation with the pin cruises the tree. Second, a target with no `.dependency-cruiser` config - the ordinary case, not the exotic one - **exits 1** with `Can't open a config file`, so this tool answers only once given `--config` with an audit-owned config or `--no-config`, and that choice is not free. Third, `--no-config` is what depcruise's own error message suggests and it **discards `--ts-config` along with the rules**: the tree that resolved its first-party graph under an audit-owned config came back with 281 unresolvable first-party specifiers and an empty cycle set under `--no-config`, at exit 0. So prefer an audit-owned config setting `options.tsConfig` and `enhancedResolveOptions.extensions`, and read [the smoke run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md) for the observed output behind each of the three. On pnpm the co-package is less dependable still, and its two failures point opposite ways: on pnpm 9.15.9 the ordering above supplies the compiler and `pnpm dlx --package=` errors outright, while on pnpm 11 `depcruise --info` reported no TypeScript under *either* ordering - so the tool ran and the compiler never arrived, with nothing on stderr to say so. Where the partition is pnpm, install into an audit-owned directory rather than trusting the runner to carry a second package. `madge` is the read-only option **only where the partition's `tsconfig` does not `extend` a base that lives in `node_modules`**: it excludes installed dependencies and carries its own TypeScript, so it needs no install, but it resolves the `tsconfig` through the TypeScript API like anything else, so the same missing `extends` chain costs it `paths` and it returns a thinned graph at exit 0 rather than an error. **Give `madge` that `tsconfig` explicitly with `--ts-config`, on every partition - and give it the file that carries `paths`, which on a solution-style layout is not `tsconfig.json`.** A Vite or React project commonly ships `tsconfig.json` holding only `{"files": [], "references": [...]}` with the compiler options in `tsconfig.app.json` beside it; madge does not follow `references`, so pointing at `tsconfig.json` there is byte-for-byte the same as passing no flag at all. Measured on one such partition: 45 warnings and 6 cycles with `tsconfig.json` or with no flag, 31 warnings and 7 cycles with `tsconfig.app.json`. The instruction is followed, and the cycle it exists to expose stays hidden. Its `tsConfig` option is documented with a default of `null` and it discovers no config on its own - only a `.madgerc` or a `madge` key in the partition's `package.json` supplies one otherwise - so an invocation without the flag resolves no `paths` at all, and the hub counts come back computed over a graph every aliased import has dropped out of, on a partition whose `tsconfig` extends nothing at all. The `extends` condition above is what remains once the flag is passed, not an alternative to passing it. Read the partition's `tsconfig` for that `extends` before trusting either tool: where it is there, neither has a complete first-party graph without the tree, and the check is `no-evidence (not-permitted)` rather than a hub count. The `extends` claim about `madge` is reasoned from documented behaviour - TypeScript's `extends` resolution - and is not reproduced on a fixture here. The `--ts-config` claim no longer rests on reasoning: run against a real npm target whose `tsconfig` extends nothing, `madge --circular` without the flag reported `✔ No circular dependency found!` at exit 0 where the same command with it found two, and the dependency map went from 1090 edges to 122, reordering the hubs rather than thinning them - so the flag is what stands between this tool and a false clean, on a partition the `extends` condition never applied to.

## Fix

Split a god-module along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

**Coupling attribution** - direct vs transitive coupling attributed correctly.

**Split-fix cohesion** - a split fix didn't fragment a cohesive unit into ravioli.
