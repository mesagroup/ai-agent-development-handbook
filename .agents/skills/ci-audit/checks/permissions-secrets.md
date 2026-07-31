---
id: ci/permissions-secrets
domain: ci
locality: local
handbook:
  - security-supply-chain/treat-the-pipeline-as-a-privileged-environment
tooling:
  any: [zizmor]
---

# Permissions / secrets

Over-broad `permissions` (default or `write-all` where read is enough); secrets exposed to steps that run untrusted code; secrets echoed to logs; long-lived cloud credentials where OIDC/short-lived would do.

## Severity

**Critical** - a secret exposed to untrusted code or leaked to logs.

**Important** - over-broad `write-all` permissions where read suffices; long-lived cloud credentials where OIDC is available.

## Tooling fallback

`zizmor <workflow>` for trigger/injection/permission/pinning findings; capture the rule id + `file:line`.

Read the top-level and per-job `permissions:` and every `secrets.` reference; confirm least privilege and that no secret is reachable from an untrusted-code step.

## Fix

Set top-level `permissions:` to least privilege (`contents: read`) and widen per-job only as needed.

**Replace long-lived secrets** with OIDC / short-lived credentials where the platform supports it.

## Review lens

**Pipeline-security correctness** - is each trigger/permission/injection finding a genuine attacker path, and does the fix remove it (not just move the secret to another reachable step)?

**Least privilege preserved** - permission reductions didn't break a job that genuinely needed the write scope.
