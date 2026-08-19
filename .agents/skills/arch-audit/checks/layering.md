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
      The record names `tach` as the alternative to a contract and
      prescribes nothing further about it - no command line, no
      configuration file, no output to capture - so, as with
      `import-linter` above, there is no argv to declare. What the record
      has the reader do by hand is the case where neither tool's condition
      holds, which is the tool-less route below rather than this one.
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
      cruises `totalCruised: 0` at exit 0. On pnpm the co-package is less
      dependable still, and installing into an audit-owned directory is
      what the record prefers there.
    alone_insufficient: >-
      Each spelling above is the prefix the record writes, not a complete
      invocation. A target with no `.dependency-cruiser` config - the
      record calls this the ordinary case, not the exotic one - exits 1
      with `Can't open a config file`. The audit-owned `--config` that
      answers that for other checks does not answer it for this one: the
      project's own config IS the declared boundary this check tests, so
      supplying one of the audit's own would judge layering against rules
      the audit invented. Where the project has no config this route does
      not apply at all, and the `applies_when` above sends the reader to
      the `tsconfig` path aliases and project references instead. The
      output observed behind that config-less exit 1 is recorded in [the
      smoke run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md).
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
      it carries are unresolvable without the tree, so this route has no
      complete first-party graph. What remains is the sibling
      `dependency-cruiser` route, which carries `resolved-tree` and does have
      the tree under that grant; the record reaches
      `no-evidence (not-permitted)` rather than a clean conformance result
      only once that grant is withheld too.
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
      edge this check exists to find is missing from the graph. Its
      `tsConfig` option is documented with a default of `null` and it
      discovers no config on its own - only a `.madgerc` or a `madge` key
      in the partition's `package.json` supplies one otherwise.
  - lang: typescript
    kind: procedure
    applies_when: >-
      The project carries no `.dependency-cruiser` config, so the
      dependency-cruiser route above does not apply. Where the partition's
      `tsconfig` also `extend`s a base that lives in `node_modules`, this
      route needs the tree materialized under `resolved-tree`: the extends
      chain resolves from the installed tree, and with it the `paths` this
      route reads.
    alone_insufficient: >-
      Where the `tsconfig` extends such a base and the tree is NOT present,
      that chain is lost and `paths` falls back to nothing, so the aliases
      this route reads as the declared boundaries disappear with it and an
      alias-routed cross-boundary edge goes unseen rather than merely
      unchecked - a clean result would be a false one. Both conditions have
      to hold for that: an extending `tsconfig` alone does not disqualify
      this route, and neither does an absent tree on a partition whose
      `tsconfig` extends nothing. Where both do hold, the record has no
      route left for this partition and reaches
      `no-evidence (not-permitted)`, the dependency-cruiser route above
      being unavailable for the separate reason that the project has no
      config of its own.
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

## Fix

Invert or cut an illegal edge: move the shared type down to a lower tier both sides may import, introduce an interface/protocol the lower tier defines and the higher tier implements, or relocate the misplaced module. Re-run the layering check to green.

## Review lens

**Layering-fix adequacy** - is each flagged edge genuinely a violation of the documented (or confirmed) rules, and does each fix actually remove the edge rather than hide it (e.g. a lazy import that still couples the tiers)?
