---
id: security/secrets-in-code
domain: security
locality: local
handbook:
  - security-supply-chain/secrets-never-commit-them-and-rotate-dont-just-delete-a
routes:
  - lang: any
    kind: command
    tool: detect-secrets
    registry: pypi
    argv: [detect-secrets, scan]
    note: >-
      The default, because it is the one of the three that a one-shot runner
      supplies: `detect-secrets` is a PyPI package, so `uvx detect-secrets scan`
      obtains it whatever the partition's language. Scans the working tree only,
      which is this check's subject. Every candidate must be verified by reading
      the line: a variable named `api_key` read from the environment is not a
      leaked secret.
  - lang: any
    kind: command
    tool: gitleaks
    argv: [gitleaks, detect, "--no-git"]
    own_runner: true
    note: >-
      A standalone binary in no language registry, so no runner supplies it and it
      has to be installed in advance; `npx gitleaks` resolves a package that
      declares no bin and reports `could not determine executable to run`, which
      reads as a missing tool rather than the wrong one. The `--no-git` is
      load-bearing, not a default being spelled out: `gitleaks detect` scans
      history unless told otherwise, and history is `security/secret-history`'s
      subject. A run here that scans it answers the other check under this one's
      name, and leaves the report saying a working-tree pass covered ground it did
      not. Every candidate must be verified by reading the line: a variable named
      `api_key` read from the environment is not a leaked secret.
  - lang: any
    kind: procedure
    tool: trufflehog
    note: >-
      Named beside the two above and prescribed no working-tree command here:
      `trufflehog git` scans history, which is `security/secret-history`'s, and
      `uvx trufflehog` silently runs PyPI's `trufflehog` 2.2.1, the superseded
      Python v2 line rather than the Go v3 this record means, so a runner does not
      obtain it either. Where the v3 binary is installed, its filesystem mode
      answers this check; where it is not, do not reach for the runner. A
      procedure rather than a command because the record prescribes no
      working-tree command line for it.
  - lang: any
    kind: procedure
    note: >-
      With none of the three, a targeted grep for high-signal patterns (`api_key`,
      `secret`, `-----BEGIN * PRIVATE KEY-----`, provider token prefixes) over the
      working tree, at lower recall than a scanner and reported as such. Every
      candidate must be verified by reading the line: a variable named `api_key`
      read from the environment is not a leaked secret.
---

# Secrets in code

Hardcoded API keys, tokens, passwords, private keys, connection strings; secrets in defaults, tests, fixtures, or notebooks.

## Severity

**Critical** - a live secret committed to the repo. A confirmed secret is never "suppressed": it must be **rotated**, not just removed.

**Important** - a secret in a test/fixture that is (or was) valid.

## Fix

**Confirmed secret → rotate first, then remove:** rotate the credential at its provider, replace with an env var / secret manager reference, and purge it from history if it was committed (coordinate - history rewrite is disruptive; see `security/secret-history`). Removing the line without rotating leaves a live secret in git history.

## Review lens

**Secret verification** - is a flagged secret real and live (vs. a placeholder / env-var name / rotated value)? For confirmed leaks, was rotation done, not just deletion?

**Sensitive-data hygiene** - the fix doesn't start logging the secret/PII it was protecting.
