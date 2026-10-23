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
    note: >-
      The record offers `pydeps` for a visual and says the counts are the
      evidence, so it prescribes no `pydeps` command line for this check and a
      `kind: command` route would have to invent one. `pydeps` reads import
      opcodes from compiled bytecode rather than executing the target, so it
      sees only the modules the import machinery can find, and fetched by a
      one-shot runner, as a tool on a route that is not `in_env` is, that is the
      target's own modules alone, materialized tree or not, so the route needs
      no grant and the counts it supports are between the target's own modules.
      Run on the venv's path instead, it also shows the target's imports of its
      external packages, and starting that interpreter is
      `target-execution`: measured with pydeps 3.0.9 on the seeded uv partition,
      the isolated graph was the same with and without the tree and started no
      interpreter, and the in-venv one added five external edges and started it.
  - lang: typescript
    kind: command
    tool: dependency-cruiser
    argv: [npx, "--package", "typescript@^5", "--package", dependency-cruiser, "--", depcruise, "--config", "${CLAUDE_PLUGIN_ROOT}/.agents/skills/arch-audit/dependency-cruiser.json", "--output-type", json, "--ts-config", "<tsconfig>", "<dir>"]
    argv_by_partition:
      pnpm: [pnpm, "--package=typescript@^5", "--package=dependency-cruiser", dlx, depcruise, "--config", "${CLAUDE_PLUGIN_ROOT}/.agents/skills/arch-audit/dependency-cruiser.json", "--output-type", json, "--ts-config", "<tsconfig>", "<dir>"]
      yarn: [yarn, dlx, "-p", "typescript@^5", "-p", dependency-cruiser, depcruise, "--config", "${CLAUDE_PLUGIN_ROOT}/.agents/skills/arch-audit/dependency-cruiser.json", "--output-type", json, "--ts-config", "<tsconfig>", "<dir>"]
    own_runner: true
    needs: resolved-tree
    note: >-
      The afferent/efferent counts come from the dependency map this builds.
      Each spelling names the packages rather than leaning on the command
      name, and the three differ structurally: the flags precede `dlx` on
      pnpm, since `pnpm dlx --package=` reads the flag as a package spec and
      fails with `ERR_PNPM_SPEC_NOT_SUPPORTED_BY_ANY_RESOLVER`. The
      `typescript` pin is load-bearing: unpinned it resolves to 7.x, outside
      the `>=2.0.0 <7.0.0` this tool declares, and a directory argument then
      cruises `totalCruised: 0` at exit 0, under the shipped config below as
      well - a hub count of nothing rather than an error. The tier is the
      target's own dependencies rather than the tool's: where the partition's
      `tsconfig` extends a base config living in `node_modules`, an
      uninstalled tree loses that `extends` chain and `paths` falls back to
      nothing, so first-party aliased imports stop resolving and the hub
      counts this check rests on go wrong rather than merely thin. On pnpm 11
      the smoke run found the co-package never arrives under `dlx`, so
      installing into an audit-owned directory is what the record prefers
      there; on pnpm 9.15.9 the record's `pnpm` spelling built the graph on
      the seeded fixture.

      Each spelling is complete once its two operands are filled:
      `<tsconfig>` is the partition's own tsconfig, the file carrying the
      compiler options and `paths`, which on a solution-style layout is not a
      `tsconfig.json` holding only `references` - pointed at one, the tool
      resolves no alias, marks every aliased import `couldNotResolve`, and
      exits 0 - and `<dir>` is the directory to cruise, both relative to the
      directory holding `<tsconfig>`, which is where the command runs:
      dependency-cruiser resolves the tsconfig's `include` against its
      working directory rather than the tsconfig's own, so run from a
      workspace root with a member's tsconfig it exits 1 with `TS18003`, no
      inputs found. `--config` names the config this plugin ships for the
      purpose, which carries `enhancedResolveOptions.extensions` and no
      rules, because a target with no `.dependency-cruiser` config of its own
      - the ordinary case - exits 1 with `Can't open a config file` without
      one, and `--ts-config` is dependency-cruiser's documented command-line
      equivalent of `options.tsConfig`, so the per-partition part stays on
      the command line and the file is the same on every target.
      `${CLAUDE_PLUGIN_ROOT}` is the plugin's install directory, the one the
      `audit` skill's emitter path names, and the repository root when the
      skills run from a clone of this repository. `--no-config` is not the
      alternative it looks like: it discards `--ts-config` along with the
      rules, and the tree that resolved its first-party graph under an
      audit-owned config came back with 281 unresolvable first-party
      specifiers and an empty cycle set under it, at exit 0. `--output-type
      json` is not optional either: with no rules loaded the default `err`
      output prints `no dependency violations found` whatever the graph
      holds, so the answer is read from the JSON - each dependency's
      `circular` flag and `cycle`, and each module's `dependencies` and
      `dependents`. The config-less exit 1 and the `--no-config` loss are
      recorded in [the smoke
      run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md),
      and the completed invocation's graph on both seeded partitions in [the
      fixture
      run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-fixture-run.md).
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
      explicitly with `--ts-config`, together with
      `--extensions ts,tsx`, since madge reads only `.js` files by default and
      reports a TypeScript tree as an empty graph without it, on every partition, and give it the file
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
