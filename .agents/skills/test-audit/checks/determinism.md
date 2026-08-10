---
id: test/determinism
domain: test
locality: local
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [pytest-randomly, pytest-rerunfailures]
  typescript: [vitest, jest]
needs:
  target-execution: [pytest-randomly, pytest-rerunfailures, vitest, jest]
ungranted_note: >-
  Grepping tests for non-deterministic inputs answers that axis with nothing
  installed, in either language: `time.time()`, `datetime.now()`, `random.` without a
  seed and live network calls in Python; `Date.now()`, a `new Date()` with no fixed
  argument, `Math.random()` with no seeded generator, and live `fetch` or HTTP-client
  calls in TypeScript. What the project already asked for is readable too: a `retry` or
  `repeats` setting, or a `sequence.shuffle` already enabled in `vitest.config.*`, says
  the project knows its own suite is order- or timing-sensitive. The randomized-order
  and repeat-run passes run the target's own suite and do not survive a withheld grant,
  so order-dependence specifically goes unmeasured in either language. Ruff is not a
  substitute for the Python grep, though it looks like one: `DTZ005` asks whether a
  `datetime.now()` is timezone-aware rather than whether it is deterministic, so it
  stays silent on `datetime.now(tz=...)`, which is exactly as non-deterministic; and
  `S311` flags `random.` as cryptographically weak whether or not a seed was set on the
  line above, so it fires on the deterministic case.
---

# Determinism / flakiness

Tests that depend on ordering, wall-clock time, randomness, network, or shared mutable state; tests that pass/fail non-deterministically.

## Severity

**Important** - a flaky test that erodes CI trust.

## Tooling fallback

**Python** - run the suite in randomized order (`pytest-randomly` randomizes automatically once installed; use `--randomly-seed=<n>` to reproduce a failing order) and, for suspected flakies, repeat runs; flag order-dependence and non-determinism.

**TypeScript** - use the partition's own runner. `vitest --sequence.shuffle --sequence.seed=<n>` randomizes order reproducibly, and `retry` or `repeats` re-runs tests to expose flakiness. `jest --randomize --seed <n>` shuffles order within a file, and is supported only on the default `jest-circus` runner, so a project on a custom runner has no randomize flag at all and the grep below carries this check on its own.

**Both** - grep the tests for the non-deterministic constructs named in this record's `ungranted_note` and read each hit; a seeded generator is not a flake, and neither is a timestamp the test pins.

## Fix

**De-flake:** inject the clock/seed/randomness as a fixture, remove order dependence and shared mutable state.

## Review lens

**Flakiness avoidance** - new tests are order-independent and don't reintroduce clock/random/network flakiness.
