---
id: arch/coupling
domain: arch
locality: global
evidence: >-
  The afferent and efferent counts per module are the evidence, whichever
  tool produced the dependency map they were computed over, and the top hubs
  are what a finding flags. A graph render is a visual rather than the
  evidence.
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
    argv_by_partition:
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

      Each spelling above is the prefix the record writes, not a complete
      invocation. A target with no `.dependency-cruiser` config - the
      ordinary case - exits 1 with `Can't open a config file`, so this tool
      answers only once given `--config` with an audit-owned config or
      `--no-config`, and that choice is not free: `--no-config` discards
      `--ts-config` along with the rules, and the tree that resolved its
      first-party graph under an audit-owned config came back with 281
      unresolvable first-party specifiers and an empty cycle set under it,
      at exit 0. Prefer an audit-owned config setting `options.tsConfig` and
      `enhancedResolveOptions.extensions`. The output observed behind the
      config-less exit 1 and the `--no-config` loss is recorded in [the
      smoke
      run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md).
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
      carries are unresolvable without the tree, so this route has no
      complete first-party graph. What that leaves is the sibling
      `dependency-cruiser` route, which carries `resolved-tree` and does
      have the tree under that grant; only where the grant is withheld too
      does the record reach `no-evidence (not-permitted)` rather than a hub
      count.
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

## Fix

Split a god-module along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

**Coupling attribution** - direct vs transitive coupling attributed correctly.

**Split-fix cohesion** - a split fix didn't fragment a cohesive unit into ravioli.
