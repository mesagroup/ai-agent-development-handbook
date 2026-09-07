---
id: test/determinism
domain: test
locality: local
evidence: >-
  A finding flags order-dependence and non-determinism. The randomized-order
  and repeat-run passes run the target's own suite and do not survive a
  withheld grant, so order-dependence specifically goes unmeasured in either
  language and what remains is the grep the untiered route below carries.
handbook:
  - implementation-disciplines/tdd-b
routes:
  - lang: python
    kind: command
    tool: pytest-randomly
    argv: [pytest]
    in_env: true
    needs: target-execution
    note: >-
      Runs the suite in randomized order. `pytest-randomly` randomizes the
      order as soon as it is installed, so the command is `pytest` itself.
  - lang: python
    kind: command
    tool: pytest-randomly
    argv: [pytest, "--randomly-seed=<n>"]
    disposition: alternative
    in_env: true
    needs: target-execution
    note: >-
      Re-run a failing order with `pytest --randomly-seed=<n>`, where `<n>` is
      the seed the run being reproduced reported. Offered rather than run,
      because there is no failing order to re-run until the route above has
      produced one.
  - lang: python
    kind: procedure
    tool: pytest-rerunfailures
    in_env: true
    needs: target-execution
    note: >-
      For suspected flakies, repeat runs. This route asks for repeat runs and
      names no flag, so the plugin's own `--reruns` is nowhere in the
      prescription and there is no argv to declare; a `kind: command` route
      would have to invent one. `in_env` is set even though this route
      prescribes nothing to run: it is a pytest plugin, resolved into the
      materialized environment rather than fetched standalone, and the version
      probe calls the launcher for every tool regardless of `argv`, so without
      the flag the probe resolves a bare one-shot interpreter with the plugin
      never installed, on every partition and grant.
  - lang: typescript
    kind: command
    tool: vitest
    argv: [vitest, run, "--sequence.shuffle", "--sequence.seed=<n>"]
    needs: target-execution
    applies_when: >-
      The partition's own runner is Vitest.
    note: >-
      `vitest run --sequence.shuffle --sequence.seed=<n>` randomizes order
      reproducibly - `run`, not bare `vitest`, which enters watch mode on an
      interactive terminal and only falls back to a single run in CI or a
      non-interactive one - and `retry` or `repeats` re-runs tests to expose
      flakiness.
  - lang: typescript
    kind: command
    tool: jest
    argv: [jest, "--randomize", "--seed", "<n>"]
    needs: target-execution
    applies_when: >-
      The partition's own runner is Jest.
    note: >-
      `jest --randomize --seed <n>` shuffles order within a file, and is
      supported only on the default `jest-circus` runner, so a project on a
      custom runner has no randomize flag at all and the untiered grep route
      below carries this check on its own.
  - lang: any
    kind: procedure
    note: >-
      Grepping tests for non-deterministic inputs answers that axis with
      nothing installed, in either language, and so is what a withheld grant
      leaves: `time.time()`, `datetime.now()`, `random.` without a seed and
      live network calls in Python; `Date.now()`, a `new Date()` with no fixed
      argument, `Math.random()` with no seeded generator, and live `fetch` or
      HTTP-client calls in TypeScript. Read each hit: a seeded generator is not
      a flake, and neither is a timestamp the test pins. What the project
      already asked for is readable too: a `retry` or `repeats` setting, or a
      `sequence.shuffle` already enabled in `vitest.config.*` or in the `test`
      block of `vite.config.*` - Vitest looks for `vitest.config.*` first and
      `vite.config.*` second, so a project with no `vitest.config.*` keeps
      these settings in its Vite config and a grep naming only the former
      reports nothing configured - says the project knows its own suite is
      order- or timing-sensitive. Ruff is not a substitute for the Python grep,
      though it looks like one: `DTZ005` asks whether a `datetime.now()` is
      timezone-aware rather than whether it is deterministic, so it stays
      silent on `datetime.now(tz=...)`, which is exactly as non-deterministic;
      and `S311` flags `random.` as cryptographically weak whether or not a
      seed was set on the line above, so it fires on the deterministic case.
---

# Determinism / flakiness

Tests that depend on ordering, wall-clock time, randomness, network, or shared mutable state; tests that pass/fail non-deterministically.

## Severity

**Important** - a flaky test that erodes CI trust.

## Fix

**De-flake:** inject the clock/seed/randomness as a fixture, remove order dependence and shared mutable state.

## Review lens

**Flakiness avoidance** - new tests are order-independent and don't reintroduce clock/random/network flakiness.
