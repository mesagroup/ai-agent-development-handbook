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
tooling:
  python: [import-linter, tach, grimp]
  typescript: [dependency-cruiser, madge]
needs:
  resolved-tree: [dependency-cruiser]
---

# Layering / dependency-rule conformance

Every import that crosses a tier boundary the wrong way (a lower tier importing a higher one), or an edge the documented rules forbid. This is the highest-value axis when the project documents its layers.

## Severity

**Critical** - an import that violates a documented dependency rule (e.g. a lower tier importing a higher one). These break the architecture the team committed to.

## Tooling fallback

**Python** - `import-linter` if a `.importlinter` contract exists, or `tach`. If neither, build the ground-truth edge set yourself - parse each module's `import` / `from ... import` statements (`grimp`, or an AST/`ast`-based walk, or a scoped grep) and check every cross-tier edge against the declared rules. Record the offending `file:line` for each violation.

**TypeScript** - `dependency-cruiser` if the project has a `.dependency-cruiser` config, else read the `tsconfig` path aliases and project references as the declared boundaries, walk each module's import specifiers, and check every cross-boundary edge against them. Record the offending `file:line`. `dependency-cruiser` needs the target's own dependencies present for two target-side reasons: an uninstalled tree returns every external import as `couldNotResolve: true` with dependency type `unknown`, so a project's own `.dependency-cruiser` config that forbids by dependency type (`not-to-dev-dep`, `not-to-unresolvable`, `no-non-package-json`) silently stops enforcing those rules while still reporting green; and where the `tsconfig` extends a base config that lives in `node_modules` - a `@tsconfig/*` preset, a framework preset, an internal base package - an uninstalled tree loses that `extends` chain, `paths` falls back to nothing, and the path aliases this fallback tells you to read as the declared boundaries disappear along with it, so a first-party cross-boundary edge routed through an alias goes unseen rather than merely unchecked. Feed it the compiler through a one-shot runner instead of relying on it being present (`npx --package typescript --package dependency-cruiser -- depcruise`, `pnpm dlx --package=typescript --package=dependency-cruiser depcruise`, or `yarn dlx -p typescript -p dependency-cruiser depcruise`) - skip that and it reports zero modules cruised at exit 0, which reads as zero violations rather than as nothing having been checked. All three name the packages rather than leaning on the command name, and none of the three may be left to the reader to reconstruct: `depcruise` is the command this tool documents but not the name of the package that provides it, and npm carries an unrelated package under that name - a dependency-confusion placeholder whose bin prints a misconfiguration notice and exits 0 - so a bare `dlx depcruise` also comes back with nothing at exit 0, by a different route than a dropped co-package, and neither route looks like a tool that failed. Reach for `madge` first on a partition where the tree isn't resolved, since it excludes installed dependencies and carries its own TypeScript - but **only where that partition's `tsconfig` does not `extend` a base that lives in `node_modules`**, because `madge` resolves the `tsconfig` through the TypeScript API too, so the same lost `extends` chain takes `paths` from it and the cross-boundary edges routed through an alias vanish from its graph at exit 0 exactly as they do from `dependency-cruiser`'s. **Give `madge` that `tsconfig` explicitly with `--ts-config`, on every partition.** Its `tsConfig` option is documented with a default of `null` and it discovers no config on its own - only a `.madgerc` or a `madge` key in the partition's `package.json` supplies one otherwise - so an invocation without the flag resolves no `paths` at all, and every alias-routed cross-boundary edge this check exists to find is missing from its graph at exit 0, on a partition whose `tsconfig` extends nothing at all. The `extends` condition above is what remains once the flag is passed, not an alternative to passing it. Read the partition's `tsconfig` for that `extends` before trusting either tool: where it is there, neither has a complete first-party graph without the tree, and the check is `no-evidence (not-permitted)` rather than a clean conformance result. Both claims about `madge` are reasoned from documented behaviour - TypeScript's `extends` resolution and `madge`'s own `tsConfig` default - and neither is reproduced on a fixture here.

## Fix

Invert or cut an illegal edge: move the shared type down to a lower tier both sides may import, introduce an interface/protocol the lower tier defines and the higher tier implements, or relocate the misplaced module. Re-run the layering check to green.

## Review lens

**Layering-fix adequacy** - is each flagged edge genuinely a violation of the documented (or confirmed) rules, and does each fix actually remove the edge rather than hide it (e.g. a lazy import that still couples the tiers)?
