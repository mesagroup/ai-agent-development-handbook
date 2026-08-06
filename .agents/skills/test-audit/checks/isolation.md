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

**Speed/isolation:** `pytest --durations=25` for the slowest tests; check unit tests for real I/O. The `--durations` pass runs the target's own suite, which needs the `target-execution` grant; without it, that pass alone is `no-evidence (not-permitted)`, and the real-I/O half is still answered by reading test source for calls that hit the network, the filesystem or a database. So a withheld grant leaves this check answered on the I/O axis with the timing evidence missing, not `no-evidence` as a whole.

## Fix

Isolate or mark real-I/O tests.
