---
id: arch/coupling
domain: arch
locality: global
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [grimp, pydeps]
  typescript: [dependency-cruiser, madge]
needs:
  resolved-tree: [pydeps, dependency-cruiser]
---

# Coupling & cohesion

Too **coarse**: modules with too many afferent/efferent dependencies (a hub everything imports, or a module that reaches into everything), or modules whose contents don't belong together (grab-bag `utils`).

## Severity

**Important** - a god-module with runaway coupling that blocks safe change.

**Minor** - a grab-bag `utils` that should be split - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - compute afferent/efferent counts per module from the same edge set; flag the top hubs. `pydeps` gives a visual; the counts are the evidence. `pydeps` reads import opcodes from compiled bytecode rather than executing the target, so a dependency the import machinery can't find just drops out of the graph - an uninstalled package thins a hub's count instead of flagging its own absence.

**TypeScript** - compute the same afferent/efferent counts from `dependency-cruiser`'s or `madge`'s dependency map; flag the top hubs. The graph render is a visual; the counts are the evidence. `dependency-cruiser` needs the target's own dependencies present for its own reason: where the `tsconfig` extends a base config living in `node_modules`, an uninstalled tree loses that `extends` chain and `paths` falls back to nothing, so first-party aliased imports stop resolving and the hub counts this check rests on go wrong rather than merely thin. Feed it the compiler through a one-shot runner instead of relying on it being present, and **pin it below the major this tool rejects** (`npx --package 'typescript@^5' --package dependency-cruiser -- depcruise`, `pnpm dlx --package=typescript@^5 --package=dependency-cruiser depcruise`, or `yarn dlx -p typescript@^5 -p dependency-cruiser depcruise`) - skip that and it reports zero modules cruised at exit 0, a hub count of nothing rather than an error. All three name the packages rather than leaning on the command name, and none of the three may be left to the reader to reconstruct: `depcruise` is the command this tool documents but not the name of the package that provides it, and npm carries an unrelated package under that name - a dependency-confusion placeholder whose bin prints a misconfiguration notice and exits 0 - so a bare `dlx depcruise` also comes back with nothing at exit 0, by a different route than a dropped co-package, and neither route looks like a tool that failed. Run against a real npm target at dependency-cruiser 18.2.0, three further routes each returned an unusable answer, and the version pin above is the first of them: an unpinned `typescript` co-package resolves to 7.x, outside the `>=2.0.0 <7.0.0` this tool declares, so `depcruise --info` reports no TypeScript transpiler and enables only `.js .cjs .mjs .jsx` - whereupon a **directory** argument cruises `totalCruised: 0` at exit 0, and the same invocation with the pin cruises the tree. Second, a target with no `.dependency-cruiser` config - the ordinary case, not the exotic one - **exits 1** with `Can't open a config file`, so this tool answers only once given `--config` with an audit-owned config or `--no-config`, and that choice is not free. Third, `--no-config` is what depcruise's own error message suggests and it **discards `--ts-config` along with the rules**: the tree that resolved its first-party graph under an audit-owned config came back with 281 unresolvable first-party specifiers and an empty cycle set under `--no-config`, at exit 0. So prefer an audit-owned config setting `options.tsConfig` and `enhancedResolveOptions.extensions`, and read [the smoke run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md) for the observed output behind each of the three. `madge` is the read-only option **only where the partition's `tsconfig` does not `extend` a base that lives in `node_modules`**: it excludes installed dependencies and carries its own TypeScript, so it needs no install, but it resolves the `tsconfig` through the TypeScript API like anything else, so the same missing `extends` chain costs it `paths` and it returns a thinned graph at exit 0 rather than an error. **Give `madge` that `tsconfig` explicitly with `--ts-config`, on every partition.** Its `tsConfig` option is documented with a default of `null` and it discovers no config on its own - only a `.madgerc` or a `madge` key in the partition's `package.json` supplies one otherwise - so an invocation without the flag resolves no `paths` at all, and the hub counts come back computed over a graph every aliased import has dropped out of, on a partition whose `tsconfig` extends nothing at all. The `extends` condition above is what remains once the flag is passed, not an alternative to passing it. Read the partition's `tsconfig` for that `extends` before trusting either tool: where it is there, neither has a complete first-party graph without the tree, and the check is `no-evidence (not-permitted)` rather than a hub count. The `extends` claim about `madge` is reasoned from documented behaviour - TypeScript's `extends` resolution - and is not reproduced on a fixture here. The `--ts-config` claim no longer rests on reasoning: run against a real npm target whose `tsconfig` extends nothing, `madge --circular` without the flag reported `✔ No circular dependency found!` at exit 0 where the same command with it found two, and the dependency map went from 1090 edges to 122, reordering the hubs rather than thinning them - so the flag is what stands between this tool and a false clean, on a partition the `extends` condition never applied to.

## Fix

Split a god-module along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

**Coupling attribution** - direct vs transitive coupling attributed correctly.

**Split-fix cohesion** - a split fix didn't fragment a cohesive unit into ravioli.
