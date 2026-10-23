---
id: arch/cycles
domain: arch
locality: global
handbook:
  - codebase-structure/order-the-tiers-by-reuse
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a
  - codebase-structure/watch-for-structural-decay-beyond-layering
routes:
  - lang: python
    kind: procedure
    tool: import-linter
    applies_when: >-
      The partition carries a `.importlinter` cycle contract. The contract is
      the input, so writing one to make the tool run would manufacture the
      configuration whose absence is what the run is meant to observe.
    note: >-
      The record names the tool and its cycle contract and prescribes no
      command line for it, so there is no argv to declare and a `kind: command`
      route would have to invent one. What the record gives is the instruction:
      read the contract the partition carries, and check the cycle clause in it.
  - lang: python
    kind: command
    tool: pydeps
    argv: [pydeps, "--show-cycles", "--show-dot"]
    note: >-
      `--show-dot` prints the underlying dot source as text, so a genuine cycle
      shows up as both directed edges of the pair (`a -> b` and `b -> a`) on
      stdout. The tool reads import opcodes from compiled bytecode rather than
      executing the target, so it sees only the modules the import machinery can
      find, and run as this route runs - isolated, through a one-shot runner,
      since it is not `in_env` - that is the target's own modules alone: no
      external package ever appears in the graph, whether or not the tree is
      materialized, which is why the route needs no grant. A cycle runs through
      the target's own modules, so that is the graph this check reads. Measured
      with pydeps 3.0.9 on the seeded uv partition: the isolated run printed the
      same graph with the tree materialized and without it, and never started the
      partition's interpreter, which a `.pth` marker planted in its venv showed;
      run on the venv's path instead, it added the edges from the external
      packages and started that interpreter, which is `target-execution`. The
      package to graph is an operand the record names none for. The dot lines this prints over a
      seeded two-module cycle, and the zero bytes the bare form returns on both
      streams over the same tree, are recorded in [the python lens smoke
      run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/python-lens-smoke-run.md).
  - lang: python
    kind: command
    tool: pydeps
    argv: [pydeps, "--show-cycles"]
    disposition: superseded
    note: >-
      Superseded by the route above, which narrows the same command:
      `--show-cycles` alone has no textual output channel at all. It exits 0
      with empty stdout and empty stderr whether a cycle is present or absent,
      because its answer is drawn onto an SVG side-file rather than printed, and
      those two states are indistinguishable to a caller reading the streams.
  - lang: python
    kind: library
    tool: grimp
    note: >-
      Cycle detection runs over a graph a scripted pass builds, rather than
      through a command.
  - lang: typescript
    kind: command
    tool: madge
    argv: [madge, "--circular", "--extensions", "ts,tsx", "--ts-config"]
    applies_when: >-
      The partition's `tsconfig` does not `extend` a base that lives in
      `node_modules`. Where it does, the `extends` chain and the `paths` it
      carries are unresolvable without the tree, so this route has no complete
      first-party graph. What remains is the sibling `dependency-cruiser`
      route, which carries `resolved-tree` and does have the tree under that
      grant, and failing that the tool-less route below, which needs nothing
      installed and answers whatever the partition's language. The record
      reaches `no-evidence (not-permitted)` only once neither of those is
      available either, rather than on this condition alone.
    note: >-
      `--ts-config` takes the partition's own `tsconfig`, and it has to be the
      file that carries `paths`, which on a solution-style layout is not
      `tsconfig.json`: a Vite or React project commonly ships a `tsconfig.json`
      holding only `files` and `references` with the compiler options in
      `tsconfig.app.json` beside it, and madge does not follow `references`.
      That operand is per partition and the record can name no single value for
      it. madge excludes installed dependencies and brings its own TypeScript,
      so it needs no install and is the one to reach for first on an unresolved
      partition. `--extensions ts,tsx` is not optional: given a directory,
      madge collects only the extensions in its `fileExtensions` option, whose
      default in its own source is `['js']`, so on a TypeScript-only tree it
      prints `Processed 0 files` and `No circular dependency found!` at exit 0
      whatever the imports are. Measured on the seeded npm fixture: without
      the flag 0 files and no cycle, with `--extensions ts` 3 files and the
      planted two-module cycle. A partition whose own modules are `.js`,
      `.mts` or `.cts` as well adds those to the list.
  - lang: typescript
    kind: command
    tool: madge
    argv: [madge, "--circular", "--extensions", "ts,tsx"]
    disposition: superseded
    note: >-
      Superseded by the route above, which narrows the same command. madge
      discovers no `tsconfig` on its own - its `tsConfig` option is documented
      with a default of `null`, and only a `.madgerc` or a `madge` key in the
      partition's `package.json` supplies one otherwise - so this form resolves
      no `paths` at all and reports no cycles at exit 0 over a graph every
      aliased import has dropped out of. Measured against a real npm target
      whose `tsconfig` extends nothing: the command without `--ts-config`
      reported `No circular dependency found!` at exit 0 where the same
      command with it found two, and the dependency map went from 1090 edges
      to 122. It carries `--extensions ts,tsx` for the reason the route above
      gives, so that the one thing it lacks is the `tsconfig`.
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
      Every dependency the built graph marks `circular`, its `cycle` naming
      the participating modules in order. Each spelling names the packages
      rather than leaning on the command name, and the three differ
      structurally: the flags precede `dlx` on pnpm, since `pnpm dlx
      --package=` reads the flag as a package spec and fails with
      `ERR_PNPM_SPEC_NOT_SUPPORTED_BY_ANY_RESOLVER`. The `typescript` pin is
      load-bearing: unpinned it resolves to 7.x, outside the `>=2.0.0 <7.0.0`
      this tool declares, and a directory argument then cruises
      `totalCruised: 0` at exit 0, under the shipped config below as well.
      The tier is the target's own dependencies rather than the tool's: where
      the partition's `tsconfig` extends a base config living in
      `node_modules`, an uninstalled tree loses that `extends` chain and
      `paths` falls back to nothing, so a first-party aliased import stops
      resolving and a cycle running through it goes undetected. On pnpm 11
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
      misconfiguration notice and exits 0 - so a bare `dlx depcruise` comes back
      with nothing at exit 0, which reads as a clean cycle-free project rather
      than as nothing having been analysed. The name is the tool this form
      actually fetches, which is not dependency-cruiser under another package
      name.
  - lang: any
    kind: procedure
    note: >-
      With none of the tools installed, the edge set built for layering is all a
      cycle needs: walk it depth-first and record every back edge, or collapse
      it into strongly-connected components and report each component of size
      greater than one. Report the participating modules in cycle order, so the
      fix has a seam to cut.
---

# Cycles

Import cycles between modules or packages (they defeat isolation and make the graph un-orderable).

## Severity

**Critical** - an import cycle across package boundaries. These break the architecture the team committed to.

**Important** - a cycle within a package.

## Fix

Break a cycle: extract the shared piece into a new lower module, or convert an import-time dependency into a lazy/local import only when extraction genuinely doesn't fit (note the trade-off).

## Review lens

**Cycle-fix adequacy** - a cycle "fix" doesn't just relocate the cycle.
