---
id: ci/workflow-correctness
domain: ci
locality: local
handbook: []
handbook_note: >-
  The handbook's own gate-enforcement clause (implementation-disciplines.md,
  cited by `ci/gate-enforcement`) asks whether a check runs and is required
  in branch protection; it never asks whether the workflow file itself is
  well-formed. Invalid syntax, a shell-quoting bug, an untrusted expression
  interpolated into a `run:` block, or a masked exit code are a mechanical
  authoring-correctness question the handbook does not raise anywhere -
  Part 9's pipeline section covers trust, privilege and pinning, not the
  workflow's own well-formedness.
tooling:
  any: [actionlint]
---

# Correctness

Invalid workflow syntax, shell quoting bugs, misused expressions (`${{ }}` injection from untrusted context into a `run:` block), jobs that pass when they should fail (masked exit codes, `|| true`).

## Severity

**Critical** - an expression-injection sink from untrusted context into a shell step.

**Minor** - a cosmetic lint finding.

## Tooling fallback

`actionlint` (catches syntax, expression, and shell-quoting errors), or the platform's config validator.

## Fix

Make failures actually fail (drop `|| true`, propagate exit codes).

## Review lens

**No pipeline regression** - nothing was silently disabled to make CI pass.
