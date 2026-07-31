---
id: arch/complexity
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [ruff, radon, xenon]
  typescript: [eslint, eslint-plugin-sonarjs]
---

# Complexity

Functions/modules with high cyclomatic complexity or deep nesting that resist understanding and testing.

## Severity

**Important** - a function whose complexity makes it untestable.

**Important** - the threshold is unconfigured, so complexity is ungated and a regression is never caught. Report this once for the repo, not once per package.

**Minor** - a moderately complex function - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - `ruff check --select C901` or `radon cc` / `xenon`. Capture the metric per function.

**Read the project's configured threshold before measuring, and treat its absence as a finding in its own right.** `C901` needs `mccabe` max-complexity set in `pyproject.toml`; if it is unset, passing a threshold on the command line yields clean numbers and silently hides the gap. Whichever tool you run, record what the project itself enforces - a number it never configured is a number nothing holds it to.

**TypeScript** - ESLint's `complexity` and `max-depth` rules, or `eslint-plugin-sonarjs` for cognitive complexity. Capture the metric per function.

**With none of them installed** - walk each function's syntax tree and count its branch points (every `if`, `for`, `while`, `case`, `except`/`catch`, boolean operator and comprehension condition adds one to a base of one); that is cyclomatic complexity by definition, and a few lines of `ast` or an equivalent parser gets it. Nesting depth is the cheaper proxy where no parser is available at all.
