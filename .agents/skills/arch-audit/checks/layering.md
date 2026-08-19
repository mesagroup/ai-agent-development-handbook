---
id: arch/layering
domain: arch
locality: local
handbook:
  - codebase-structure/order-the-tiers-by-reuse
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a
  - codebase-structure/watch-for-structural-decay-beyond-layering
  - codebase-structure/compose-agents-with-typed-hooks-over-a-generic-runner-b
  - codebase-structure/dispatch-on-a-discriminator-not-a-type
  - three-layer-model/hold-the-contracts-that-make-layering-pay-off-a
routes:
  - lang: python
    kind: procedure
    tool: import-linter
    applies_when: >-
      The partition carries a `.importlinter` contract.
    note: >-
      The record names the tool and its contract and prescribes no command
      line for it, so there is no argv to declare and a `kind: command`
      route would have to invent one.
  - lang: python
    kind: procedure
    tool: tach
    applies_when: >-
      The partition carries no `.importlinter` contract for the route above
      to apply. The record offers `tach` as the alternative and names no
      command for it either.
    note: >-
      Where neither tool's condition holds, the record has the reader build
      the ground-truth edge set by hand instead: parse each module's
      `import` / `from ... import` statements and check every cross-tier
      edge against the declared rules.
  - lang: python
    kind: library
    tool: grimp
    note: >-
      Builds the edge set the record's manual fallback asks to be walked -
      "parse each module's import statements ... (`grimp`, or an
      AST/`ast`-based walk, or a scoped grep)" - so this is a graph a
      scripted pass builds rather than a command grimp itself runs. Record
      the offending `file:line` for each violation.
  - lang: python
    kind: procedure
    note: >-
      Where neither tool answers, the record has the reader build the
      ground-truth edge set by hand instead: parse each module's `import` /
      `from ... import` statements (an AST/`ast`-based walk, or a scoped
      grep) and check every cross-tier edge against the declared rules,
      flagging the file and line of each one. Needs nothing installed,
      unlike `import-linter`, `tach` and `grimp` above.
  - lang: typescript
    kind: command
    tool: dependency-cruiser
    applies_when: >-
      The project has its own `.dependency-cruiser` config. Absent one, the
      record has the reader fall back to reading the `tsconfig` path
      aliases and project references as the declared boundaries instead of
      reaching for this tool.
    argv: [npx, "--package", "typescript@^5", "--package", dependency-cruiser, "--", depcruise]
    argv_by_manager:
      pnpm: [pnpm, "--package=typescript@^5", "--package=dependency-cruiser", dlx, depcruise]
      yarn: [yarn, dlx, "-p", "typescript@^5", "-p", dependency-cruiser, depcruise]
    needs: resolved-tree
    note: >-
      Needs the target's own dependencies present for two reasons the
      record gives: an uninstalled tree returns every external import as
      `couldNotResolve: true` with dependency type `unknown`, so a
      project's own config that forbids by dependency type
      (`not-to-dev-dep`, `not-to-unresolvable`, `no-non-package-json`)
      silently stops enforcing those rules while still reporting green;
      and where the `tsconfig` extends a base config living in
      `node_modules`, an uninstalled tree loses that `extends` chain,
      `paths` falls back to nothing, and the path aliases the fallback
      above reads as the declared boundaries disappear along with it, so a
      first-party cross-boundary edge routed through an alias goes unseen
      rather than merely unchecked. Each spelling names the packages rather
      than leaning on the command name, and the three differ structurally:
      the flags precede `dlx` on pnpm, since `pnpm dlx --package=` reads
      the flag as a package spec and fails with
      `ERR_PNPM_SPEC_NOT_SUPPORTED_BY_ANY_RESOLVER`. The `typescript` pin
      is load-bearing: unpinned it resolves to 7.x, outside the
      `>=2.0.0 <7.0.0` this tool declares, and a directory argument then
      cruises `totalCruised: 0` at exit 0.
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
      `enhancedResolveOptions.extensions`.
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
      `dlx depcruise` comes back with nothing at exit 0, which reads as
      zero violations rather than as nothing having been checked.
  - lang: typescript
    kind: procedure
    tool: madge
    applies_when: >-
      The partition's `tsconfig` does not `extend` a base that lives in
      `node_modules`. Where it does, the `extends` chain and the `paths`
      it carries are unresolvable without the tree, so neither TypeScript
      route here has a complete first-party graph and the check is
      `no-evidence (not-permitted)` rather than a clean conformance
      result.
    note: >-
      The record prescribes no boundary-checking command for `madge`; it
      names the tool as the one to reach for first on a partition where
      the tree isn't resolved, since it excludes installed dependencies
      and carries its own TypeScript, and has the reader give it the
      partition's own `tsconfig` explicitly with `--ts-config` - the file
      that carries `paths`, which on a solution-style layout is not
      `tsconfig.json` - before walking the graph it builds for
      cross-boundary edges. Passing no flag, or the wrong `tsconfig` file,
      resolves no `paths` at all and every alias-routed cross-boundary
      edge this check exists to find is missing from the graph.
  - lang: typescript
    kind: procedure
    applies_when: >-
      The project carries no `.dependency-cruiser` config, so the
      dependency-cruiser route above does not apply.
    note: >-
      Read the `tsconfig` path aliases and project references as the
      declared boundaries, walk each module's import specifiers, and check
      every cross-boundary edge against them. Record the offending
      `file:line`.
