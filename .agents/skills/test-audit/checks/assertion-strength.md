---
id: test/assertion-strength
domain: test
locality: local
handbook:
  - implementation-disciplines/tdd-b
---

# Assertion strength

Tests that assert nothing, only assert "no exception raised," assert against a value the test itself computed the same way (tautology), or over-mock so the real unit never runs. These inflate coverage without catching regressions.

## Severity

**Critical** - load-bearing deterministic logic (a scorer's math, an adjudicator's id-mapping, a parser, a security check) covered only by a test that can't fail; a green suite that misses a class of bug because assertions are hollow.

**Important** - heavy over-mocking that means the unit under test never actually runs.

## Tooling fallback

**Assertion-strength review (the load-bearing step):** read the tests covering each high-risk module and judge whether an assertion would actually fail if the code regressed. A scanner can't do this - a subagent reading test → code pairs can. Flag no-op asserts, tautologies, and over-mocking with `file:line`.

## Fix

**Strengthen a weak test:** replace a no-op/tautological assert with one that would fail on a plausible regression; unwind over-mocking so the real unit executes.

## Review lens

Would each new/changed test actually fail if the code it covers regressed? (The single highest-value catch - reject tests that raise coverage without catching bugs.)
