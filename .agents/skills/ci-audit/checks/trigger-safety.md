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
      workflow it follows can be started by a pull request, directly or
      through another `workflow_run`, since otherwise the triggering run's code
      is not the pull request's. Each tell below is a property, and the
      spellings given for it are examples of that property rather than a list
      to match: a spelling not named here that has the property is the tell.

      For each workflow with such a trigger, read whether a job executes code
      the pull request's author controls, wherever that code lands. It gets
      there by any step that fetches it - an `actions/checkout` whose `ref:`
      or `repository:` names the head sha or ref, the merge commit, a
      `refs/pull/<n>/` ref or the head repository, a `git fetch`, `git clone`
      or `gh pr checkout` of it, a package install from the head repository,
      or under `workflow_run` the triggering run's `head_sha`, `head_branch` or
      `head_repository` - and it executes in any step that runs what was
      fetched: a script, a local action, an install step whose hooks it
      supplies, or a build tool reading its configuration from it. A reusable
      workflow the job calls and a composite action it uses are read through,
      as part of the job and under this trigger, with the caller's `with:`
      inputs and passed secrets bound into them, so a ref or a secret that
      arrives as an input is the same tell as one written in place.

      For each such job, read what is in its effective scope, which is
      everything the job can reach rather than only what it names. A secret is
      in scope when the job's own definition, under any key and in any step,
      or the workflow-level `env:` it inherits, reads the `secrets` context in
      any form - `secrets.NAME`, `secrets['NAME']`, `toJSON(secrets)`, the last
      putting every secret in scope - and, for a called workflow, when the
      call passes it, by an explicit `secrets:` mapping or by `secrets:
      inherit`. `secrets.GITHUB_TOKEN` is not one of those: it is the job's
      token, spelled like a secret, and it is judged by its permission like
      `github.token`. The job's token is always in scope, and its permission is
      the job's `permissions:` block, else the workflow's top-level block, else
      the repository's default token permissions, which the workflow does not
      show; a called workflow's block can only narrow what its caller grants.

      The verdict is taken in this order, and the first that applies is the
      row's. First, the gate. A gate is a condition that, in every run in which
      the job executes the pull request's code, only someone with write access
      to the repository can have made true, and made true for that exact
      code. Judge a condition against that sentence rather than against its
      spelling, whatever level it sits at: a condition an outside author can
      satisfy, or can outlast - an approval that stays in place while new
      commits arrive, an identity the author can borrow or grow into, a
      prerequisite job the executing job can run without - is no gate, and
      nor is an approval of a run that then fetches a ref the author can still
      move. Code that executes only after a gate the workflow shows is `ok`. A
      gate whose force the workflow cannot show, an `environment:` whose
      required reviewers are a repository setting, is `warn`, naming that
      setting and whoever administers the repository as its holder, where the
      code it releases is fixed at the moment of approval, and no gate where
      it is not. Second, what the clone cannot resolve: where
      what the clone holds neither makes the job the band below nor clears it,
      because the answer turns on something it does not hold - a workflow or
      action from another repository, a ref computed at run time, or the
      repository's default token permissions where the workflow sets none and
      no secret is in scope - the row is `warn`, naming what would settle it
      and who holds that, never `ok`. Third, the band: a job that executes the pull
      request's code before any gate, with a secret in scope or a token whose
      effective permission includes a write, is the Critical band's
      `violation`. Otherwise the row is `ok`: a job whose explicit block grants
      no write scope, `permissions: {}` included, and which has no secret in
      scope, and a workflow with no such trigger or no job executing the pull
      request's code, every `on:` block having been read. A row records the
      workflow and job, the trigger, the step that fetches the code at its
      `file:line`, the gate if any, and each secret and the permission in
      scope with where it comes from.
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
