---
id: docs/docstring-staleness
domain: docs
locality: local
optin: true
handbook: []
handbook_note: >-
  This check's detection is contradiction - a docstring that is actively
  wrong (wrong parameter names, a removed return type, a "raises" clause the
  code no longer raises, an example that would fail) - while the handbook's
  ask is broader: keep the docstring "updated whenever the purpose or
  interface changes". A docstring that is merely incomplete after a change
  (a new parameter added but not yet mentioned) contradicts nothing and so
  passes this check while still violating the handbook's timeliness ask,
  which is the near-miss the matrix's mapping rule forbids.
---

# Docstring staleness

Docstrings that contradict the code (wrong parameter names, removed return types, "raises X" the code no longer raises, examples that would fail). Needs reading - use source-mapping subagents as in the prose audit.

## Fix

Docstring fixes touch code, so they are **not** docs-only - they need the normal lint/typecheck/test gate and may need the code-review gate.
