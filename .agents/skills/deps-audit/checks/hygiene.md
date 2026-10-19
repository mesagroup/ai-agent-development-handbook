---
id: deps/hygiene
domain: deps
locality: global
evidence: >-
  A scanner run without the tree gives a partial signal, and a row records it
  with that limit rather than at face value: on a partition whose
  dependencies are not installed the scanner's row is `no-evidence
  (not-permitted)` rather than a clean result, and the check is carried by
  the manifest and lockfile reading the untiered route below prescribes, at
  lower recall than the scanner and reported as such. One answer at reduced
  recall, not two halves: the reading is the scanner's alternative, and a
  clean reading is not a clean scan.
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
routes:
  - lang: python
    kind: command
    tool: deptry
    argv: [deptry]
    in_env: true
    needs: target-execution
    findings_stream: stderr
    note: >-
      `deptry` answers unused / missing / transitive / misplaced. It reads
      installed distribution metadata, so it must run inside the project's own
      environment. Measured on a seeded partition, `deptry .` exits 1 with an
      empty stdout and its whole DEP002/DEP001 report on stderr, so a caller
      reading stdout, or treating the non-zero exit as the tool having failed,
      loses a real finding rather than an absence of one. Without the tree
      `deptry` is correct
      where a distribution name equals its import name and misreports in both
      directions at once where they diverge, emitting a declared-but-unused
      finding for the distribution and a missing-dependency finding for the
      import it could not resolve. **How the scan root is written changes what
      it does, twice over, and neither shows in the output.** The root selects
      the files while the dependency definitions come from the configuration
      found at the working directory, so `deptry <target>` run from anywhere
      else scans the target's source against *your* dependencies: measured by
      removing a declared dependency from a project and pointing the tool at
      it from outside, that prints `Success! No dependency issues found.` and
      exits 0, while the same files run with that project as the working
      directory report the missing import. An audit that reports a pass is
      worse than one that cannot run. **There is one right invocation, and it
      is `.` with the target as the working directory.**
      `--config <target>/pyproject.toml` is not the escape it looks like: it
      chooses which manifest supplies the dependency definitions and nothing
      else, so it leaves the second problem below untouched and still reads
      the caller's installed distributions rather than the target's, which
      this route's `in_env` requires. The second problem is that the exclude
      patterns are matched against the path as written, anchored at its
      start, and the defaults are relative - `tests`, `venv`, `\.venv`. So
      **any** root but `.` puts a prefix in front of every path and matches
      none of them: measured, a target scanned as an absolute path and as a
      relative sibling both pull its test suite in, where every
      `import pytest` returns as a misplaced dev dependency. Absoluteness is
      not the trigger; being anything other than `.` is. By the same
      mechanism a target carrying a virtualenv is exposed to having it
      scanned, those patterns sitting in the same anchored list. These are
      invocation artifacts rather than findings about the target, and unlike
      the first problem they are loud: the run fails, with findings that are
      not there. **A sibling module imported as a top-level
      name is the third:** where a target's scripts sit on `sys.path` and
      import each other, each such import is reported as a missing
      dependency, so on such a target the count of DEP001s can be entirely
      first-party and none of them a hygiene defect. A project closes it by
      declaring those modules in `known_first_party`, which is a fix to
      recommend rather than a finding to report.

      `deptry` takes a scan root and the record names none, so the argv is
      not a complete invocation on its own - and naming one is not enough
      either: it has to be `.`, with the target as the working directory,
      for the reasons given above. The two ways of getting it wrong are
      worth telling apart: name the wrong working directory and the run does
      not fail, it passes; write the root as anything but `.` and it fails
      loudly, with findings that are artifacts of the invocation.
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
