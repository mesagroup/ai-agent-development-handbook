---
id: test/coverage-reach
domain: test
locality: local
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [pytest-cov, coverage.py]
  typescript: [vitest, jest, c8]
needs:
  target-execution: [pytest-cov, coverage.py, vitest, jest, c8]
ungranted_note: >-
  What is excluded from measurement is readable with nothing installed, in either
  language. In Python, `[tool.coverage.run]`'s `source` and `omit`, and
  `[tool.coverage.report]`'s `exclude_lines`, in `pyproject.toml` (`[run]` and
  `[report]` respectively in `.coveragerc`), name the code no coverage number will
  ever account for. In TypeScript the same reading is `coverage.include` and
  `coverage.exclude` in `vitest.config.*` or in the `test` block of `vite.config.*` -
  Vitest looks for `vitest.config.*` first and `vite.config.*` second, so a project
  with no `vitest.config.*` keeps these keys in its Vite config and a grep naming only
  the former reads a project that excluded half its tree as one that configured
  nothing - or `collectCoverageFrom` and `coveragePathIgnorePatterns` in
  `jest.config.*` or `package.json`'s `jest` key; a
  branch threshold the project set for itself is readable in the same place
  (`coverage.thresholds.branches`, `coverageThreshold.global.branches`) and says what
  it asked of itself. That is part of what this check asks. The reach measurement
  itself runs the suite and does not survive a withheld grant, in either language.
  Whether a coverage threshold is *enforced* is a different check's question -
  `ci/gate-enforcement` owns whether an intended gate is actually required - so do not
  answer it here.
---

# Coverage reach

Line and (crucially) **branch** coverage per module; uncovered load-bearing logic; error/exception paths never exercised. Raw percentage is context, not the finding - an uncovered branch in a scorer is.

## Severity

**Critical** - load-bearing deterministic logic (a scorer's math, an adjudicator's id-mapping, a parser, a security check) with **no** effective test.

**Important** - an untested error/branch path in important code.

**Minor** - a moderately-low-coverage-but-low-risk module.

## Tooling fallback

**Python** - `pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage run -m pytest` + `coverage report --show-missing`). Branch coverage is the signal; capture the missing line/branch ranges per module as the evidence pointer.

**TypeScript** - use the runner the project inventory says the partition has, because neither runner can run the other's suite: `vitest run --coverage`, whose coverage needs the coverage provider the partition has configured to be installed, or `jest --coverage`. Both report branch coverage. **Where the runner has coverage integration but the provider is missing, install the provider into the audit's own copy of the target and re-run there** - that is the only route observed to produce a true number, and it is not an install into the target, which stays barred. Vitest names the missing package outright (`MISSING DEPENDENCY Cannot find dependency '@vitest/coverage-v8'`), and **pass `--coverage.reportOnFailure` when you do**: it defaults to false, so a target whose suite has one failing test - the ordinary state of a foreign repository at an arbitrary ref - produces no coverage report at all while otherwise looking like a run that worked. **Never reach for `c8` around a Vitest command.** `c8` wraps an arbitrary command and is fetchable from the partition's own registry, and it cannot see coverage produced inside Vitest's worker processes, nor the TypeScript Vitest transforms in memory: run against a real target it reported **96.35% statements and 69.56% branches over three files** - two configs and one script - where the provider-based measurement of the same tree was **8.05% and 5.86%** over 339 files. That is a false clean in exactly the format this check asks for, and it is worse than `no-evidence`. Pointed at the source tree with `--all --src`, the same `c8` run reports 0% of 47,306 statements, which is honest and still measures nothing. Its plain form remains the measurement for a runner `c8` can actually observe - one whose tests run in the process it wrapped - and there `c8`'s reporter defaults to `text`, Istanbul's per-file table of `% Stmts`, `% Branch`, `% Funcs`, `% Lines` and `Uncovered Line #s`, exactly the evidence this check wants. Confirm the file list in that table is the source tree before reading any number off it. Add `--check-coverage --branches <n>` only where the project already states a branch floor of its own and you are checking the suite against it: it is a gate rather than a measurement, exiting nonzero when coverage falls short, so reaching for it here would make you invent an `<n>` the project never asked for and would turn a measurement that worked into something that looks like `tool-failed`. Capture the missing line/branch ranges per module, as in Python.

**Both** - every command above runs the target's own suite to produce that report, which is the `target-execution` grant; without it the reach measurement itself is `no-evidence (not-permitted)`, and what remains is the exclusion-config reading described in this record's `ungranted_note`.

## Fix

**Cover the gap with a real test:** exercise the actual branch/behavior and assert on the observable outcome, not on a value the test recomputed. Prefer testing the deterministic core directly; mock only true I/O edges.

## Review lens

**Coverage genuineness** - is the reported gain from real exercised behavior, not from importing code or asserting nothing? Branch coverage, not just line.
