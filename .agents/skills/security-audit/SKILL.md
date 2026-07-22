---
name: security-audit
description: "Audit a Python project's first-party code for security weaknesses: dangerous calls (eval/exec/pickle/unsafe yaml/subprocess shell), injection (SQL/command/path/SSRF), hardcoded secrets, weak crypto and insecure randomness, and unsafe deserialization or file handling. Use before a release or a public/open-source push, after a security-relevant change, when handling untrusted input or credentials, or when the user asks for a security / SAST / secret-scan audit. Works on any Python project. Runs on the audit-core engine. Third-party CVEs belong to deps-audit; pipeline secrets to ci-audit — this skill owns first-party code."
---

# Security Audit (first-party code)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. This skill supplies the security lens for **first-party code**. It cross-links, and does not duplicate, two neighbors: **[deps-audit](../deps-audit/SKILL.md)** owns third-party CVEs / license risk, and **`ci-audit`** (a sibling in the audit-skills program) owns secrets and hardening inside the CI/CD pipeline.

**Core principle:** find the places where untrusted input meets a dangerous operation, and where a secret could leak. A finding is only real when you can name the source of untrusted data and the sink it reaches; a scanner hit with no reachable attacker path is noise, and a real dataflow the scanner missed is the finding that matters. Verify both directions against the actual code.

**Announce:** "I'm using the security-audit skill (on the audit-core engine) to audit the first-party code for security weaknesses."

**Bash rule:** never pass a line starting with `#` to the Bash tool (you or any subagent).

## When to use

- Before a release, or before making a repo public / open-source (secret history matters here — see §7).
- After a change that parses untrusted input, runs a subprocess, handles credentials, deserializes data, or touches auth.
- When the user asks for a security review, SAST scan, secret scan, or "is this safe to ship."

**Not for:** third-party dependency CVEs (use `deps-audit`), CI/pipeline secret and permission hardening (use `ci-audit`), or a formal pentest of a deployed service (out of scope — this is static, first-party).

## 1. Subject & scope

The project's own source tree (the importable package plus scripts and entry points), and the trust boundaries in it. Establish first, because they set what "untrusted" means:

- **Trust boundaries / input surfaces** — where external data enters (HTTP handlers, CLI args, file/S3 reads, message queues, LLM/tool outputs, env vars). These are the sources.
- **Sensitive sinks** — subprocess/shell, `eval`/`exec`, deserialization, SQL, filesystem paths, outbound requests (SSRF), template rendering.
- **Threat context** — is this an internet-facing service, an internal tool, or a library others import? It changes severity (an injection in a public endpoint outranks the same pattern in a local dev script).

Slice the parallel evidence pass by top-level package/entry point, or by dimension (one agent per weakness class), whichever partitions the tree cleanly.

## 2. Dimensions (findings-matrix columns)

- **Dangerous calls / code execution** — `eval`, `exec`, `compile` on dynamic input; `pickle` / `marshal` / `shelve` loads of untrusted data; `yaml.load` without `SafeLoader`; `subprocess`/`os.system` with `shell=True` or an interpolated command.
- **Injection** — command, SQL (string-built queries), path traversal (`../` into file ops), template/SSTI, and SSRF (user-controlled URL into an outbound request).
- **Secrets in code** — hardcoded API keys, tokens, passwords, private keys, connection strings; secrets in defaults, tests, fixtures, or notebooks.
- **Crypto & randomness** — weak hashes for security use (`md5`/`sha1`), `random` used where `secrets` is required (tokens, salts), disabled TLS verification (`verify=False`), hardcoded IV/keys.
- **Unsafe I/O & deserialization** — XML from untrusted source (XXE via `xml.etree`/`lxml`), tarfile/zip extraction without path checks (zip-slip), world-writable temp files, following symlinks.
- **Sensitive-data handling** — secrets/PII written to logs or error messages, overly broad exception handling that hides security failures, tokens in URLs.

## 3. Evidence sources & tooling

**Detect** what the project has (check `pyproject.toml` / config / pre-commit): a SAST scanner (`bandit`, or `ruff` with the `S` = flake8-bandit ruleset, or `semgrep`), a secret scanner (`detect-secrets`, `gitleaks`, `trufflehog`), and any type checker (a strict typechecker catches some misuse). Prefer a tool the project already runs; fall back otherwise. Instruct subagents: never pass `#`-comment lines to Bash.

