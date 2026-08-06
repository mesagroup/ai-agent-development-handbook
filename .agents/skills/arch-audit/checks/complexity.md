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
---

# Complexity

Functions/modules with high cyclomatic complexity or deep nesting that resist understanding and testing.

## Severity

**Important** - a function whose complexity makes it untestable.

**Minor** - a moderately complex function - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - `ruff check --select C901` or `radon cc` / `xenon`. Capture the metric per function.

**TypeScript** - ESLint's `complexity` and `max-depth` rules, or `eslint-plugin-sonarjs` for cognitive complexity. Capture the metric per function. Both load through a flat config that imports its plugins from the target's own `node_modules`; without it ESLint aborts with `ERR_MODULE_NOT_FOUND` rather than reporting a metric, and `eslint-plugin-sonarjs`'s type-aware rules additionally need a real TypeScript program over the installed tree.

**With none of them installed** - walk each function's syntax tree and count its branch points (every `if`, `for`, `while`, `case`, `except`/`catch`, boolean operator and comprehension condition adds one to a base of one); that is cyclomatic complexity by definition, and a few lines of `ast` or an equivalent parser gets it. Nesting depth is the cheaper proxy where no parser is available at all.
