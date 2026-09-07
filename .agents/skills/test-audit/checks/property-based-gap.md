---
id: test/property-based-gap
domain: test
locality: local
optin: true
evidence: >-
  The evidence is the pure functions and the tests covering them, read
  together: neither library below needs the suite run to answer this check,
  because the gap is found by reading those functions and those tests and
  judging where a property would say more than a handful of examples. Prefer
  whichever library the partition already depends on. Where neither is present
  the absence is itself the finding, so name the functions that would benefit
  rather than prescribing a library.
handbook: []
handbook_note: >-
  The handbook's TDD clause asks for real assertions over tautologies, branch
  and diff coverage, and deterministic tests, but states no preference
  between example-based and property-based test style; identifying where
  property-based tests would strengthen the suite is this check's own opt-in
  scope, not a clause the handbook states.
routes:
  - lang: python
    kind: library
    tool: hypothesis
    note: >-
      `hypothesis`, a library imported inside the partition's existing tests
      rather than a runner of its own, so there is no command to declare and a
      `kind: command` route would have to invent one.
  - lang: typescript
    kind: library
    tool: fast-check
    note: >-
      `fast-check`, a library imported inside the partition's existing tests
      rather than a runner of its own - its README documents integration with
      ava, jasmine, jest, mocha and tape - so there is no command to declare
      here either.
---

# Property-based testing gap

Identify pure functions that would benefit from property-based tests over example-based ones - ask the user.
