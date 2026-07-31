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
---

# Layering / dependency-rule conformance

Every import that crosses a tier boundary the wrong way (a lower tier importing a higher one), or an edge the documented rules forbid. This is the highest-value axis when the project documents its layers.

## Severity

**Critical** - an import that violates a documented dependency rule (e.g. a lower tier importing a higher one). These break the architecture the team committed to.

## Tooling fallback

**Python** - `import-linter` if a `.importlinter` contract exists, or `tach`. If neither, build the ground-truth edge set yourself - parse each module's `import` / `from ... import` statements (`grimp`, or an AST/`ast`-based walk, or a scoped grep) and check every cross-tier edge against the declared rules. Record the offending `file:line` for each violation.

**TypeScript** - `dependency-cruiser` if the project has a `.dependency-cruiser` config, else read the `tsconfig` path aliases and project references as the declared boundaries, walk each module's import specifiers, and check every cross-boundary edge against them. Record the offending `file:line`.

## Fix

Invert or cut an illegal edge: move the shared type down to a lower tier both sides may import, introduce an interface/protocol the lower tier defines and the higher tier implements, or relocate the misplaced module. Re-run the layering check to green.

## Review lens

Is each flagged edge genuinely a violation of the documented (or confirmed) rules, and does each fix actually remove the edge rather than hide it (e.g. a lazy import that still couples the tiers)?