---

# Layering / dependency-rule conformance

Every import that crosses a tier boundary the wrong way (a lower tier importing a higher one), or an edge the documented rules forbid. This is the highest-value axis when the project documents its layers.

## Severity

**Critical** - an import that violates a documented dependency rule (e.g. a lower tier importing a higher one). These break the architecture the team committed to.

## Tooling fallback

**Python** - `import-linter` if a `.importlinter` contract exists, or `tach`. If neither, build the ground-truth edge set yourself - parse each module's `import` / `from ... import` statements (`grimp`, or an AST/`ast`-based walk, or a scoped grep) and check every cross-tier edge against the declared rules. Record the offending `file:line` for each violation.

**TypeScript** - `dependency-cruiser` if the project has a `.dependency-cruiser` config, else read the `tsconfig` path aliases and project references as the declared boundaries, walk each module's import specifiers, and check every cross-boundary edge against them. Record the offending `file:line`. `dependency-cruiser` needs the target's own dependencies present for two target-side reasons: an uninstalled tree returns every external import as `couldNotResolve: true` with dependency type `unknown`, so a project's own `.dependency-cruiser` config that forbids by dependency type (`not-to-dev-dep`, `not-to-unresolvable`, `no-non-package-json`) silently stops enforcing those rules while still reporting green; and where the `tsconfig` extends a base config that lives in `node_modules` - a `@tsconfig/*` preset, a framework preset, an internal base package - an uninstalled tree loses that `extends` chain, `paths` falls back to nothing, and the path aliases this fallback tells you to read as the declared boundaries disappear along with it, so a first-party cross-boundary edge routed through an alias goes unseen rather than merely unchecked. Feed it the compiler through a one-shot runner instead of relying on it being present, and **pin it below the major this tool rejects** (`npx --package 'typescript@^5' --package dependency-cruiser -- depcruise`, `pnpm --package=typescript@^5 --package=dependency-cruiser dlx depcruise` - **note the flags precede `dlx` on pnpm**, since `pnpm dlx --package=...` reads the flag as a package spec and fails with `ERR_PNPM_SPEC_NOT_SUPPORTED_BY_ANY_RESOLVER` - or `yarn dlx -p typescript@^5 -p dependency-cruiser depcruise`) - skip that and it reports zero modules cruised at exit 0, which reads as zero violations rather than as nothing having been checked. All three name the packages rather than leaning on the command name, and none of the three may be left to the reader to reconstruct: `depcruise` is the command this tool documents but not the name of the package that provides it, and npm carries an unrelated package under that name - a dependency-confusion placeholder whose bin prints a misconfiguration notice and exits 0 - so a bare `dlx depcruise` also comes back with nothing at exit 0, by a different route than a dropped co-package, and neither route looks like a tool that failed. Run against a real npm target at dependency-cruiser 18.2.0, three further routes each returned an unusable answer, and the version pin above is the first of them: an unpinned `typescript` co-package resolves to 7.x, outside the `>=2.0.0 <7.0.0` this tool declares, so `depcruise --info` reports no TypeScript transpiler and enables only `.js .cjs .mjs .jsx` - whereupon a **directory** argument cruises `totalCruised: 0` at exit 0, and the same invocation with the pin cruises the tree. Second, a target with no `.dependency-cruiser` config - the ordinary case, not the exotic one - **exits 1** with `Can't open a config file`, so this tool answers only once given `--config` with an audit-owned config or `--no-config`, and that choice is not free. Third, `--no-config` is what depcruise's own error message suggests and it **discards `--ts-config` along with the rules**: the tree that resolved its first-party graph under an audit-owned config came back with 281 unresolvable first-party specifiers and an empty cycle set under `--no-config`, at exit 0. So prefer an audit-owned config setting `options.tsConfig` and `enhancedResolveOptions.extensions`, and read [the smoke run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md) for the observed output behind each of the three. On pnpm the co-package is less dependable still, and its two failures point opposite ways: on pnpm 9.15.9 the ordering above supplies the compiler and `pnpm dlx --package=` errors outright, while on pnpm 11 `depcruise --info` reported no TypeScript under *either* ordering - so the tool ran and the compiler never arrived, with nothing on stderr to say so. Where the partition is pnpm, install into an audit-owned directory rather than trusting the runner to carry a second package. Reach for `madge` first on a partition where the tree isn't resolved, since it excludes installed dependencies and carries its own TypeScript - but **only where that partition's `tsconfig` does not `extend` a base that lives in `node_modules`**, because `madge` resolves the `tsconfig` through the TypeScript API too, so the same lost `extends` chain takes `paths` from it and the cross-boundary edges routed through an alias vanish from its graph at exit 0 exactly as they do from `dependency-cruiser`'s. **Give `madge` that `tsconfig` explicitly with `--ts-config`, on every partition - and give it the file that carries `paths`, which on a solution-style layout is not `tsconfig.json`.** A Vite or React project commonly ships `tsconfig.json` holding only `{"files": [], "references": [...]}` with the compiler options in `tsconfig.app.json` beside it; madge does not follow `references`, so pointing at `tsconfig.json` there is byte-for-byte the same as passing no flag at all. Measured on one such partition: 45 warnings and 6 cycles with `tsconfig.json` or with no flag, 31 warnings and 7 cycles with `tsconfig.app.json`. The instruction is followed, and the cycle it exists to expose stays hidden. Its `tsConfig` option is documented with a default of `null` and it discovers no config on its own - only a `.madgerc` or a `madge` key in the partition's `package.json` supplies one otherwise - so an invocation without the flag resolves no `paths` at all, and every alias-routed cross-boundary edge this check exists to find is missing from its graph at exit 0, on a partition whose `tsconfig` extends nothing at all. The `extends` condition above is what remains once the flag is passed, not an alternative to passing it. Read the partition's `tsconfig` for that `extends` before trusting either tool: where it is there, neither has a complete first-party graph without the tree, and the check is `no-evidence (not-permitted)` rather than a clean conformance result. The `extends` claim about `madge` is reasoned from documented behaviour - TypeScript's `extends` resolution - and is not reproduced on a fixture here. The `--ts-config` claim no longer rests on reasoning: run against a real npm target whose `tsconfig` extends nothing, `madge --circular` without the flag reported `✔ No circular dependency found!` at exit 0 where the same command with it found two, and the dependency map went from 1090 edges to 122, reordering the hubs rather than thinning them - so the flag is what stands between this tool and a false clean, on a partition the `extends` condition never applied to.

## Fix

Invert or cut an illegal edge: move the shared type down to a lower tier both sides may import, introduce an interface/protocol the lower tier defines and the higher tier implements, or relocate the misplaced module. Re-run the layering check to green.

## Review lens

**Layering-fix adequacy** - is each flagged edge genuinely a violation of the documented (or confirmed) rules, and does each fix actually remove the edge rather than hide it (e.g. a lazy import that still couples the tiers)?
