---
name: security-audit
description: "Audit a Python project's first-party code for security weaknesses: dangerous calls (eval/exec/pickle/unsafe yaml/subprocess shell), injection (SQL/command/path/SSRF), hardcoded secrets, weak crypto and insecure randomness, and unsafe deserialization or file handling. Use before a release or a public/open-source push, after a security-relevant change, when handling untrusted input or credentials, or when the user asks for a security / SAST / secret-scan audit. Works on any Python project. Runs on the audit-core engine. Third-party CVEs belong to deps-audit; pipeline secrets to ci-audit — this skill owns first-party code."
---

# Security Audit (first-party code)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory. This skill supplies the security lens for **first-party code**.

**Core principle:** find the places where untrusted input meets a dangerous operation, and where a secret could leak. A finding is only real when you can name the source of untrusted data and the sink it reaches; a scanner hit with no reachable attacker path is noise, and a real dataflow the scanner missed is the finding that matters. Verify both directions against the actual code.

**Announce:** "I'm using the security-audit skill (on the audit-core engine) to audit the first-party code for security weaknesses."

**Not for:** third-party dependency CVEs (use `deps-audit`), CI/pipeline secret and permission hardening (use `ci-audit`), or a formal pentest of a deployed service (out of scope - this is static, first-party).

**Subject:** the project's own source tree (the importable package plus scripts and entry points), and the trust boundaries in it. Establish first, because they set what "untrusted" means:

- **Trust boundaries / input surfaces** - where external data enters (HTTP handlers, CLI args, file/S3 reads, message queues, LLM/tool outputs, env vars). These are the sources.
- **Threat context** - is this an internet-facing service, an internal tool, or a library others import? It changes severity (an injection in a public endpoint outranks the same pattern in a local dev script).

Slice the parallel evidence pass by top-level package/entry point, or by check (one agent per weakness class), whichever partitions the tree cleanly. Every core check is `local` to a code slice; only the opt-in `security/secret-history` is `global`, because git history is one object that no per-slice agent can scan.

**Detect** what the project has (check `pyproject.toml` / config / pre-commit): a SAST scanner (`bandit`, or `ruff` with the `S` = flake8-bandit ruleset, or `semgrep`), a secret scanner (`detect-secrets`, `gitleaks`, `trufflehog`), and any type checker (a strict typechecker catches some misuse). Prefer a tool the project already runs; fall back otherwise.

Read the trust-boundary map above and record source + sink `file:line` as the evidence pointer for every row.

Status per row: **ok / warn / violation** (secrets: none / suspected / confirmed-leak). Suppressions (a scanner false positive, an intentionally allowed pattern with a `# noqa`/`# nosec`-style marker) must be explicit and recorded with a reason - never silently dropped.

Security fixes **touch code** (and sometimes secret-management infra), so they are **not** docs-only: the domain gate is "the SAST/secret scan is clean (or every remaining hit is a recorded suppression) **and** the test suite passes" - run the normal install + lint/typecheck/test CI plus the scanner, and the code-review gate. **Highest-leverage fix:** wire the SAST + secret scan into CI (and pre-commit) so the class of finding can't silently recur. Docs-only outputs: the findings report, a `SECURITY.md` / disclosure policy, and a threat-model note.

**Dependency-CVE cross-check** - hand off to `deps/vulnerabilities` rather than scanning third-party code here; note the handoff in the report. **CI/secret-hardening cross-check** - hand off pipeline secrets / permissions to `ci/permissions-secrets`; note the handoff.
