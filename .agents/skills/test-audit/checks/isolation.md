---
id: test/isolation
domain: test
locality: local
evidence: >-
  The duration reported per test is the timing evidence, and the calls a test
  makes are the real-I/O evidence. The timing pass runs the target's own suite,
  so without the `target-execution` grant the duration evidence is missing: the
  timing axis is `no-evidence (not-permitted)`, the I/O axis is still answered
  by the untiered route below, and the check reports as half-answered, its
  evidence naming both, never as `ok` because the I/O reading was clean, in
  either language.
handbook:
  - implementation-disciplines/tdd-b
routes:
  - lang: python
    kind: command
    answers: timing
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
    answers: timing
    tool: vitest
    argv: [vitest, run, "--reporter=json", "--outputFile", "<report-path>"]
    in_env: true
    needs: target-execution
    applies_when: >-
      The partition's own runner is Vitest.
    note: >-
      Run the partition's own runner in run mode and read each test's
      `duration` from its JSON report: `run` rather than bare `vitest`, which
      enters watch mode on an interactive terminal and never returns a
      completed timing pass, and `--reporter=json` because the duration is a
      field of every test's result there, under `testResults[].assertionResults[]`,
      where the default reporter prints only file and test totals and the
      suite's duration, and the only slow mark any reporter prints is a
      colour that captured output does not carry. `<report-path>` is a file
      outside the target's tree, and `--outputFile` is not optional: without
      it the JSON reporter writes `.vitest/json/output.json` under the
      project, which the no-writes invariant bars. A row is a test whose
      `duration` exceeds the partition's own `slowTestThreshold`, read from
      `vitest.config.*` or, where there is none, from the `test` block of
      `vite.config.*`, and 300ms, Vitest's documented default, where neither
      sets one. An `isolate: false` or non-default `pool` in that config tells
      you the suite has been opted out of per-file isolation deliberately
      rather than by accident.
  - lang: typescript
    kind: procedure
    answers: timing
    tool: jest
    in_env: true
    needs: target-execution
    applies_when: >-
      The partition's own runner is Jest.
    note: >-
      The partition's own `jest` test command, in run mode, as on the Vitest
      route above, with the duration read per test from what the run reports
      and cut at the partition's own Jest `slowTestThreshold`. That command is the one the
      partition declares rather than one written here, so there is no argv to
      declare and a `kind: command` route would have to invent one.
  - lang: any
    kind: procedure
    answers: io
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
