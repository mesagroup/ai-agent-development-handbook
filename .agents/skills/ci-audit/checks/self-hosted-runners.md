---
id: ci/self-hosted-runners
domain: ci
locality: global
optin: true
handbook: []
handbook_note: >-
  The word "runner" appears in the handbook five times, in exactly two
  files: four in codebase-structure.md (its heading and body, naming the
  core tier's generic agent-Runner abstraction) and one in
  agent-harness.md ("an A/B runner", an eval-harness script). Neither
  file names a CI execution environment - a homonym, not a near miss.
  Nothing anywhere distinguishes hosted from self-hosted execution, and
  Part 9's pipeline checklist covers the token, the action pins and the
  trigger, never the machine the job actually runs on.
routes:
  - lang: any
    kind: procedure
    note: >-
      Needs reading - no scanner covers self-hosted-runner configuration; read
      the runner's registration, whether it is ephemeral (recycled per job) or
      long-lived, and whether a workflow that checks out untrusted PR code can
      schedule onto it.
---

# Self-hosted-runner hardening

If the project uses self-hosted runners, audit runner isolation, ephemerality, and exposure to untrusted PRs - ask the user; skip for hosted-runner-only projects.