Run in the parallel evidence pass:
- **SAST:** `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit.
- **Secrets (working tree):** `detect-secrets scan`, `gitleaks detect --no-git` (or against history — see §7), or a targeted grep for high-signal patterns (`api_key`, `secret`, `-----BEGIN * PRIVATE KEY-----`, provider token prefixes). Every candidate must be **verified by reading the line** — a variable named `api_key` read from the environment is not a leaked secret.
- **Dataflow verification (the load-bearing step):** for each scanner hit, trace source → sink in the real code to confirm an attacker-reachable path and rule out false positives (a `subprocess` call on a hardcoded constant is not command injection). This is what separates a real finding from a scanner artifact.
- **Manual review targets:** grep the codebase for the §2 sink patterns even where the scanner is silent (`eval(`, `pickle.load`, `yaml.load(`, `shell=True`, `verify=False`, `md5(`, `os.system`, `subprocess.*(f"`), and read each hit.

Read the trust-boundary map from §1 and record source + sink `file:line` as the evidence pointer for every row. When a finding overlaps a dependency CVE, note it and defer the CVE detail to `deps-audit` rather than restating it.

## 4. Status scale + severity rubric

Status per row: **ok / warn / violation** (secrets: none / suspected / confirmed-leak).

- **Critical** — a confirmed exploitable path from untrusted input to code execution / injection (RCE, SQLi, command injection) on a reachable surface; a live secret committed to the repo or its history.
- **Important** — an injection/deserialization on a surface not clearly attacker-reachable but plausible; disabled TLS verification; weak crypto protecting real secrets; a secret in a test/fixture that is (or was) valid.
- **Minor** — a defense-in-depth gap, a dangerous pattern on trusted-only input, an insecure-randomness use with no security impact, a low-confidence scanner hit that survives review only as a code-smell.

Suppressions (a scanner false positive, an intentionally allowed pattern with a `# noqa`/`# nosec`-style marker) must be explicit and recorded with a reason — never silently dropped. A confirmed secret is never "suppressed": it must be **rotated**, not just removed.

## 5. Fix patterns (and CI implications)

Security fixes **touch code** (and sometimes secret-management infra), so they are **not** docs-only: the domain gate is "the SAST/secret scan is clean (or every remaining hit is a recorded suppression) **and** the test suite passes" — run the normal install + lint/typecheck/test CI plus the scanner, and the code-review gate.
- **Neutralize the sink:** parameterized queries instead of string SQL; `subprocess.run([...])` with an argument list and no `shell=True`; `yaml.safe_load`; `json`/a schema-validated format instead of `pickle`; `defusedxml` for untrusted XML; `secrets` for tokens; restore TLS verification.
- **Validate/canonicalize input at the boundary:** allowlist, path canonicalization + containment check (defeat traversal/zip-slip), URL host allowlisting (defeat SSRF).
- **Confirmed secret → rotate first, then remove:** rotate the credential at its provider, replace with an env var / secret manager reference, and purge it from history if it was committed (coordinate — history rewrite is disruptive; see §7). Removing the line without rotating leaves a live secret in git history.
- **Highest-leverage fix:** wire the SAST + secret scan into CI (and pre-commit) so the class of finding can't silently recur.
- Docs-only outputs: the findings report, a `SECURITY.md` / disclosure policy, and a threat-model note.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **Exploitability** — is each Critical/Important finding a genuinely reachable source→sink path, or a scanner artifact? Does each fix actually cut the path (not just silence the linter)?
- **Secret verification** — is a flagged secret real and live (vs. a placeholder / env-var name / rotated value)? For confirmed leaks, was rotation done, not just deletion?
- **No security regression / no behavior change** — the fix preserves functionality and does not open a new hole (e.g. an allowlist that is trivially bypassable).
- **Suppression legitimacy** — every `# nosec`/`# noqa` suppression has a recorded, valid reason and isn't hiding a real issue.
- **Sensitive-data hygiene** — the fix doesn't start logging the secret/PII it was protecting.

## 7. Opt-in sub-audits

- **Git-history secret scan** — scan the full commit history (`gitleaks detect`, `trufflehog git`), not just the working tree — enable via argument or ask the user. Default **on before making a repo public**. Findings here usually require credential rotation and possibly history rewrite; flag both.
- **Dependency-CVE cross-check** — hand off to `deps-audit` rather than scanning third-party code here; note the handoff in the report.
- **CI/secret-hardening cross-check** — hand off pipeline secrets / permissions to `ci-audit`; note the handoff.
