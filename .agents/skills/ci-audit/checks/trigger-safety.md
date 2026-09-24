---
id: ci/trigger-safety
domain: ci
locality: local
handbook:
  - security-supply-chain/treat-the-pipeline-as-a-privileged-environment
routes:
  - lang: any
    kind: command
    tool: zizmor
    registry: pypi
    argv: [zizmor, "<workflow>"]
    applies_when: >-
      The CI platform is GitHub Actions, whose workflow and action definitions are what the tool reads.
    note: >-
      `zizmor <workflow>` for trigger/injection/permission/pinning findings;
      capture the rule id + `file:line`. A PyPI package, so `uvx zizmor`
      obtains it whatever the partition's language. Where it cannot be
      obtained, the reading route answers the same question.
  - lang: any
    kind: procedure
    applies_when: >-
      The CI platform is GitHub Actions, whose workflow syntax this reading names.
    note: >-
      Read every workflow's `on:` block for a `pull_request_target` or
      `workflow_run` trigger. For each workflow that has one, read whether a
      job checks out the pull request's code - an `actions/checkout` step whose
      `ref:` or `repository:` names it (the head sha or head ref, the
      `refs/pull/<n>/merge` ref, or the head repository; under `workflow_run`,
      the triggering run's `head_sha`, `head_branch` or `head_repository`), or a
      `git fetch` or `gh pr checkout` of it - and then runs anything from that
      checkout, and what the job holds while it does: every `secrets.`
      reference in the job or its steps, a `secrets: inherit` on a
      reusable-workflow call, and the `permissions:` it runs with, the
      workflow's top-level block applying where the job sets none. Where
      neither sets one, the repository's default token permissions apply,
      which the workflow does not show: record that as a default of unknown
      scope, never as read-only. The Critical band is a job doing both:
      running the pull request's code with a secret or a write permission in
      scope. A row records the workflow and job, the trigger, the checkout step
      at its `file:line`, and the secrets and permissions in scope; a trigger
      with no checkout of the pull request's code, or a checkout with no secret
      and no write permission in scope, is recorded as read and is not a
      finding.
---

# Trigger safety

Dangerous triggers: `pull_request_target` or `workflow_run` that checks out and runs untrusted PR code with secrets in scope; workflows that run untrusted code before an approval gate.

## Severity

**Critical** - a pipeline-takeover path: `pull_request_target`/`workflow_run` running untrusted PR code with secrets or write permissions.

## Fix

**Lock down triggers:** prefer `pull_request` over `pull_request_target`; when `pull_request_target` is unavoidable, do not check out+run PR code with secrets - split into a safe build + a gated, least-privilege follow-up.

## Review lens

**Pipeline-security correctness** - is each trigger/permission/injection finding a genuine attacker path, and does the fix remove it (not just move the secret to another reachable step)?

**No pipeline regression** - required jobs still run on the right events.
