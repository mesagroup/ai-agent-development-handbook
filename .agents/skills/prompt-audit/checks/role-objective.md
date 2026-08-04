---
id: prompt/role-objective
domain: prompt
locality: local
handbook:
  - implementation-disciplines/prompt-and-sop-engineering-a
---

# Role, objective & task framing

The prompt establishes who the model is, what it is trying to accomplish, and the scope/limits of the task, so "done" and "out of scope" are legible. A prompt that never states its objective forces the model to guess it.

## Severity

**Important** - no role/objective, so the task must be inferred.

## Tooling fallback

**Well-specified-prompt read:** work the Tier A principles against the text - is there a role/objective and a scope.

## Fix

**Specify the missing role/objective:** add the missing role/objective/scope.

## Review lens

**Well-specified** - the edit actually improved specification - a real role/objective where it was missing.
