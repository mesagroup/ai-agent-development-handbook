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
    alone_insufficient: >-
      A `dangerous-triggers` hit is a candidate, not the verdict: whether the
      job's code runs before a gate, and what is in its scope, are the reading
      route's to decide, so a zizmor row reads the tool-less route before it
      is the check's answer, and a clean zizmor run beside an unread workflow
      is not this check answered.
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
      Read every workflow's `on:` block for a `pull_request_target` or `workflow_run` trigger; a `workflow_run` trigger counts only where the workflow it follows can be started by a pull request - by an event whose name starts with `pull_request`, `pull_request_target` included - directly or through another `workflow_run`, since otherwise the triggering run's code is not the pull request's.

      For each workflow with such a trigger, read whether a job fetches the pull request's code and executes it, and what is in the effective scope of each run in which it executes that code. Both are judged by the definitions `ci/permissions-secrets` states: untrusted code and each way a job fetches it, a ref an artifact or output names included, `actions/checkout`'s guard and when it refuses a fetch, and a run's effective scope, with when its token is read-only or holds a write and how the runs that share a way combine. This reading owns one way untrusted code reaches a job: the pull request's code fetched and executed under these two triggers. Every other way, in the same job or another - an artifact's or output's content executed, or a fetch under any other trigger - is that record's row, because each way has its own fix.

      The verdict is taken in this order, and the first that applies is the row's. First, a run whose effective scope holds no secret and whose token is read-only, as that record defines both, has nothing to expose and is `ok`, whatever else the clone cannot see about the code. Second, the gate. A gate is a condition that, in every run in which the job executes the pull request's code, only someone with write access to the repository can have made true, and made true for that exact code. Judge a condition against that sentence rather than against its spelling, whatever level it sits at: a condition an outside author can satisfy, or can outlast - an approval that stays in place while new commits arrive, an identity the author can borrow or grow into, a prerequisite job the executing job can run without - is no gate, and nor is an approval of a run that then fetches a ref the author can still move. Code that executes only after a gate the workflow shows is `ok`. A gate whose force the workflow cannot show, an `environment:` whose required reviewers are a repository setting, is `warn`, naming that setting and whoever administers the repository as its holder, where the code it releases is fixed at the moment of approval, and no gate where it is not. Third, the band: a job that executes the pull request's code before any gate, with a secret in the run's effective scope or a token that holds a write for that run, is the Critical band's `violation`. Fourth, what the clone cannot resolve: where what the clone holds neither makes the job the band above nor clears it, because the answer turns on something it does not hold - a workflow or action from another repository, a ref computed at run time, or the repository's default token permissions where no block settles the token's permission and no secret is in the run's effective scope - the row is `warn`, naming what would settle it and who holds that, never `ok`. Otherwise the row is `ok`, as is a workflow with no such trigger or no job executing the pull request's code, every `on:` block having been read. A row records the workflow and job, the trigger, the step that fetches the code at its `file:line`, the gate if any, and each secret and the permission in scope with where it comes from.
---

# Trigger safety

Dangerous triggers: `pull_request_target` or `workflow_run` that fetches and runs untrusted PR code with secrets or a write token in scope, before any approval gate.

## Severity

**Critical** - a pipeline-takeover path: `pull_request_target`/`workflow_run` running untrusted PR code with secrets or write permissions.

## Fix

**Lock down triggers:** prefer `pull_request` over `pull_request_target`; when `pull_request_target` is unavoidable, do not check out+run PR code with secrets - split into a safe build + a gated, least-privilege follow-up.

## Review lens

**Pipeline-security correctness** - is each trigger/permission/injection finding a genuine attacker path, and does the fix remove it (not just move the secret to another reachable step)?

**No pipeline regression** - required jobs still run on the right events.
