---
id: security/secrets-in-code
domain: security
locality: local
handbook:
  - security-supply-chain/secrets-never-commit-them-and-rotate-dont-just-delete-a
tooling:
  any: [detect-secrets, gitleaks, trufflehog]
---

# Secrets in code

Hardcoded API keys, tokens, passwords, private keys, connection strings; secrets in defaults, tests, fixtures, or notebooks.

## Severity

**Critical** - a live secret committed to the repo. A confirmed secret is never "suppressed": it must be **rotated**, not just removed.

**Important** - a secret in a test/fixture that is (or was) valid.

## Tooling fallback

**The three tools are not the same kind, and only one is fetchable.** `detect-secrets` is a PyPI package, so `uvx detect-secrets scan` obtains it whatever the partition's language and it is the default here. `gitleaks` and `trufflehog` are standalone binaries no runner supplies, and each fails misleadingly if one is asked to: `npx gitleaks` reports `could not determine executable to run`, and `uvx trufflehog` silently runs PyPI's `trufflehog` 2.2.1, the superseded Python v2 line rather than the Go v3 - see `security/secret-history` for `gitleaks` and `trufflehog`.

**Secrets (working tree):** `detect-secrets scan`, `gitleaks detect --no-git`, or a targeted grep for high-signal patterns (`api_key`, `secret`, `-----BEGIN * PRIVATE KEY-----`, provider token prefixes). Every candidate must be **verified by reading the line** - a variable named `api_key` read from the environment is not a leaked secret. **The `--no-git` is load-bearing, not a default being spelled out**: `gitleaks detect` and `trufflehog git` scan history unless told otherwise, and history is `security/secret-history`'s subject. A run here that scans it answers the other check under this one's name, and leaves the report saying a working-tree pass covered ground it did not.

## Fix

**Confirmed secret → rotate first, then remove:** rotate the credential at its provider, replace with an env var / secret manager reference, and purge it from history if it was committed (coordinate - history rewrite is disruptive; see `security/secret-history`). Removing the line without rotating leaves a live secret in git history.

## Review lens

**Secret verification** - is a flagged secret real and live (vs. a placeholder / env-var name / rotated value)? For confirmed leaks, was rotation done, not just deletion?

**Sensitive-data hygiene** - the fix doesn't start logging the secret/PII it was protecting.
