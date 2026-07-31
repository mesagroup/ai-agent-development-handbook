---
id: security/unsafe-io
domain: security
locality: local
handbook:
  - security-supply-chain/first-party-code-trace-a-path-from-source-to-sink
tooling:
  python: [bandit, ruff, semgrep]
---

# Unsafe I/O & deserialization

XML from untrusted source (XXE via `xml.etree`/`lxml`), tarfile/zip extraction without path checks (zip-slip), world-writable temp files, following symlinks.

## Severity

**Important** - an injection/deserialization on a surface not clearly attacker-reachable but plausible.

**Minor** - a defense-in-depth gap, a low-confidence scanner hit that survives review only as a code-smell.

## Tooling fallback

**Python** - `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit.

## Fix

**Neutralize the sink:** `defusedxml` for untrusted XML.

**Validate/canonicalize input at the boundary:** path canonicalization + containment check (defeat zip-slip).

## Review lens

Is each Critical/Important finding a genuinely reachable source→sink path, or a scanner artifact? Does each fix actually cut the path (not just silence the linter)?
