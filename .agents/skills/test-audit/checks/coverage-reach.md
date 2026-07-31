---
id: test/coverage-reach
domain: test
locality: local
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [pytest-cov, coverage.py]
---

# Coverage reach

Line and (crucially) **branch** coverage per module; uncovered load-bearing logic; error/exception paths never exercised. Raw percentage is context, not the finding - an uncovered branch in a scorer is.

## Severity

**Critical** - load-bearing deterministic logic (a scorer's math, an adjudicator's id-mapping, a parser, a security check) with **no** effective test.

**Important** - an untested error/branch path in important code.

**Minor** - a moderately-low-coverage-but-low-risk module.

## Tooling fallback

**Coverage (with branches):** `pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage run -m pytest` + `coverage report --show-missing`). Branch coverage is the signal; capture the missing line/branch ranges per module as the evidence pointer.

## Fix

**Cover the gap with a real test:** exercise the actual branch/behavior and assert on the observable outcome, not on a value the test recomputed. Prefer testing the deterministic core directly; mock only true I/O edges.

## Review lens

Is the reported gain from real exercised behavior, not from importing code or asserting nothing? Branch coverage, not just line.
