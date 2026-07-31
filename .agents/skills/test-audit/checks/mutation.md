---
id: test/mutation
domain: test
locality: local
optin: true
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [mutmut, cosmic-ray]
---

# Mutation testing (effectiveness)

Mutation score: do the tests actually kill injected faults? Run `mutmut` / `cosmic-ray` on the highest-risk modules to measure whether tests kill injected faults (the truest test-effectiveness signal, but slow) - enable via argument or ask the user; default off for a quick pass, recommend on for a scorer/parser-heavy core.
