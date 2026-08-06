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
ungranted_note: >-
  Reading test source for calls that hit the network, the filesystem or a database
  answers the real-I/O axis with nothing installed. The `--durations` pass runs the
  target's own suite, so without the grant the timing evidence is missing and this
  check is answered on the I/O axis rather than `no-evidence` as a whole.
---

# Isolation & speed

Unit tests doing real I/O, missing markers (integration masquerading as unit), pathologically slow tests that discourage running the suite.

## Severity

**Minor** - a slow test, a missing marker, a stylistic test-hygiene issue.

## Tooling fallback

**Speed/isolation:** `pytest --durations=25` for the slowest tests; check unit tests for real I/O.

## Fix

Isolate or mark real-I/O tests.
