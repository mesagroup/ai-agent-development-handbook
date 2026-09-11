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
  untrusted *code*, which is `ci/trigger-safety`'s. The source-to-sink
  clause is the other candidate and is also not it: Part 9 divides its
  subject into three surfaces - first-party code, what you depend on, and
  the pipeline that builds you - and that clause is the first surface's, so
  a workflow's own `run:` block is outside it by the handbook's own
  division. So this check exceeds the handbook on technical grounds rather
  than on taste, which is what the empty list is for.
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

`zizmor <workflow>` for the injection half; capture the rule id + `file:line`. The two tools answer different questions rather than standing in for one another, and this skill's `**Detect**` list is where that split is stated: it gives `actionlint` workflow correctness and shellcheck of `run:` blocks, and gives `zizmor` injection. Shellchecking the block an expression lands in says nothing about whether the value interpolated there is attacker-controlled, so a run reaching for `actionlint` alone answers the syntax and quoting halves and reports nothing for the half this record calls Critical - a tool that ran and found nothing, which reads exactly like a clean workflow.

Where `zizmor` cannot be obtained the injection half is still answerable by reading, so it is not `no-evidence` - but the reading is wider than one grep, in both directions a narrow one goes wrong. **Search every position where a `${{ }}` value reaches a shell or a script**, not `run:` alone: a `run:` block, a `github-script` step's `script:`, and a `with:` input to a composite or container action, which are the positions `## Fix` already treats as sinks. A pass that greps `run:` reports clean on the other two while this record's own fix section says they are reachable. **Then read each hit for the property, not for membership of a list**: a context whose value an outsider can write without review. `github.event.issue.*` and `github.event.pull_request.*` - title as well as body - `github.event.comment.*`, `github.event.review.*`, `github.event.discussion.*`, `github.event.head_commit.message` and the messages under `github.event.commits.*`, `github.head_ref`, and `inputs.*` on a `workflow_dispatch` are the ones most often met. They are examples and not the set: GitHub's own script-injection guidance enumerates it and moves, so a reading pass that treats any list written here as closed reproduces the false-clean failure this fallback exists to avoid. Where a context is not on a list and you cannot say who can write it, that is a finding to report as unresolved rather than to drop. Say which half each row's evidence came from either way. A status that covers both halves when one tool ran is the failure the paragraph above describes, arriving by a different route.

## Fix

**Bind untrusted context into `env:` rather than interpolating it into the shell:** give the step an `env:` block mapping a name to the expression, `BODY` to `${{ github.event.issue.body }}`, and reference `"$BODY"` in the `run:` body, so the value reaches the script as an environment variable the shell reads rather than as text spliced into the script before the shell parses it. The reference is the step's shell's, not bash's everywhere - `$env:BODY` under `pwsh`, `os.environ["BODY"]` under `shell: python`, `process.env.BODY` in an `actions/github-script` `script:`. **Quoting the interpolation is not the fix** - `"${{ github.event.issue.body }}"` is substituted into the script text first, so the quotes end up around whatever the attacker sent and inside whatever they closed.

**An action input is a fix only where the action reads it from the environment.** A JavaScript action does, so passing the value as a `with:` input neutralizes it there. A composite action does not: its inputs arrive as `${{ inputs.* }}`, so a composite whose own `run:` interpolates one has moved the sink into another file rather than removed it, and a container action's `args:` is the same shape. Read the action before preferring its input - this is exactly the fix-that-moves-rather-than-removes case `## Review lens` asks about, so a finding closed this way and not read is one the lens is meant to reopen.

**A value written to a workflow command file needs a delimiter as well as the binding.** `echo "TITLE=$BODY" >> "$GITHUB_ENV"` satisfies the binding above and is still a sink: a newline in the value appends lines of the attacker's choosing to the file, which sets environment variables for every later step in the job. Write it as a heredoc under a delimiter the value cannot contain, and the same for `$GITHUB_OUTPUT` and `$GITHUB_PATH`.

**What the pattern covers.** An expression in a `run:` block, which is what the lead prose and the Critical tier name. The same binding carries to another position where a shell or a script reads the value, a `github-script` `script:` being the common one. An `if:` is not a shell at all, so the binding does not apply there and this record prescribes nothing for a finding in one - `zizmor` reports injection at positions this fix does not reach, and saying so is better than a pattern that looks general.

**Make failures actually fail** (drop `|| true`, propagate exit codes).

## Review lens

**Pipeline-security correctness** - is each trigger/permission/injection finding a genuine attacker path, and does the fix remove it (not just move the secret to another reachable step)?

**No pipeline regression** - nothing was silently disabled to make CI pass.
