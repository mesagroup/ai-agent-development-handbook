---
name: ci-audit
description: "Audit a project's CI/CD pipelines (GitHub Actions and similar): workflow correctness, required quality gates actually being enforced, action pinning and supply-chain risk, least-privilege token permissions and secret handling, caching/matrix efficiency, and deploy safety. Use before relying on CI as a merge gate, after adding or changing workflows, when a pipeline is slow/flaky/over-privileged, or when the user asks to audit CI/CD or pipeline security. Works on any project with a pipeline. Runs on the audit-core engine."
---

# CI/CD Audit (pipelines, gates, pipeline security)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. This skill supplies the pipeline lens. It cross-links two neighbors: **[security-audit](../security-audit/SKILL.md)** owns first-party application-code weaknesses, and **[deps-audit](../deps-audit/SKILL.md)** owns third-party package CVEs/licenses — this skill owns the *pipeline itself* (its secrets, permissions, and the actions it pulls in).

**Core principle:** CI is both a quality gate and a privileged execution environment holding your secrets. The audit answers two questions at once — *does the pipeline actually enforce what everyone assumes it enforces?* (a gate that never runs is worse than no gate, because people trust it) and *what could a malicious PR or a compromised action do with the pipeline's permissions and secrets?* Verify both against the real workflow files and run history, not the badge.

**Announce:** "I'm using the ci-audit skill (on the audit-core engine) to audit the CI/CD pipelines."

**Bash rule:** never pass a line starting with `#` to the Bash tool (you or any subagent).

## When to use

- Before trusting CI as the merge gate ("green means safe"): confirm the gates are required and actually run on the paths that matter.
- After adding or restructuring workflows, or when a pipeline became slow, flaky, or over-privileged.
- When the pipeline handles secrets/deploys and you want to bound the blast radius of a malicious PR or a compromised third-party action.
- When the user asks to audit CI/CD, pipeline security, or release automation.

**Not for:** application-code security (use `security-audit`), dependency CVEs in the app's own requirements (use `deps-audit`), or writing a brand-new pipeline from scratch (that's authoring, not auditing — though the findings inform it).

## 1. Subject & scope

The pipeline definitions and the platform they run on. Establish first:

- **Platform + workflow set** — detect the CI system (`.github/workflows/*.yml` for GitHub Actions; `.gitlab-ci.yml`; `.circleci/`; Jenkinsfile; etc.) and enumerate every workflow, its triggers, and its jobs.
- **What must be gated** — the checks the team treats as required (lint, typecheck, tests, and any project-specific quality gate) and the branch-protection expectation behind them.
- **Trust + privilege model** — which workflows run on `pull_request` vs the more dangerous `pull_request_target` / `workflow_run`, which have access to secrets, and which can deploy or write to the repo.

Slice the parallel evidence pass **by workflow file** — one read-only agent per workflow — so each maps its triggers, permissions, secrets, and actions.

## 2. Dimensions (findings-matrix columns)

- **Gate enforcement** — are the intended quality gates actually run and *required*? A workflow that is skippable via path filters, only runs on a schedule, is `continue-on-error`, or isn't in branch protection is a gate in name only. Mismatch between "what CLAUDE.md/README says CI enforces" and "what the workflows enforce."
- **Trigger safety** — dangerous triggers: `pull_request_target` or `workflow_run` that checks out and runs untrusted PR code with secrets in scope; workflows that run untrusted code before an approval gate.
- **Permissions / secrets** — over-broad `permissions` (default or `write-all` where read is enough); secrets exposed to steps that run untrusted code; secrets echoed to logs; long-lived cloud credentials where OIDC/short-lived would do.
- **Action supply chain** — third-party actions pinned to a mutable tag/branch (`@v4`, `@main`) instead of a full commit SHA; unvetted/abandoned actions; actions from untrusted publishers.
- **Correctness** — invalid workflow syntax, shell quoting bugs, misused expressions (`${{ }}` injection from untrusted context into a `run:` block), jobs that pass when they should fail (masked exit codes, `|| true`).
- **Efficiency** — missing dependency caching, no concurrency cancellation for superseded runs, an over-broad matrix, redundant re-installs.
- **Deploy safety** — deploys without environment protection/approval, no rollback path, missing required-status enforcement before release.

## 3. Evidence sources & tooling

**Detect** what the platform offers and what the project already uses: for GitHub Actions, `actionlint` (workflow correctness + shellcheck of `run:` blocks), `zizmor` (GHA security auditor — trigger safety, injection, permissions, unpinned actions), `pinact`/`ratchet` (action-pin checking), and the GitHub API/CLI (`gh`) for branch-protection and run history. For other platforms, use their native linter (`gitlab-ci-lint`, `circleci config validate`) plus manual review. Prefer a tool the project already runs; fall back to careful manual reading of every workflow. Instruct subagents: never pass `#`-comment lines to Bash.

