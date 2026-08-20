---
id: deps/hygiene
domain: deps
locality: global
evidence: >-
  A scanner run without the tree gives a partial signal, and a row records it
  with that limit rather than at face value: on a partition whose
  dependencies are not installed the scanner half of this check is
  `no-evidence (not-permitted)` rather than a clean result.
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
routes:
  - lang: python
    kind: command
    tool: deptry
    argv: [deptry]
    in_env: true
    needs: resolved-tree
    findings_stream: stderr
    note: >-
      `deptry` answers unused / missing / transitive / misplaced. It reads
      installed distribution metadata, so it must run inside the project's own
      environment. Measured on a seeded partition, `deptry .` exits 1 with an
      empty stdout and its whole DEP002/DEP001 report on stderr, so a caller
      reading stdout, or treating the non-zero exit as the tool having failed,
      loses a real finding rather than an absence of one. The scan root is an
      operand the record names none for. Without the tree `deptry` is correct
      where a distribution name equals its import name and misreports in both
      directions at once where they diverge, emitting a declared-but-unused
      finding for the distribution and a missing-dependency finding for the
      import it could not resolve.
    applies_when: >-
      The partition is not pipenv-only. `deptry` has no reader for `Pipfile`
      or `Pipfile.lock` at all: pointed at a pipenv-only project it raises
      `deptry.exceptions.DependencySpecificationNotFoundError` ("No file
      called 'pyproject.toml' with a [tool.poetry.dependencies], [tool.pdm] or
      [project] section or file(s) called 'requirements.txt' found")
      regardless of whether the tree is resolved, so a pipenv partition has no
      scanner lens under this record on either grant.
  - lang: any
    kind: procedure
    note: >-
      What answers with nothing installed, so a withheld grant leaves this
      check answerable in either language: duplicate and conflicting pins, and
      a dependency declared in the wrong group, are read from the manifest and
      the lockfile. The alternative to a scanner in Python is the same reading
      pass one step further - an import-vs-declared cross-check.
  - lang: typescript
    kind: procedure
    tool: depcheck
    needs: resolved-tree
    note: >-
      A registry package a one-shot runner can fetch, and this check does not
      branch on which package manager the partition uses, so the record names
      the tool and prescribes no command line and a `kind: command` route
      would have to invent one. It does not answer from `package.json` plus
      the source alone. `depcheck` resolves plain `require` and `import` usage
      without `node_modules`, and its `bin` and config specials are exactly
      the part that needs the tree: the `bin` special resolves each
      dependency's *installed* `package.json` to learn its bin names, and
      `loadModuleData` swallows a resolution failure and returns null
      metadata, so a dependency used only as a CLI in `scripts` is silently
      reported unused when `node_modules` is absent - reproduced on a fixture
      whose scripts were `eslint .` and `tsc -p .`: with no `node_modules`,
      `depcheck` reported `eslint` and `typescript` as unused devDependencies,
      and after an install it reported neither. Its `eslint` special likewise
      `require`s the resolved shareable config and silently returns nothing on
      failure.
  - lang: typescript
    kind: procedure
    tool: knip
    needs: target-execution
    note: >-
      Where the question extends to unused exports and files. A registry
      package a one-shot runner can fetch, named without a command line for
      the same reason `depcheck` is. It needs more than the tree, because it
      loads and executes the target's own tool configuration (its peer deps
      `typescript` and `@types/node`, plus whatever the config files declare)
      to see what is actually exported, which is why it sits at
      `target-execution` where `depcheck` sits at `resolved-tree`. `knip`
      answers nothing trustworthy without the tree.
---

# Hygiene

Declared-but-unused dependencies, used-but-undeclared (relying on a transitive), duplicate/conflicting pins, dev deps leaking into runtime.

## Severity

**Important** - a used-but-undeclared dependency.

**Minor** - unused declared deps.

## Fix

Replace or remove an unused dependency; update imports; re-test.
