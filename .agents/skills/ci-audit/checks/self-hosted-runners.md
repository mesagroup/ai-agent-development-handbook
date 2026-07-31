---
id: ci/self-hosted-runners
domain: ci
locality: global
optin: true
handbook: []
handbook_note: >-
  The word "runner" appears in the handbook exactly twice, both in
  codebase-structure.md and agent-harness.md, and both name the shared
  agent-runner class the core tier exposes - a homonym, not a near miss of
  a CI concept. Nothing anywhere distinguishes hosted from self-hosted
  execution, and Part 9's pipeline checklist covers the token, the action
  pins and the trigger, never the machine the job actually runs on.
---

# Self-hosted-runner hardening

If the project uses self-hosted runners, audit runner isolation, ephemerality, and exposure to untrusted PRs - ask the user; skip for hosted-runner-only projects.

## Tooling fallback

Needs reading - no scanner covers self-hosted-runner configuration; read the runner's registration, whether it is ephemeral (recycled per job) or long-lived, and whether a workflow that checks out untrusted PR code can schedule onto it.
