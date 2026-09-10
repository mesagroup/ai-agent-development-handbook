---
id: ci/workflow-correctness
domain: ci
locality: local
handbook: []
handbook_note: >-
  Two faults, neither of them raised by the handbook, and for different
  reasons. Well-formedness - invalid syntax, a shell-quoting bug, a masked
  exit code - is a mechanical authoring-correctness question the handbook
  does not ask anywhere: its own gate-enforcement clause
  (implementation-disciplines.md, cited by `ci/gate-enforcement`) asks
  whether a check runs and is required in branch protection, never whether
  the workflow file itself is well-formed. An untrusted expression
  interpolated into a `run:` block is not that; it is a security fault, and
  it is absent from the clause a reader would reach for.
  `security-supply-chain/treat-the-pipeline-as-a-privileged-environment`
  names four things - a read-only default token, actions pinned to a commit
  SHA, never running untrusted pull-request code with secrets in scope, and
  short-lived federated credentials - and interpolating attacker-controlled
  *data* into an otherwise trusted step is none of them. The third is
  untrusted *code*, which is `ci/trigger-safety`'s. So this check exceeds
  the handbook on technical grounds rather than on taste, which is what the
  empty list is for.
tooling:
  any: [actionlint, zizmor]
---

# Correctness

Invalid workflow syntax, shell quoting bugs, misused expressions (`${{ }}` injection from untrusted context into a `run:` block), jobs that pass when they should fail (masked exit codes, `|| true`).

## Severity

**Critical** - an expression-injection sink from untrusted context into a shell step.

**Important** - a masked exit code: the job reports green over a step that failed, so a gate the project believes in stops gating. Not an attacker path, and not cosmetic either.

**Minor** - a cosmetic lint finding.

## Tooling fallback

`actionlint` (catches syntax, expression, and shell-quoting errors), or the platform's config validator.

`zizmor <workflow>` for the injection half; capture the rule id + `file:line`. Both tools are needed and they answer different questions: `actionlint` type-checks an expression and shellchecks the `run:` block it lands in, which says nothing about whether the value interpolated there is attacker-controlled, and this skill's `**Detect**` list is where the split is stated. A run reaching for `actionlint` alone answers the syntax and quoting halves and reports nothing for the half this record calls Critical - a tool that ran and found nothing, which reads exactly like a clean workflow.

## Fix

**Bind untrusted context into `env:` rather than interpolating it into the shell:** put `env: BODY: ${{ github.event.issue.body }}` on the step and reference `"$BODY"` in the `run:` body, so the value reaches the script as an environment variable the shell reads rather than as text spliced into the script before the shell parses it. Where the action offers an input for the value, prefer that over shell interpolation entirely. **Quoting the interpolation is not the fix** - `"${{ github.event.issue.body }}"` is substituted into the script text first, so the quotes end up around whatever the attacker sent and inside whatever they closed.

**Make failures actually fail** (drop `|| true`, propagate exit codes).

## Review lens

**Pipeline-security correctness** - is each trigger/permission/injection finding a genuine attacker path, and does the fix remove it (not just move the secret to another reachable step)?

**No pipeline regression** - nothing was silently disabled to make CI pass.
