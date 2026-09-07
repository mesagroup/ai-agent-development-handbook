---
id: test/isolation
domain: test
locality: local
evidence: >-
  The duration reported per test is the timing evidence, and the calls a test
  makes are the real-I/O evidence. The timing pass runs the target's own suite,
  so without the `target-execution` grant the duration evidence is missing and
  this check is answered on the I/O axis the untiered route below carries
  rather than `no-evidence` as a whole, in either language.
handbook:
  - implementation-disciplines/tdd-b
routes:
  - lang: python
    kind: command
    tool: pytest-timeout
    argv: [pytest, "--durations=25"]
    in_env: true
    needs: target-execution
    note: >-
      `pytest --durations=25` for the slowest tests. The route pairs that
      command with `pytest-timeout`, and the pairing is a convenience rather
      than a claim that one exercises the other: `--durations` is core pytest
      and runs whether or not the plugin is installed, while the plugin's own
      flag is `--timeout`, which this record does not prescribe. So the
      durations table is the evidence here and the plugin is what a caller
      reaches for to turn a slow test into a failing one - name the timeout
      yourself if you want that, because nothing above names it for you.
  - lang: typescript
    kind: command
    tool: vitest
    argv: [vitest, run]
    needs: target-execution
    applies_when: >-
      The partition's own runner is Vitest.
    note: >-
      Run the partition's own runner in run mode and read the duration it
      reports per test: `vitest run`, with `run` rather than bare `vitest`,
      which enters watch mode on an interactive terminal and never returns a
      completed timing pass. Vitest additionally marks anything past
      `slowTestThreshold`, which defaults to 300ms, and an `isolate: false` or
      non-default `pool` in its config tells you the suite has been opted out
      of per-file isolation deliberately rather than by accident.
  - lang: typescript
    kind: procedure
    tool: jest
    needs: target-execution
    applies_when: >-
      The partition's own runner is Jest.
    note: >-
      The partition's own `jest` test command, in run mode, with the duration
      read per test as on the Vitest route above. That command is the one the
      partition declares rather than one written here, so there is no argv to
      declare and a `kind: command` route would have to invent one.
  - lang: any
    kind: procedure
    note: >-
      Reading test source for calls that hit the network, the filesystem or a
      database answers the real-I/O axis with nothing installed, in either
      language - check unit tests for real I/O this way whichever timing route
      above applies, and whether or not it ran. What the project configured is
      readable in the same way: a `testTimeout` raised well above its default
      (5000ms in jest), `isolate: false` or a non-default `pool` in
      `vitest.config.*` or in the `test` block of `vite.config.*` - Vitest
      looks for `vitest.config.*` first and `vite.config.*` second, so a
      project with no `vitest.config.*` keeps these settings in its Vite config
      and a grep naming only the former reports nothing configured - and a
      `slowTestThreshold` above its 300ms default each say the suite has tests
      needing more than an isolated unit test should.
---

# Isolation & speed

Unit tests doing real I/O, missing markers (integration masquerading as unit), pathologically slow tests that discourage running the suite.

## Severity

**Minor** - a slow test, a missing marker, a stylistic test-hygiene issue.

## Fix

Isolate or mark real-I/O tests.
