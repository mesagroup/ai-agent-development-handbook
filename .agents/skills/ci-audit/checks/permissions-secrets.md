---
id: ci/permissions-secrets
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
      The record prescribes the reading as well as the scan: the `permissions:`
      blocks and every `secrets.` reference are read whatever the scanner
      reported, as the tool-less route says.
    note: >-
      `zizmor <workflow>` for trigger/injection/permission/pinning findings;
      capture the rule id + `file:line`. A PyPI package, so `uvx zizmor`
      obtains it whatever the partition's language.
  - lang: any
    kind: procedure
    note: >-
      Read the top-level and per-job `permissions:` and every `secrets.`
      reference; confirm least privilege and that no secret is reachable from
      an untrusted-code step.
---

# Permissions / secrets

Over-broad `permissions` (default or `write-all` where read is enough); secrets exposed to steps that run untrusted code; secrets echoed to logs; long-lived cloud credentials where OIDC/short-lived would do.

## Severity

**Critical** - a secret exposed to untrusted code or leaked to logs.

**Important** - over-broad `write-all` permissions where read suffices; long-lived cloud credentials where OIDC is available.

## Fix

Set top-level `permissions:` to least privilege (`contents: read`) and widen per-job only as needed.

**Replace long-lived secrets** with OIDC / short-lived credentials where the platform supports it.

## Review lens

**Pipeline-security correctness** - is each trigger/permission/injection finding a genuine attacker path, and does the fix remove it (not just move the secret to another reachable step)?

**Least privilege preserved** - permission reductions didn't break a job that genuinely needed the write scope.
