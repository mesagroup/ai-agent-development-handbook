---
id: test/isolation
domain: test
locality: local
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [pytest-timeout]
  typescript: [vitest, jest]
needs:
  target-execution: [pytest-timeout, vitest, jest]
ungranted_note: >-
  Reading test source for calls that hit the network, the filesystem or a database
  answers the real-I/O axis with nothing installed, in either language. What the
  project configured is readable in the same way: a `testTimeout` raised well above its
  default (5000ms in jest), `isolate: false` or a non-default `pool` in
  `vitest.config.*`, and a `slowTestThreshold` above its 300ms default each say the
  suite has tests needing more than an isolated unit test should. The timing pass runs
  the target's own suite, so without the grant the duration evidence is missing and this
  check is answered on the I/O axis rather than `no-evidence` as a whole, in either
  language.
---

# Isolation & speed

Unit tests doing real I/O, missing markers (integration masquerading as unit), pathologically slow tests that discourage running the suite.

## Severity

**Minor** - a slow test, a missing marker, a stylistic test-hygiene issue.

## Tooling fallback

**Python** - `pytest --durations=25` for the slowest tests; check unit tests for real I/O.

**TypeScript** - the partition's own runner reports a duration per test; vitest additionally marks anything past `slowTestThreshold`, which defaults to 300ms, and an `isolate: false` or non-default `pool` in its config tells you the suite has been opted out of per-file isolation deliberately rather than by accident. Check unit tests for real I/O the same way.

## Fix

Isolate or mark real-I/O tests.
