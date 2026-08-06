---
id: test/isolation
domain: test
locality: local
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [pytest-timeout]
needs:
  target-execution: [pytest-timeout]
---

# Isolation & speed

Unit tests doing real I/O, missing markers (integration masquerading as unit), pathologically slow tests that discourage running the suite.

## Severity

**Minor** - a slow test, a missing marker, a stylistic test-hygiene issue.

## Tooling fallback

**Speed/isolation:** `pytest --durations=25` for the slowest tests; check unit tests for real I/O. `--durations` runs the target's own suite, which needs the `target-execution` grant; without it, this check is `no-evidence (not-permitted)` and falls back to reading test source for real I/O calls, with no timing evidence.

## Fix

Isolate or mark real-I/O tests.
