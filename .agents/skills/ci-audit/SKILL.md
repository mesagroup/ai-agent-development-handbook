---
name: ci-audit
description: "Audit a project's CI/CD pipelines (GitHub Actions and similar): workflow correctness, required quality gates actually being enforced, action pinning and supply-chain risk, least-privilege token permissions and secret handling, caching/matrix efficiency, and deploy safety. Use before relying on CI as a merge gate, after adding or changing workflows, when a pipeline is slow/flaky/over-privileged, or when the user asks to audit CI/CD or pipeline security. Works on any project with a pipeline. Runs on the audit-core engine."
---

# CI/CD Audit (pipelines, gates, pipeline security)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR), the `## Running a route` contract that turns this skill's records into commands, and the cross-cutting rules. The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory. This skill supplies the pipeline lens. It cross-links two neighbors: **`security-audit`** (a sibling in the audit-skills program) owns first-party application-code weaknesses, and **[deps-audit](../deps-audit/SKILL.md)** owns third-party package CVEs/licenses - this skill owns the *pipeline itself* (its secrets, permissions, and the actions it pulls in).

**Core principle:** CI is both a quality gate and a privileged execution environment holding your secrets. The audit answers two questions at once - *does the pipeline actually enforce what everyone assumes it enforces?* (a gate that never runs is worse than no gate, because people trust it) and *what could a malicious PR or a compromised action do with the pipeline's permissions and secrets?* Verify both against the real workflow files and run history, not the badge.

**Announce:** "I'm using the ci-audit skill (on the audit-core engine) to audit the CI/CD pipelines."

**Not for:** application-code security (use `security-audit`), dependency CVEs in the app's own requirements (use `deps-audit`), or writing a brand-new pipeline from scratch (that's authoring, not auditing - though the findings inform it).

**Subject:** the pipeline definitions and the platform they run on. Establish first:

- **Platform + workflow set** - detect the CI system (`.github/workflows/*.yml` for GitHub Actions; `.gitlab-ci.yml`; `.circleci/`; Jenkinsfile; etc.) and enumerate every workflow, its triggers, and its jobs.
- **What must be gated** - the checks the team treats as required (lint, typecheck, tests, and any project-specific quality gate) and the branch-protection expectation behind them.
- **Trust + privilege model** - which workflows run on `pull_request` vs the more dangerous `pull_request_target` / `workflow_run`, which have access to secrets, and which can deploy or write to the repo.

**The partition here is one workflow file**, so most checks are `local` to a workflow - one read-only agent per workflow, mapping its triggers, permissions, secrets, and actions. Two checks are not: `ci/gate-enforcement` compares what the contributor guide claims CI enforces against what the workflows plus branch protection actually enforce, which needs every workflow at once and repo settings, and `ci/deploy-safety` reasons about the release path across workflows - both are `global`. The two opt-in checks - `ci/branch-protection` and `ci/self-hosted-runners` - are global as well, and are loaded like any other.

**Detect** what the platform offers and what the project already uses: for GitHub Actions, `actionlint` (workflow correctness + shellcheck of `run:` blocks), `zizmor` (GHA security auditor - trigger safety, injection, permissions, unpinned actions), `pinact`/`ratchet` (action-pin checking), and the GitHub API/CLI (`gh`) for branch-protection and run history. For other platforms, use their native linter (`glab ci lint`, `circleci config validate`) plus manual review. Prefer a tool the project already runs; fall back to careful manual reading of every workflow.

Status per row: **ok / warn / violation**. Suppressions (an intentionally broad permission, an action deliberately tracked by tag) must be explicit and recorded with a reason - never silently dropped.

Fixes here **change the pipeline definition itself**, so the domain gate is unusual: **the changed workflow must parse and run green on a real trigger** - validate with `actionlint` and, where feasible, a test run on a branch/PR before relying on it. Route through the normal review gate. **Highest-leverage fix:** wire `actionlint` + `zizmor` into the pipeline (and pre-commit) so workflow regressions and new insecure patterns are caught automatically. Docs-only output: the findings report and any update to the contributor guide's "what CI enforces" section so the claim matches reality.

**Pipeline-secret history scan** - hand off to `security/secret-history` for secrets that may have been committed to workflow files; note the handoff.
