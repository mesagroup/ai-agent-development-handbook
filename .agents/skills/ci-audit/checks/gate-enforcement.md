---
id: ci/gate-enforcement
domain: ci
locality: global
handbook:
  - lifecycle/make-the-standard-executable-and-audit-periodically-a
  - implementation-disciplines/ci-and-static-analysis-a
  - implementation-disciplines/when-to-add-an-end-to-end-agent-quality-gate
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-b
  - evaluation/grow-the-eval-into-a-gate
  - documentation/audit-docs-like-a-test-suite-b
  - security-supply-chain/turn-every-fix-into-a-gate
routes:
  - lang: any
    kind: procedure
    answers: workflows
    applies_when: >-
      The CI platform is GitHub Actions, whose workflow syntax this reading names.
    note: >-
      Read each workflow's `on:`, `if:`, path filters, and
      `continue-on-error`, and read the contributor guide (CLAUDE.md / README)
      for what CI is *claimed* to enforce, then diff that against reality.
      This half alone says which checks run and when; whether a check that
      runs is *required* is the protection route's, and a gate that is green
      but not required does not block a merge.
  - lang: any
    kind: command
    tool: gh
    answers: protection
    argv: [gh, api, "repos/{owner}/{repo}/branches/{branch}/protection"]
    then: [gh, run, list]
    own_runner: true
    applies_when: >-
      The repository is hosted on GitHub and its CI is GitHub Actions: `gh api`
      reads the host's protection rules and `gh run list` its Actions runs, so
      on a GitHub repository built elsewhere the second command lists nothing.
    note: >-
      Check the repo's **branch protection** (`gh api
      repos/{owner}/{repo}/branches/{branch}/protection` or the settings UI)
      to confirm the intended checks are actually *required*. A gate that is
      green but not required does not block a merge - verify against branch
      protection, not the workflow alone. Also skim recent run history
      (`gh run list`) for chronically-skipped or always-failing-but-ignored
      jobs. `gh` is a standalone binary in no language registry, installed in
      advance.
---

# Gate enforcement

Are the intended quality gates actually run and *required*? A workflow that is skippable via path filters, only runs on a schedule, is `continue-on-error`, or isn't in branch protection is a gate in name only. Mismatch between "what CLAUDE.md/README says CI enforces" and "what the workflows enforce."

## Severity

**Critical** - a claimed merge gate that is not actually required, so unreviewed/broken code can merge green.

## Fix

**Close the gate gap:** add the check to branch-protection required-status, remove the path filter or `continue-on-error` that let it skip.

## Review lens

**Gate reality** - is each "gate is enforced" claim backed by branch-protection evidence, not just a green workflow? Does the fix actually make the check required and blocking?

**No pipeline regression** - nothing was silently disabled to make CI pass.