Run in the parallel evidence pass:
- **Correctness:** `actionlint` (catches syntax, expression, and shell-quoting errors), or the platform's config validator.
- **Pipeline security:** `zizmor <workflow>` for trigger/injection/permission/pinning findings; capture the rule id + `file:line`.
- **Action pinning:** check each `uses:` for a full-SHA pin vs a tag; `pinact` can report and fix.
- **Gate enforcement (the load-bearing step):** read each workflow's `on:`, `if:`, path filters, and `continue-on-error`, then check the repo's **branch protection** (`gh api repos/{owner}/{repo}/branches/{branch}/protection` or the settings UI) to confirm the intended checks are actually *required*. A gate that is green but not required does not block a merge — verify against branch protection, not the workflow alone. Also skim recent run history (`gh run list`) for chronically-skipped or always-failing-but-ignored jobs.
- **Permissions/secrets:** read the top-level and per-job `permissions:` and every `secrets.` reference; confirm least privilege and that no secret is reachable from an untrusted-code step.

Read the contributor guide (CLAUDE.md / README) for what CI is *claimed* to enforce, and diff that against reality. Record the workflow `file:line` (or the branch-protection fact) as the evidence pointer for every row.

## 4. Status scale + severity rubric

Status per row: **ok / warn / violation**.

- **Critical** — a pipeline-takeover path: `pull_request_target`/`workflow_run` running untrusted PR code with secrets or write permissions; a secret exposed to untrusted code or leaked to logs; an expression-injection sink from untrusted context into a shell step. Also: a claimed merge gate that is not actually required, so unreviewed/broken code can merge green.
- **Important** — over-broad `write-all` permissions where read suffices; a third-party action pinned to a mutable tag in a privileged workflow; long-lived cloud credentials where OIDC is available; a deploy with no environment approval.
- **Minor** — missing caching / concurrency cancellation, an over-broad matrix, an unpinned action in a non-privileged workflow, a cosmetic lint finding.

Suppressions (an intentionally broad permission, an action deliberately tracked by tag) must be explicit and recorded with a reason — never silently dropped.

## 5. Fix patterns (and CI implications)

Fixes here **change the pipeline definition itself**, so the domain gate is unusual: **the changed workflow must parse and run green on a real trigger** — validate with `actionlint` and, where feasible, a test run on a branch/PR before relying on it. Route through the normal review gate.
- **Close the gate gap:** add the check to branch-protection required-status, remove the path filter or `continue-on-error` that let it skip, and make failures actually fail (drop `|| true`, propagate exit codes).
- **Lock down triggers/permissions:** prefer `pull_request` over `pull_request_target`; when `pull_request_target` is unavoidable, do not check out+run PR code with secrets — split into a safe build + a gated, least-privilege follow-up. Set top-level `permissions:` to least privilege (`contents: read`) and widen per-job only as needed.
- **Pin the supply chain:** pin third-party actions to a full commit SHA (with a comment naming the version), and adopt `pinact`/Dependabot to keep pins current.
- **Replace long-lived secrets** with OIDC / short-lived credentials where the platform supports it.
- **Efficiency:** add dependency caching, `concurrency:` with `cancel-in-progress`, and trim the matrix.
- **Highest-leverage fix:** wire `actionlint` + `zizmor` into the pipeline (and pre-commit) so workflow regressions and new insecure patterns are caught automatically.
- Docs-only output: the findings report and any update to the contributor guide's "what CI enforces" section so the claim matches reality.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **Gate reality** — is each "gate is enforced" claim backed by branch-protection evidence, not just a green workflow? Does the fix actually make the check required and blocking?
- **Pipeline-security correctness** — is each trigger/permission/injection finding a genuine attacker path, and does the fix remove it (not just move the secret to another reachable step)?
- **Supply-chain integrity** — are actions pinned to immutable SHAs, and does the pin correspond to the intended version (no typosquat / wrong repo)?
- **No pipeline regression** — the changed workflow still validates and runs; required jobs still run on the right events; nothing was silently disabled to make CI pass.
- **Least privilege preserved** — permission reductions didn't break a job that genuinely needed the write scope.

## 7. Opt-in sub-audits

- **Branch-protection & environment review** — a full pass over repo/branch protection rules and deployment-environment approvals (needs repo-admin API access) — enable via argument or ask the user; needed to fully verify gate enforcement.
- **Self-hosted-runner hardening** — if the project uses self-hosted runners, audit runner isolation, ephemerality, and exposure to untrusted PRs — ask the user; skip for hosted-runner-only projects.
- **Pipeline-secret history scan** — hand off to `security-audit`'s git-history secret scan for secrets that may have been committed to workflow files; note the handoff.
