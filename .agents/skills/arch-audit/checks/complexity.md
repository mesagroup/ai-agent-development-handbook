---
id: arch/complexity
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [ruff, radon, xenon]
  typescript: [eslint, eslint-plugin-sonarjs]
needs:
  target-execution: [eslint, eslint-plugin-sonarjs]
ungranted_note: >-
  Cyclomatic complexity is a property of the syntax tree, so the branch-point count
  the `With none of them installed` paragraph below describes answers the metric on any
  partition with nothing installed, in either language. ESLint answers it too under a
  config the audit supplies rather than the target's: pointed at an audit-owned flat
  config with `--config` and `--no-config-lookup`, with a TypeScript parser fetched
  alongside ESLint rather than taken from the target, the core `complexity` and
  `max-depth` rules read the target's source without loading the target's own flat
  config, so no `node_modules` is needed. What the grant buys is the thresholds the
  project set for itself, and `eslint-plugin-sonarjs`'s type-aware cognitive-complexity
  rules, which need a real TypeScript program over the installed tree.
---

# Complexity

Functions/modules with high cyclomatic complexity or deep nesting that resist understanding and testing.

## Severity

**Important** - a function whose complexity makes it untestable.

**Minor** - a moderately complex function - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - `ruff check --select C901` or `radon cc` / `xenon`. Capture the metric per function.

**TypeScript** - ESLint's `complexity` and `max-depth` rules, or `eslint-plugin-sonarjs` for cognitive complexity. Capture the metric per function. Both, run under the target's own flat config, load their plugins from the target's own `node_modules`; without it ESLint aborts with `ERR_MODULE_NOT_FOUND` rather than reporting a metric, and `eslint-plugin-sonarjs`'s type-aware rules additionally need a real TypeScript program over the installed tree - see the note above for the audit-owned-config path that avoids this.

**With none of them installed** - walk each function's syntax tree and count its branch points (every `if`, `for`, `while`, `case`, `except`/`catch`, boolean operator and comprehension condition adds one to a base of one); that is cyclomatic complexity by definition, and a few lines of `ast` or an equivalent parser gets it. Nesting depth is the cheaper proxy where no parser is available at all.
