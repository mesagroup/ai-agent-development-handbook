---
id: test/mutation
domain: test
locality: local
optin: true
evidence: >-
  Every tool these routes name re-runs the target's own suite once per injected
  mutant, so this check needs the `target-execution` grant, and it is the most
  expensive tool in this family to run - many suite executions rather than one.
  Without the grant it is `no-evidence (not-permitted)`. Where the grant exists,
  scope the run to the highest-risk module rather than the whole suite; a
  full-suite mutation run multiplies an already-slow tool by every module in the
  tree.
handbook:
  - implementation-disciplines/tdd-b
answers_ungranted: none
routes:
  - lang: python
    kind: command
    tool: mutmut
    argv: [mutmut, run]
    in_env: true
    needs: target-execution
    note: >-
      A non-zero exit from bare `mutmut run` is never itself a findings signal,
      at least as of 3.7.0: every `exit(1)` reachable from the `run` command
      sits in setup or collection - stats collection, test collection, the
      clean-tests baseline, a source-layout check - all before the mutation loop
      begins, and that loop tallies survivors and killed counts and returns
      without ever calling `sys.exit`. Read the tally in the printed stats or
      with the `mutmut results` route below, never the exit code - a `run` that
      exits non-zero has failed before testing a single mutant, not found one
      that survived. A test suite carrying module-level state that accumulates
      across a single process can fail `mutmut run` at exactly that clean-tests
      baseline: the baseline re-runs the suite in the same process mutmut itself
      is driving, so a test asserting on state a prior test in that process
      already populated sees the accumulated state rather than a fresh one, even
      though the same suite passes cleanly run stand-alone - reported as
      `Failed to run clean test` with zero mutants tested, not as a suite
      defect.
  - lang: python
    kind: command
    tool: mutmut
    argv: [mutmut, results]
    disposition: alternative
    in_env: true
    needs: target-execution
    note: >-
      Where the tally is read rather than the exit code, alongside the stats the
      `mutmut run` route above prints.
  - lang: python
    kind: procedure
    tool: cosmic-ray
    in_env: true
    needs: target-execution
    note: >-
      Named without a command line, so there is no argv to declare and a
      `kind: command` route would have to invent one: `cosmic-ray` drives a
      session from a TOML config, and that config is the input, so writing one
      to make the tool run would manufacture the input rather than transcribe
      the record. `in_env` is set because it is true of the tool - driving a
      session re-runs the target's suite in the target's own environment, as
      `mutmut` does - and not because this route needs it: with no argv there
      is no command for a launcher to prefix, and the only thing the flag
      still reaches is the version probe, which resolves `cosmic-ray`'s own
      console script and obtains the tool with the flag or without it. So do
      not read the flag here as saying the tool is unreachable when the grant
      is withheld. That reasoning does hold for the pytest plugins, whose
      probes import the package rather than running a script of their own, and
      it is theirs rather than a general property of `in_env`.
  - lang: typescript
    kind: procedure
    tool: "@stryker-mutator/core"
    needs: target-execution
    note: >-
      `@stryker-mutator/core`, whose CLI is `stryker run`, drives the
      partition's own runner through a matching plugin
      (`@stryker-mutator/vitest-runner`, `@stryker-mutator/jest-runner` or
      `@stryker-mutator/mocha-runner`, selected by `testRunner` and `plugins`
      in `stryker.config.json`). Core on its own runs nothing, so on a partition
      whose runner has no matching plugin the tool cannot be obtained and this
      check is `no-evidence (tool-unavailable)` rather than clean. Not
      `not-applicable`: that status says the check has no lens in this
      partition's languages, and this record offers one, so using it here would
      report a tool the audit could not get hold of as a question nobody could
      have asked. **Name the package rather than the bin wherever the tool has
      to be fetched**, because this package's bin name is not its package name.
      Where the partition already carries Stryker among its own dev
      dependencies, `npx stryker run` resolves that local binary and is
      StrykerJS's own documented invocation; where it does not, the same string
      is a fetch of a package named `stryker`, and the npm registry carries
      one - Stryker's own pre-1.0 line, published by the same maintainers as the
      scoped package, `latest` `0.35.1`, still declaring a `stryker` bin, and
      deprecated with a message that names `@stryker-mutator/core` as its
      replacement. So on a partition with no local install `npx stryker run`
      resolves and executes an unmaintained 0.x rather than failing cleanly.
      Because the publisher is the same, this is a stale genuine tool rather
      than unvetted code in the audit environment, so the worst case is a wrong
      mutation score rather than a poisoned run, and a wrong answer is the
      harder of the two to notice. That is not the shape it took when tried: on
      node 24 the 0.x resolved, executed and died, a loud failure rather than a
      quiet wrong number. Do not rely on either shape - a version this old fails
      differently on each runtime it is dragged onto, which is the reason for
      naming the package rather than the bin, not the specific way it broke on
      one node. Fetching it with a one-shot runner does not work, and the reason
      is worth knowing before trying: `@stryker-mutator/core` dynamically
      imports `typescript` from its own sandbox, and on npm 11 a
      `--package typescript` alongside it went uninstalled - the sandbox
      recorded three requested packages and installed two - so the run died on
      `ERR_MODULE_NOT_FOUND: Cannot find package 'typescript'` whether or not
      the compiler was named, and whether or not it was pinned. **Install
      Stryker and its matching runner plugin into a copy of the target this
      check owns and run there**, which is the same move `test/coverage-reach`
      needs for a missing coverage provider and is not an install into the
      target - nor into the shared reconstructed tree a sweep hands every
      domain, for the reason `audit-core` gives: these are packages the target
      does not declare, so they belong in a copy this check owns rather than in
      the graph the other domains are reading: that produced a real mutation
      score - 52.34% over one scoped module, 56 mutants killed and 37 survived,
      in 68 seconds. That install-and-run is prescribed as an operation and not
      as a command line, so there is no argv to declare here.
  - lang: typescript
    kind: command
    tool: "@stryker-mutator/core"
    argv: [npx, "--package", "@stryker-mutator/core", "--package", "@stryker-mutator/<runner>-runner", "--", stryker, run]
    argv_by_partition:
      pnpm: [pnpm, "--package=@stryker-mutator/core", "--package=@stryker-mutator/<runner>-runner", dlx, stryker, run]
      yarn: [yarn, dlx, "-p", "@stryker-mutator/core", "-p", "@stryker-mutator/<runner>-runner", stryker, run]
    disposition: alternative
    needs: target-execution
    note: >-
      Where you do reach for a one-shot runner anyway, name the packages -
      `npx --package @stryker-mutator/core --package @stryker-mutator/<runner>-runner -- stryker run`,
      naming the plugin that matches the inventory's test runner; on a pnpm
      partition the flags precede `dlx` -
      `pnpm --package=@stryker-mutator/core --package=@stryker-mutator/<runner>-runner dlx stryker run` -
      because `pnpm dlx --package=...` reads the flag as a package spec and
      fails outright on pnpm 9, and delivered no co-package at all on pnpm 11
      when tried against another tool, and on a yarn one as
      `yarn dlx -p @stryker-mutator/core -p @stryker-mutator/<runner>-runner stryker run`.
      All three name the package rather than leaning on the command name, which
      is the whole point: a bare `dlx stryker` resolves the unscoped 0.x exactly
      as a bare `npx stryker` does, so writing "the `dlx` equivalent" and
      leaving the reader to supply it hands back the hazard the package option
      exists to close.
---

# Mutation testing (effectiveness)

Mutation score: do the tests actually kill injected faults? Run `mutmut` / `cosmic-ray` on the highest-risk modules to measure whether tests kill injected faults (the truest test-effectiveness signal, but slow) - enable via argument or ask the user; default off for a quick pass, recommend on for a scorer/parser-heavy core.
