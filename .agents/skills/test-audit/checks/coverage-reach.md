---
id: test/coverage-reach
domain: test
locality: local
evidence: >-
  Branch coverage is the signal; capture the missing line/branch ranges per
  module as the evidence pointer, in either language. What the untiered
  `kind: procedure` routes below read - what a project excluded from
  measurement, and the branch threshold it set for itself - is part of what
  this check asks, as what its measured number is read against. Two adjacent
  questions are not this check's. Whether a coverage threshold is *enforced* is
  `ci/gate-enforcement`'s - it owns whether an intended gate is actually
  required. Whether a floor was ever *decided*, and whether it has an
  executable home rather than living in prose, is
  `test/coverage-floor-declaration`'s. What stays here is whether the number
  this check measures is adequate and whether the threshold measures the right
  thing - the `fail_under`-without-`branch = true` pair the Python route below
  names is a metric-basis finding and belongs to this record. Every command route below runs
  the target's own suite to produce its report, which is the `target-execution`
  grant; without it the reach measurement itself is
  `no-evidence (not-permitted)`, and what remains is the exclusion-config
  reading those untiered routes carry.
handbook:
  - implementation-disciplines/tdd-b
routes:
  - lang: python
    kind: command
    answers: measurement
    tool: pytest-cov
    argv: [pytest, "--cov-branch", "--cov-report=term-missing"]
    in_env: true
    needs: target-execution
    note: >-
      The argv omits the `--cov=<pkg>` the record's own form carries and is
      not a complete invocation. Write it as `pytest --cov=<pkg>
      --cov-branch --cov-report=term-missing`, naming the package under
      measurement; `<pkg>` is the caller's to resolve, which is why the argv
      stops short of the placeholder.
  - lang: python
    kind: command
    answers: measurement
    tool: coverage.py
    package: coverage
    argv: [coverage, run, "-m", pytest]
    then: [coverage, report, "--show-missing"]
    in_env: true
    needs: target-execution
    note: >-
      The other form the record writes for the Python side -
      `coverage run -m pytest` followed by `coverage report --show-missing` -
      and one route rather than two: the two commands are prescribed in
      sequence, so the second is this route's `then` rather than a route of its
      own.
  - lang: python
    kind: procedure
    answers: configuration
    note: >-
      What is excluded from measurement is readable with nothing installed.
      `[tool.coverage.run]`'s `source` and `omit`, and
      `[tool.coverage.report]`'s `exclude_lines`, in `pyproject.toml` (`[run]`
      and `[report]` respectively in `.coveragerc`), name the code no coverage
      number will ever account for. What the project asked of itself is
      `[tool.coverage.report]`'s `fail_under`, and read it for what it is: a
      floor on the total, not on branches, so a project that set it without
      also setting `branch = true` in `[tool.coverage.run]` has a threshold
      that never looked at a branch. That pair is the finding, and coverage.py
      offers no branch-only floor to look for instead - unlike the TypeScript
      side, where `coverage.thresholds.branches` and
      `coverageThreshold.global.branches` are branch thresholds outright. The
      reach measurement itself runs the suite and does not survive a withheld
      grant; this reading does, which is why it is what a withheld grant
      leaves.
  - lang: typescript
    kind: command
    answers: measurement
    tool: vitest
    argv: [vitest, run, "--coverage"]
    in_env: true
    needs: target-execution
    applies_when: >-
      The project inventory says this partition has Vitest. Use the runner the
      inventory names, because neither runner can run the other's suite.
    note: >-
      `vitest run --coverage` reports branch coverage, and its coverage needs
      the coverage provider the partition has configured to be installed. **Where the runner has coverage
      integration but the provider is missing, install the provider into a copy
      of the target this check owns and re-run there** - that is the only route
      observed to produce a true number, and it is not an install into the
      target, which stays barred. **Its own copy, not the shared reconstructed
      tree a sweep hands every domain at once**: the provider is a package the
      target does not declare, so adding it to the shared tree mutates what the
      other domains are concurrently measuring and leaves `deps` reading it as
      one the target declared, which is why `audit-core` requires the second
      copy rather than treating any audit-side tree as fair game. Vitest names
      the missing package outright
      (`MISSING DEPENDENCY Cannot find dependency '@vitest/coverage-v8'`), and
      **pass `--coverage.reportOnFailure` when you do**: it defaults to false,
      so a target whose suite has one failing test - the ordinary state of a
      foreign repository at an arbitrary ref - produces no coverage report at
      all while otherwise looking like a run that worked.
  - lang: typescript
    kind: command
    answers: measurement
    tool: jest
    argv: [jest, "--coverage"]
    in_env: true
    needs: target-execution
    applies_when: >-
      The project inventory says this partition has Jest. Use the runner the
      inventory names, because neither runner can run the other's suite.
    note: >-
      `jest --coverage` reports branch coverage.
  - lang: typescript
    kind: procedure
    tool: c8
    disposition: forbidden
    applies_when: >-
      The command to be wrapped is a Vitest command - the case this route
      exists to refuse.
    note: >-
      **Never reach for `c8` around a Vitest command.** `c8` wraps an arbitrary
      command and is fetchable from npm, and it cannot
      see coverage produced inside Vitest's worker processes, nor the TypeScript
      Vitest transforms in memory: run against a real target it reported
      **96.35% statements and 69.56% branches over three files** - two configs
      and one script - where the provider-based measurement of the same tree was
      **8.05% and 5.86%** over 339 files. That is a false clean in exactly the
      format this check asks for, and it is worse than `no-evidence`. Pointed at
      the source tree with `--all --src`, the same `c8` run reports 0% of 47,306
      statements, which is honest and still measures nothing. The record
      prescribes no `c8` command line, so there is no argv to declare, and the
      prohibition is this route's `disposition`: a forbidden procedure route
      names the tool it warns against and its note says why. It carries no
      `answers` and no `needs`, because a route the record forbids running
      answers no axis and needs nothing; the axis the prohibited run would
      have falsified is `measurement`, which the `vitest`, `jest` and
      plain-form `c8` routes answer.
  - lang: typescript
    kind: procedure
    answers: measurement
    tool: c8
    needs: target-execution
    applies_when: >-
      The command to be wrapped belongs to a runner `c8` can actually observe -
      one whose tests run in the process it wrapped.
    note: >-
      `c8`'s plain form remains the measurement there, and its reporter defaults
      to `text`, Istanbul's per-file table of `% Stmts`, `% Branch`, `% Funcs`,
      `% Lines` and `Uncovered Line #s`, exactly the evidence this check wants.
      Confirm the file list in that table is the source tree before reading any
      number off it. Add `--check-coverage --branches <n>` only where the
      project already states a branch floor of its own and you are checking the
      suite against it: it is a gate rather than a measurement, exiting nonzero
      when coverage falls short, so reaching for it here would make you invent
      an `<n>` the project never asked for and would turn a measurement that
      worked into something that looks like `tool-failed`. No command line is
      prescribed for this form either, so there is no argv to declare: writing
      one would invent the command being wrapped.
  - lang: typescript
    kind: procedure
    answers: configuration
    note: >-
      What is excluded from measurement is readable with nothing installed:
      `coverage.include` and `coverage.exclude` in `vitest.config.*` or in the
      `test` block of `vite.config.*` - Vitest looks for `vitest.config.*`
      first and `vite.config.*` second, so a project with no `vitest.config.*`
      keeps these keys in its Vite config and a grep naming only the former
      reads a project that excluded half its tree as one that configured
      nothing - or `collectCoverageFrom` and `coveragePathIgnorePatterns` in
      `jest.config.*` or `package.json`'s `jest` key. A branch threshold the
      project set for itself is readable in the same place
      (`coverage.thresholds.branches`, `coverageThreshold.global.branches`) and
      says what it asked of itself. The reach measurement itself runs the suite
      and does not survive a withheld grant; this reading does, which is why it
      is what a withheld grant leaves.
---

# Coverage reach

Line and (crucially) **branch** coverage per module; uncovered load-bearing logic; error/exception paths never exercised. Raw percentage is context, not the finding - an uncovered branch in a scorer is.

## Severity

**Critical** - load-bearing deterministic logic (a scorer's math, an adjudicator's id-mapping, a parser, a security check) with **no** effective test.

**Important** - an untested error/branch path in important code.

**Minor** - a moderately-low-coverage-but-low-risk module.

## Fix

**Cover the gap with a real test:** exercise the actual branch/behavior and assert on the observable outcome, not on a value the test recomputed. Prefer testing the deterministic core directly; mock only true I/O edges.

## Review lens

**Coverage genuineness** - is the reported gain from real exercised behavior, not from importing code or asserting nothing? Branch coverage, not just line.
