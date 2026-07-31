---
id: docs/docstring-standard
domain: docs
locality: local
optin: true
handbook: []
handbook_note: >-
  This check tests conformance to "the project's convention", a
  locally-defined bar that can be weaker than the handbook's own fixed ask
  ("what it does and how to use it"). A docstring that satisfies a thin
  local convention would pass this check while still falling short of the
  handbook's fuller bar, which is the near-miss the matrix's mapping rule
  forbids.
---

# Docstring standard

Each module/`__init__` and public symbol has a docstring describing what it does and how to use it, per the project's convention.

## Fix

Docstring fixes touch code, so they are **not** docs-only - they need the normal lint/typecheck/test gate and may need the code-review gate.
