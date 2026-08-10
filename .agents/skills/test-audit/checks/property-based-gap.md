---
id: test/property-based-gap
domain: test
locality: local
optin: true
handbook: []
handbook_note: >-
  The handbook's TDD clause asks for real assertions over tautologies, branch
  and diff coverage, and deterministic tests, but states no preference
  between example-based and property-based test style; identifying where
  property-based tests would strengthen the suite is this check's own opt-in
  scope, not a clause the handbook states.
tooling:
  python: [hypothesis]
  typescript: [fast-check]
---

# Property-based testing gap

Identify pure functions that would benefit from property-based tests over example-based ones - ask the user.

## Tooling fallback

**Python** - `hypothesis`. **TypeScript** - `fast-check`. Both are libraries imported inside the partition's existing tests rather than runners of their own - fast-check's README documents integration with ava, jasmine, jest, mocha and tape rather than a runner of its own - so neither needs the suite run to answer this check: the gap is found by reading the pure functions and the tests covering them, and judging where a property would say more than a handful of examples. Prefer whichever the partition already depends on. Where neither is present the absence is itself the finding, so name the functions that would benefit rather than prescribing a library.
