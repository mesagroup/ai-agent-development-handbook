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
tooling:
  any: [gh]
---

# Gate enforcement

Are the intended quality gates actually run and *required*? A workflow that is skippable via path filters, only runs on a schedule, is `continue-on-error`, or isn't in branch protection is a gate in name only. Mismatch between "what CLAUDE.md/README says CI enforces" and "what the workflows enforce."

## Severity

**Critical** - a claimed merge gate that is not actually required, so unreviewed/broken code can merge green.

## Tooling fallback

Read each workflow's `on:`, `if:`, path filters, and `continue-on-error`, then check the repo's **branch protection** (`gh api repos/{owner}/{repo}/branches/{branch}/protection` or the settings UI) to confirm the intended checks are actually *required*. A gate that is green but not required does not block a merge - verify against branch protection, not the workflow alone. Also skim recent run history (`gh run list`) for chronically-skipped or always-failing-but-ignored jobs.

Read the contributor guide (CLAUDE.md / README) for what CI is *claimed* to enforce, and diff that against reality.

## Fix

**Close the gate gap:** add the check to branch-protection required-status, remove the path filter or `continue-on-error` that let it skip.

## Review lens

**Gate reality** - is each "gate is enforced" claim backed by branch-protection evidence, not just a green workflow? Does the fix actually make the check required and blocking?

**No pipeline regression** - nothing was silently disabled to make CI pass.
