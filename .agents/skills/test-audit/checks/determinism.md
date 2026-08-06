---
id: test/determinism
domain: test
locality: local
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [pytest-randomly, pytest-rerunfailures]
needs:
  target-execution: [pytest-randomly, pytest-rerunfailures]
ungranted_note: >-
  Grepping tests for `time.time()`, `datetime.now()`, `random.` without a seed, and
  live network calls answers the non-determinism axis with nothing installed. The
  randomized-order and repeat-run passes run the target's own suite and do not survive
  a withheld grant, so order-dependence specifically goes unmeasured. Ruff is not a
  substitute for the grep, though it looks like one: `DTZ005` asks whether a
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

**Flakiness:** run the suite in randomized order (`pytest-randomly` randomizes automatically once installed; use `--randomly-seed=<n>` to reproduce a failing order) and, for suspected flakies, repeat runs; flag order-dependence and non-determinism. Grep tests for `time.time()`, `datetime.now()`, `random.` without a seed, and live network calls. The randomized-order and repeat-run passes both run the target's own suite, which needs the `target-execution` grant; without it, they are `no-evidence (not-permitted)` and only the grep pass answers.

## Fix

**De-flake:** inject the clock/seed/randomness as a fixture, remove order dependence and shared mutable state.

## Review lens

**Flakiness avoidance** - new tests are order-independent and don't reintroduce clock/random/network flakiness.
