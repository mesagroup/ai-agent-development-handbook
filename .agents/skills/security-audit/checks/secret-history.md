---
id: security/secret-history
domain: security
locality: global
optin: true
handbook: []
handbook_note: >-
  The handbook's secrets clause frames a committed credential as live until
  rotated and asks for history to be purged when a secret was ever pushed,
  but the one clause the matrix can cite reads the working tree
  (`security/secrets-in-code`'s no-literal-in-source check); scanning the
  commit history itself is this check's own opt-in scope, and the handbook
  states no separate clause asking for a history scan specifically.
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
