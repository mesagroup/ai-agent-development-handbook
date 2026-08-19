---
id: arch/complexity
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
routes:
  - lang: python
    kind: command
    tool: ruff
    argv: [ruff, check, "--select", C901]
    note: >-
      Capture the metric per function.
  - lang: python
    kind: command
    tool: radon
    argv: [radon, cc]
    note: >-
      Capture the metric per function. The path to measure is an operand the
      record names none for.
  - lang: python
    kind: command
    tool: xenon
    argv: [xenon]
    findings_stream: stderr
    note: >-
      Capture the metric per function. `xenon` reports its finding on stderr,
      not stdout, and exits 1 when a block breaches the configured threshold -
      observed as `ERROR:xenon:block "<path>:<line> <function>" has a rank of
      C` on stderr with stdout empty. A caller that reads stdout, or that
      treats the non-zero exit itself as the tool having failed, loses a real
      finding rather than an absence of one. The record names the tool and no
      arguments; the threshold and the path are operands it names none for.
  - lang: typescript
    kind: procedure
    tool: eslint
    note: >-
      Capture the metric per function. ESLint's core `complexity` and
      `max-depth` rules under a flat config the audit supplies rather than the
      target's: pointed at an audit-owned flat config with `--config` and
      `--no-config-lookup`, they read the target's source without loading the
      target's own flat config, so no `node_modules` is needed - 286 functions
      over a threshold of 10 on the target this was first run against. The record names those two flags in a sentence and
      prescribes no command line, and `--config` takes a config path the record
      names no value for, so there is no argv to declare and a `kind: command`
      route would have to invent one. Install ESLint and the TypeScript parser
      into an audit-owned directory and keep that config in it; a parser handed
      to a one-shot runner instead is not resolvable from a config living
      outside the runner's sandbox, which aborts the run with
      `ERR_MODULE_NOT_FOUND` before any rule reads anything. What the install
      needs is network rather than the target's tree, which is why this route
      carries no tier and survives a withheld grant.
  - lang: typescript
    kind: procedure
    tool: eslint
    needs: target-execution
    note: >-
      Capture the metric per function. The same two rules run under the
      target's own flat config, which is what the grant buys: the thresholds
      the project set for itself. That config
      loads its plugins from the target's own `node_modules`, and without it
      ESLint aborts with `ERR_MODULE_NOT_FOUND` rather than reporting a metric.
      The record names the rules and prescribes no command line for them, so
      this route declares no argv either. It is the same tool as the route
      above and a different invocation mode, which is the whole distinction
      between them; the schema carries the two tiers and the two notes, and
      nothing machine-readable tells the modes apart.
  - lang: typescript
    kind: procedure
    tool: eslint-plugin-sonarjs
    needs: target-execution
    note: >-
      Cognitive complexity, captured per function like the metrics above. The
      record names the plugin and prescribes no command line for it. Its type-aware rules need a real TypeScript program
      over the installed tree, so unlike the core rules above there is no
      audit-owned-config path that avoids the grant.
  - lang: any
    kind: procedure
    note: >-
      Cyclomatic complexity is a property of the syntax tree, so this answers
      the metric on any partition with nothing installed, in either language.
      With none of them installed, walk each function's syntax tree and count
      its branch points (every `if`, `for`, `while`, `case`, `except`/`catch`,
      boolean operator and comprehension condition adds one to a base of one);
      that is cyclomatic complexity by definition, and a few lines of `ast` or
      an equivalent parser gets it. Nesting depth is the cheaper proxy where no
      parser is available at all.
---

# Complexity

Functions/modules with high cyclomatic complexity or deep nesting that resist understanding and testing.

## Severity

**Important** - a function whose complexity makes it untestable.

**Minor** - a moderately complex function - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - `ruff check --select C901` or `radon cc` / `xenon`. Capture the metric per function. `xenon` reports its finding on stderr, not stdout, and exits 1 when a block breaches the configured threshold - observed as `ERROR:xenon:block "<path>:<line> <function>" has a rank of C` on stderr with stdout empty. A caller that reads stdout, or that treats the non-zero exit itself as the tool having failed, loses a real finding rather than an absence of one.

**TypeScript** - ESLint's `complexity` and `max-depth` rules, or `eslint-plugin-sonarjs` for cognitive complexity. Capture the metric per function. Both, run under the target's own flat config, load their plugins from the target's own `node_modules`; without it ESLint aborts with `ERR_MODULE_NOT_FOUND` rather than reporting a metric, and `eslint-plugin-sonarjs`'s type-aware rules additionally need a real TypeScript program over the installed tree - see the note above for the audit-owned-config path that avoids this.

**With none of them installed** - walk each function's syntax tree and count its branch points (every `if`, `for`, `while`, `case`, `except`/`catch`, boolean operator and comprehension condition adds one to a base of one); that is cyclomatic complexity by definition, and a few lines of `ast` or an equivalent parser gets it. Nesting depth is the cheaper proxy where no parser is available at all.
