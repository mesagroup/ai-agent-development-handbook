---
id: security/crypto
domain: security
locality: local
handbook: []
handbook_note: >-
  The handbook's own sink taxonomy (shell/subprocess, eval/exec,
  deserialization, SQL, filesystem paths, outbound requests, template
  rendering) names no crypto or randomness sink, and its secrets clause
  covers what a credential must not be, not how it is hashed, generated, or
  transmitted - so no clause grounds a dedicated crypto & randomness check.
tooling:
  python: [bandit, ruff, semgrep]
---

# Crypto & randomness

Weak hashes for security use (`md5`/`sha1`), `random` used where `secrets` is required (tokens, salts), disabled TLS verification (`verify=False`), hardcoded IV/keys.

## Severity

**Important** - disabled TLS verification; weak crypto protecting real secrets.

**Minor** - an insecure-randomness use with no security impact, a low-confidence scanner hit that survives review only as a code-smell.

## Tooling fallback

**Python** - `bandit -r <pkg>` (captures test id like `B602`, severity, confidence, `file:line`), or `ruff check --select S` if the project standardizes on ruff, or `semgrep --config p/python` for dataflow-aware rules. Record test id + `file:line` per hit.

Grep the codebase for these patterns even where the scanner is silent (`verify=False`, `md5(`), and read each hit.

## Fix

**Neutralize the sink:** `secrets` for tokens; restore TLS verification.
