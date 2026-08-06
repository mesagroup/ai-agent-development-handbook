---
id: test/new-code-coverage
domain: test
locality: global
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [diff-cover]
needs:
  target-execution: [diff-cover]
---

# TDD adherence / new-code coverage

Does new or changed deterministic code ship with tests? Modules that grew without their tests growing; a coverage regression introduced by recent work (measure coverage on the diff, not just globally).

## Severity

**Critical** - a coverage regression that drops below a required floor.

**Important** - new/changed code that shipped without tests.

## Tooling fallback

**Diff coverage:** `diff-cover coverage.xml --compare-branch=origin/main` to find coverage the current work added or dropped - this is the TDD-adherence evidence. `diff-cover` itself only reads `coverage.xml` and a git diff, so given that artifact it needs nothing from the target. Producing `coverage.xml` is what needs the `target-execution` grant, since generating it runs the suite. Where the target's own CI publishes `coverage.xml` as a build artifact, fetch that and run `diff-cover` against it without the grant - the one route to an answer on a read-only clone; where no such artifact exists, this check is `no-evidence (not-permitted)` without the grant.

## Fix

**Cover the gap with a real test:** exercise the actual branch/behavior and assert on the observable outcome, not on a value the test recomputed. Prefer testing the deterministic core directly; mock only true I/O edges.

## Review lens

**Coverage genuineness** - is the reported gain from real exercised behavior, not from importing code or asserting nothing? Branch coverage, not just line.

**Scope vs plan** - every planned Critical/Important gap actually addressed; nothing silently dropped or papered over with a weak assert.
