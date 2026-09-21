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
routes:
  - lang: python
    kind: command
    tool: ruff
    argv: [ruff, check, "--select", D]
    note: >-
      Docstring presence per module and public symbol, reported per file so the
      row names what is undocumented rather than a percentage over the tree. `ruff
      check --select D` selects the pydocstyle rules ruff carries; the record
      names the `D` rules and this is the command that turns them on.
  - lang: python
    kind: command
    tool: pydocstyle
    argv: [pydocstyle]
    note: >-
      Docstring presence per module and public symbol, reported per file so the
      row names what is undocumented rather than a percentage over the tree.
      `pydocstyle` defaults to the working directory, so the bare name is
      runnable.
  - lang: python
    kind: command
    tool: interrogate
    argv: [interrogate]
    note: >-
      Docstring presence per module and public symbol, reported per file so the
      row names what is undocumented rather than a percentage over the tree.
      `interrogate` defaults to the working directory too and reports a coverage
      percentage beside the per-file list; record the list, and record the
      percentage at the run rather than predicting it.
  - lang: any
    kind: procedure
    note: >-
      With none of the three present, an AST or grep sweep over module and
      public-symbol definitions answers the same question in either language: a
      definition with no docstring node is the finding, and the sweep needs
      nothing installed and nothing resolved.
---

# Docstring coverage

Which public modules/classes/functions lack docstrings. Report per package.

## Fix

**CI note:** docstring fixes **touch code**, so they are **not** docs-only - they need the normal lint/typecheck/test gate and may need the code-review gate.
