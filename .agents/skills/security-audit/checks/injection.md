---
id: security/injection
domain: security
locality: local
handbook:
  - security-supply-chain/first-party-code-trace-a-path-from-source-to-sink
tooling:
  python: [bandit, ruff, semgrep]
---

# Injection

Command, SQL (string-built queries), path traversal (`../` into file ops), template/SSTI, and SSRF (user-controlled URL into an outbound request).

## Severity

**Critical** - a confirmed exploitable path from untrusted input to code execution / injection (RCE, SQLi, command injection) on a reachable surface.

**Important** - an injection/deserialization on a surface not clearly attacker-reachable but plausible.

**Minor** - a defense-in-depth gap, a low-confidence scanner hit that survives review only as a code-smell.

## Tooling fallback

**Python** - `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit.

**Dataflow verification (the load-bearing step):** for each scanner hit, trace source → sink in the real code to confirm an attacker-reachable path and rule out false positives (a `subprocess` call on a hardcoded constant is not command injection). This is what separates a real finding from a scanner artifact.

## Fix

**Neutralize the sink:** parameterized queries instead of string SQL; `subprocess.run([...])` with an argument list and no `shell=True`.

**Validate/canonicalize input at the boundary:** allowlist, path canonicalization + containment check (defeat traversal), URL host allowlisting (defeat SSRF).

## Review lens

Is each Critical/Important finding a genuinely reachable source→sink path, or a scanner artifact? Does each fix actually cut the path (not just silence the linter)?
