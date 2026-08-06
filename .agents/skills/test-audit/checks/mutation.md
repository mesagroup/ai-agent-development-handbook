---
id: test/mutation
domain: test
locality: local
optin: true
handbook:
  - implementation-disciplines/tdd-b
tooling:
  python: [mutmut, cosmic-ray]
needs:
  target-execution: [mutmut, cosmic-ray]
---

# Mutation testing (effectiveness)

Mutation score: do the tests actually kill injected faults? Run `mutmut` / `cosmic-ray` on the highest-risk modules to measure whether tests kill injected faults (the truest test-effectiveness signal, but slow) - enable via argument or ask the user; default off for a quick pass, recommend on for a scorer/parser-heavy core.

## Tooling fallback

**Mutation score:** `mutmut run` / `cosmic-ray` re-run the target's own suite once per injected mutant, so this check needs the `target-execution` grant, and it is the most expensive tool in this family to run - many suite executions rather than one. Without the grant it is `no-evidence (not-permitted)`. Where the grant exists, scope the run to the highest-risk module rather than the whole suite; a full-suite mutation run multiplies an already-slow tool by every module in the tree.
