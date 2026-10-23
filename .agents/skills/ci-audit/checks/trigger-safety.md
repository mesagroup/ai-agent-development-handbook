---
id: ci/trigger-safety
domain: ci
locality: global
handbook:
  - security-supply-chain/treat-the-pipeline-as-a-privileged-environment
routes:
  - lang: any
    kind: command
    tool: zizmor
    registry: pypi
    argv: [zizmor, "<workflows>", "<local-actions>"]
    applies_when: >-
      The CI platform is GitHub Actions, whose workflow and action definitions are what the tool reads.
    alone_insufficient: >-
      A `dangerous-triggers` hit is a candidate, not the verdict: whether the
      job's code runs before a gate, and what is in its scope, are the reading
      route's to decide, so a zizmor row reads the tool-less route before it
      is the check's answer, and a clean zizmor run beside an unread workflow
      is not this check answered.
    note: >-
      `zizmor <workflows> <local-actions>` for trigger/injection/permission/pinning
      findings, as one invocation whose operands are every workflow file this
      agent holds and the definition file, `action.yml` or `action.yaml`, of
      every local action those workflows use, each file once and the workflows
      alone where they use none. A local action is one a `uses:` step names by
      a workspace-relative `./` path or by GitHub's self-repository `$/` path,
      wherever in the tree it lives, and the local actions those use in turn.
      A step naming this repository by its slug, `<owner>/<repo>/<path>@<ref>`,
      is a remote action rather than a local one, because it fetches the version
      at that ref rather than the running commit, so the clone's copy is not
      what runs. Never pass an action's directory: a directory operand collects
      every workflow and action file beneath it, so a root action, `uses: ./`
      or `uses: $/`, would make it the whole tree, and a file named twice
      reports its findings twice. Capture the rule id + `file:line`. A step's
      `./` action path, unlike a `$/` one or a reusable workflow's `./` path,
      resolves against the job's workspace, so where a step checks code out to
      another `path:`, or checks out the pull request's code, the file scanned
      is the clone's copy and not necessarily what the job ran, which the
      reading route settles. A remote composite action's own steps can name a
      `./` path too, which resolves against the caller's workspace and so runs
      a file of this repository, but no workflow here names that file, so the
      operands above never include it: a clean scan says nothing about it, and
      the reading route, which reads through composite actions, is what
      covers it. Measured with zizmor 1.31.1 on a
      tree planting a template injection in a workflow and in two composite
      actions it uses: a workflow operand alone scans the workflow and not the
      actions; `zizmor .github` scans `.github/actions/` and misses an action
      elsewhere; `zizmor .` scans every action definition the tree's
      `.gitignore` does not exclude, a vendored one or one no workflow uses
      included; the explicit operands scan exactly the three files, with one
      action named by `./` and the other by `$/`. A PyPI
      package, so `uvx zizmor`
      obtains it whatever the partition's language. Where it cannot be
      obtained, the reading route answers the same question.
  - lang: any
    kind: procedure
    applies_when: >-
      The CI platform is GitHub Actions, whose workflow syntax this reading names.
    note: >-
      Read every workflow's `on:` block for a `pull_request_target` or `workflow_run` trigger; a `workflow_run` trigger counts only where the workflow it follows can be started by a pull request - by an event whose name starts with `pull_request`, `pull_request_target` included - directly or through another `workflow_run`, since otherwise the triggering run's code is not the pull request's. The workflows it follows are the ones its `workflows:` filter names: glob patterns matched against each workflow's name, which is its `name:`, and which GitHub shows as the workflow's file path where it declares none, so read a pattern against that path too; where which workflows a pattern matches cannot be settled from the clone, the trigger is something the clone cannot resolve. A workflow runs under the triggers its own `on:` names and under every trigger that any workflow in the repository calling it runs under, read up through each caller in turn whatever else that caller's `on:` names, because a called workflow runs as part of its caller's run. A caller in another repository is judged in that repository's audit, so a workflow called here is read under its callers here. A workflow whose `on:` names `workflow_call` and that nothing in the repository calls runs, besides the runs its other triggers start, in the runs its `workflow_call` stands for, whose triggers are unknown because its callers are outside the clone; those are judged here as unknown rather than left to another audit, since otherwise no audit here reads its content, and every workflow below it in a call chain runs in them too, as well as under its own callers'. Every run is judged by its own trigger, so a trigger such a workflow names beside `workflow_call` is read like any other, and only the runs its `workflow_call` stands for are unknown. This reading covers every workflow that runs under such a trigger, and the pull request's code fetched in a run whose triggers are unknown, since such a trigger may be among them. In such a run, a fetch whose ref or repository comes from an input or is computed from the event is read as a fetch of the pull request's code, because what binds it is the unknown caller.

      For each such workflow and run, read whether a job fetches the pull request's code and executes it, and what is in the effective scope of each run in which it executes that code. Both are judged by the definitions `ci/permissions-secrets` states: untrusted code and each way a job fetches it, a ref an artifact or output names included, `actions/checkout`'s guard and when it refuses a fetch, and a run's effective scope, with when its token is read-only or holds a write and how the runs that share a way combine. This reading owns one way untrusted code reaches a job: the pull request's code fetched and executed under these two triggers, or in a run whose triggers are unknown, as above. Every other way, in the same job or another - an artifact's or output's content executed, or a fetch under any other known trigger - is that record's row, because each way has its own fix.

      The verdict is taken in this order, and the first that applies is the row's. First, a run whose effective scope holds no secret and whose token is read-only, as that record defines both, has nothing to expose and is `ok`, whatever else the clone cannot see about the code. Second, the gate. A gate is a condition that, in every run in which the job executes the pull request's code, only someone with write access to the repository can have made true, and made true for that exact code. Judge a condition against that sentence rather than against its spelling, whatever level it sits at: a condition an outside author can satisfy, or can outlast - an approval that stays in place while new commits arrive, an identity the author can borrow or grow into, a prerequisite job the executing job can run without - is no gate, and nor is an approval of a run that then fetches a ref the author can still move. Code that executes only after a gate the workflow shows is `ok`. A gate whose force the workflow cannot show, an `environment:` whose required reviewers are a repository setting, is `warn`, naming that setting and whoever administers the repository as its holder, where the code it releases is fixed at the moment of approval, and no gate where it is not. Third, the band: a job that executes the pull request's code before any gate, with a secret in the run's effective scope or a token that holds a write for that run, is the Critical band's `violation`. Fourth, what the clone cannot resolve: where what the clone holds neither makes the job the band above nor clears it, because the answer turns on something it does not hold - a workflow or action from another repository, a ref computed at run time, the triggers, inputs and passed secrets of a run whose triggers are unknown, as above, or the repository's default token permissions where no block settles the token's permission and no secret is in the run's effective scope, which in a run whose triggers are unknown are the levels above the workflow and the default they rest on, its callers' - the row is `warn`, naming what would settle it and who holds that, never `ok`. Otherwise the row is `ok`, as is a workflow that runs under no such trigger or in which no job executes the pull request's code, every `on:` block having been read. A reusable workflow is read through as part of each job that calls it, under that caller's trigger, as `ci/permissions-secrets` says, so for a fetch inside it the job a row records is the job at the top of its call chain, in the workflow whose own trigger the run is under, with each called location down to the fetch at its `file:line` as well; in a run whose triggers are unknown, the row records the job of the workflow at the top of its chain, the one nothing in the repository calls, and the run's triggers, inputs and passed secrets are the part the clone cannot resolve. A row records the workflow and job, the trigger, the step that fetches the code at its `file:line`, the gate if any, and each secret and the permission in scope with where it comes from.
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
