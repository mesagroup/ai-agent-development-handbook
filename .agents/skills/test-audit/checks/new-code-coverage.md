---
id: test/new-code-coverage
domain: test
locality: global
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [diff-cover]
---

# TDD adherence / new-code coverage

Does new or changed deterministic code ship with tests? Modules that grew without their tests growing; a coverage regression introduced by recent work (measure coverage on the diff, not just globally).

## Severity

**Critical** - a coverage regression that drops below a required floor.

**Important** - new/changed code that shipped without tests.

## Tooling fallback

**Diff coverage:** `diff-cover coverage.xml --compare-branch=origin/main` to find coverage the current work added or dropped - this is the TDD-adherence evidence. **The tool needs nothing from the target**, which is why it carries no `needs:` tier: it reads a coverage XML and a git diff, and given that artifact it answers on a read-only clone under no grant at all. What needs a grant is *producing* the artifact, because generating `coverage.xml` runs the target's own suite, which is `target-execution`. So look for a published one first: where the target's CI already publishes `coverage.xml` as a build artifact, fetch that and run `diff-cover` against it - a complete answer with no grant, and the reason this record must not be gated behind one. Where no such artifact exists, generate it under the `target-execution` grant against the reconstructed tree; where neither the artifact nor the grant is available, this check is `no-evidence (not-permitted)`, never a clean result.

## Fix

**Cover the gap with a real test:** exercise the actual branch/behavior and assert on the observable outcome, not on a value the test recomputed. Prefer testing the deterministic core directly; mock only true I/O edges.

## Review lens

**Coverage genuineness** - is the reported gain from real exercised behavior, not from importing code or asserting nothing? Branch coverage, not just line.

**Scope vs plan** - every planned Critical/Important gap actually addressed; nothing silently dropped or papered over with a weak assert.
