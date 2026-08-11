---
id: test/new-code-coverage
domain: test
locality: global
handbook:
  - implementation-disciplines/tdd-b
tooling:
  any: [diff-cover]
---

# TDD adherence / new-code coverage

Does new or changed deterministic code ship with tests? Modules that grew without their tests growing; a coverage regression introduced by recent work (measure coverage on the diff, not just globally).

## Severity

**Critical** - a coverage regression that drops below a required floor.

**Important** - new/changed code that shipped without tests.

## Tooling fallback

**Diff coverage:** `diff-cover <report> --compare-branch=origin/main`, where `<report>` is the target's own coverage report - `coverage.xml` where the runner writes Cobertura, `coverage/lcov.info` where it writes LCov - to find coverage the current work added or dropped - this is the TDD-adherence evidence. **The tool needs nothing from the target**, which is why it carries no `needs:` tier: it reads a coverage report and a git diff, and given that artifact it answers on a read-only clone under no grant at all. What needs a grant is *producing* the artifact, because generating a coverage report runs the target's own suite, which is `target-execution`. So look for a published one first, **and search for it under both names**: where the target's CI already publishes a coverage report as a build artifact - `coverage.xml` from a Cobertura reporter, `lcov.info` from an LCov one - fetch that and run `diff-cover` against it, a complete answer with no grant and the reason this record must not be gated behind one. Searching only for `coverage.xml` is how this check reports `no-evidence` on a target that published everything it needed, and it goes wrong most often on a TypeScript partition, because LCov is the format both of that partition's runners document a reporter for. Where no such artifact exists, generate one under the `target-execution` grant against the reconstructed tree; where neither the artifact nor the grant is available, this check is `no-evidence (not-permitted)`, never a clean result. Both TypeScript runners can produce an input it accepts: `diff-cover`'s own documentation takes "Cobertura, Clover or JaCoCo XML format, or LCov format", and `lcov` is a documented reporter for `vitest` (`coverage.reporter`) and for `jest` (`coverageReporters`, which accepts any istanbul reporter). That reporter is Istanbul's, and Istanbul's `lcov` is a composite that writes its LCov data to `lcov.info` in the coverage output directory beside an HTML report in `lcov-report/`, so `lcov.info` is the name to search the target's artifacts for. `diff-cover` is itself a Python-registry package, published on PyPI under that name, so run it with `uvx diff-cover` or `pipx run diff-cover` whatever the partition's language is, and do not reach for the partition's own one-shot runner: an npm package named `diff-cover` does exist, an independent third-party TypeScript port with working `diff-cover` and `diff-quality` binaries, so `npx diff-cover` does not fail at all - it runs a different implementation, whose flags and defaults nothing here has verified, and prints a plausible diff-coverage number with no sign that the tool was substituted.

## Fix

**Cover the gap with a real test:** exercise the actual branch/behavior and assert on the observable outcome, not on a value the test recomputed. Prefer testing the deterministic core directly; mock only true I/O edges.

## Review lens

**Coverage genuineness** - is the reported gain from real exercised behavior, not from importing code or asserting nothing? Branch coverage, not just line.

**Scope vs plan** - every planned Critical/Important gap actually addressed; nothing silently dropped or papered over with a weak assert.
