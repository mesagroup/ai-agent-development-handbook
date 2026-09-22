---
id: ci/deploy-safety
domain: ci
locality: global
handbook: []
handbook_note: >-
  The handbook names deploy/deployment in exactly one sentence
  (lifecycle.md's DORA-measures sentence, "commit-to-deploy" and
  "deployment frequency"), and that sentence is about measuring
  deployment frequency as a throughput metric, not about the safety
  controls around a deploy - a different question about the same word,
  not a near miss. Nothing in Part 9's pipeline checklist or elsewhere
  asks for an environment-approval gate, a rollback path, or
  required-status enforcement specifically on the release workflow; that
  section stops at pinning, permissions and trigger safety for the
  pipeline in general and never singles out the deploy/release step.
routes:
  - lang: any
    kind: procedure
    note: >-
      Needs reading - no tool in this domain's evidence pass reaches the
      release path; read the deploy/release workflow(s) for an
      environment-protection/approval requirement, a documented rollback
      procedure, and required-status enforcement gating the release step.
---

# Deploy safety

Deploys without environment protection/approval, no rollback path, missing required-status enforcement before release.

## Severity

**Important** - a deploy with no environment approval.

