---
id: docs/docstring-coverage
domain: docs
locality: local
optin: true
handbook: []
handbook_note: >-
  The handbook's living-docs clause asks for a docstring that "says what it
  does and how to use it" - a content-quality bar - but this check's
  detection (`ruff` `D` rules / `pydocstyle` / `interrogate` if present, else
  an AST/grep sweep) only tests whether a docstring exists at all. A
  one-word placeholder docstring passes this check's coverage bar while
  still violating the clause's quality bar, which is exactly the near-miss
  the matrix's mapping rule forbids - the quality half is
  `docs/docstring-standard`'s to reach, not this check's.
tooling:
  python: [ruff, pydocstyle, interrogate]
---

# Docstring coverage

Which public modules/classes/functions lack docstrings. Report per package.

## Tooling fallback

`ruff` `D` rules / `pydocstyle` / `interrogate` if present, else an AST/grep sweep.

## Fix

Docstring fixes touch code, so they are **not** docs-only - they need the normal lint/typecheck/test gate and may need the code-review gate.
