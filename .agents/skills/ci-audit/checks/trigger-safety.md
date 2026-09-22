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
      obtains it whatever the partition's language. The record prescribes no
      reading where the tool cannot be obtained.
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
