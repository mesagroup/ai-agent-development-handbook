---
id: test/determinism
domain: test
locality: local
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [pytest-randomly, pytest-rerunfailures]
---

# Determinism / flakiness

Tests that depend on ordering, wall-clock time, randomness, network, or shared mutable state; tests that pass/fail non-deterministically.

## Severity

**Important** - a flaky test that erodes CI trust.

## Tooling fallback

**Flakiness:** run the suite in randomized order (`pytest-randomly` randomizes automatically once installed; use `--randomly-seed=<n>` to reproduce a failing order) and, for suspected flakies, repeat runs; flag order-dependence and non-determinism. Grep tests for `time.time()`, `datetime.now()`, `random.` without a seed, and live network calls.

## Fix

**De-flake:** inject the clock/seed/randomness as a fixture, remove order dependence and shared mutable state.

## Review lens

**Flakiness avoidance** - new tests are order-independent and don't reintroduce clock/random/network flakiness.
