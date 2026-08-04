---
id: security/secret-history
domain: security
locality: global
optin: true
handbook:
  - security-supply-chain/secrets-never-commit-them-and-rotate-dont-just-delete-b
tooling:
  any: [gitleaks, trufflehog]
---

# Git-history secret scan

Scan the full commit history (`gitleaks detect`, `trufflehog git`), not just the working tree - enable via argument or ask the user. Default **on before making a repo public**.

## Severity

**Critical** - a live secret committed to the repo's history.

## Fix

Findings here usually require credential rotation and possibly history rewrite; flag both.

## Review lens

**Secret verification** - is a flagged secret real and live (vs. a placeholder / env-var name / rotated value)? For confirmed leaks, was rotation done, not just deletion?
