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
---

# Property-based testing gap

Identify pure functions that would benefit from `hypothesis` property tests over example-based ones - ask the user.
