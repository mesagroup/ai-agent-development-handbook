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
      `workflow_run` trigger; a `workflow_run` trigger counts only where the
      workflow it follows can run on a `pull_request` event, since otherwise
      the triggering run's code is not the pull request's. For each workflow
      with such a trigger, read whether a job checks out the pull request's
      code - an `actions/checkout` step whose `ref:` or `repository:` names it
      (the head sha or head ref, the `refs/pull/<n>/merge` ref, or the head
      repository; under `workflow_run`, the triggering run's `head_sha`,
      `head_branch` or `head_repository`), or a `git fetch` or `gh pr
      checkout` of it - and then runs anything from that checkout: a script,
      a local or composite action, an install step whose hooks the checkout
      supplies, or a build tool reading its configuration from it. A job that
      calls a reusable workflow is read through the call: the called
      workflow's jobs are judged as this workflow's jobs, under this trigger.

      For each such job, read what is in its effective scope, which is
      everything the job can reach rather than only what it names. A secret is
      in scope when a `secrets.` expression appears anywhere in the job's own
      definition, under any key and in any step, or in the workflow-level
      `env:` the job inherits; for a called workflow, the secrets are the ones
      the call passes, by an explicit `secrets:` mapping or by `secrets:
      inherit`. `secrets.GITHUB_TOKEN` is not one of those: it is the job's
      token, spelled like a secret, and it is judged by its permission like
      `github.token`. The job's token is always in scope, and its permission is the
      job's `permissions:` block, else the workflow's top-level block, else the
      repository's default token permissions, which the workflow does not
      show; a called workflow's block can only narrow what its caller grants.

      The verdict is about code that runs before any gate, and it follows
      from those readings. A job that runs the pull request's code with a
      secret in scope, or with a token whose effective permission includes a
      write, is the Critical band's `violation`. The same job whose permission
      comes from the repository default, with no secret in scope, is the
      Critical band too, but the clone cannot read that default, so it is
      `warn` naming the repository's default workflow permissions setting as
      what would settle it and whoever administers the repository as its
      holder, never clean. A gate the workflow shows - a job condition that
      excludes pull requests from outside the repository - puts the job
      after the gate and it is `ok`; a gate the workflow only names, an
      `environment:` whose required reviewers are a repository setting, is
      `warn` naming that setting and the same holder. A job whose explicit
      block grants no write scope, `permissions: {}` included, and which has
      no secret in scope is `ok`, and so is a workflow with no such trigger or
      no job running the pull request's code, every `on:` block having been
      read. A row records the workflow and job, the trigger, the checkout step
      at its `file:line`, and each secret and the permission in scope with
      where it comes from.
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
