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

Scan the full commit history (`gitleaks detect`, `trufflehog git`), not just the working tree. **It is opt-in for two reasons, and neither is that history matters less**: it needs one of those binaries already present in the audit environment, since no one-shot runner supplies either - the fallback below sets out what that costs - and acting on what it finds is a coordinated history rewrite rather than an edit, which is a decision the project takes rather than one an audit takes for it. Enable via argument or ask the user, and default it **on before making a repo public**.

## Tooling fallback

**Both tools are standalone binaries in no language registry, so no one-shot runner supplies either** - an audit environment expected to answer this check needs one installed in advance, and where neither is present this check is `no-evidence (tool-unavailable)` rather than a clean history. Reaching for a runner anyway does not fail cleanly in either ecosystem. `npx gitleaks` resolves a package that declares no bin and reports `could not determine executable to run`, which reads as a missing tool rather than the wrong one. `uvx trufflehog` is worse, because it succeeds: PyPI carries `trufflehog` 2.2.1, the original `dxa4481/truffleHog`, which is the Python v2 line superseded by the Go TruffleHog v3 this record means. It runs, takes a `git_url` positional rather than v3's subcommands, and scans with v2's detectors, so it answers the check with a weaker tool and no sign of the substitution. Same publisher lineage as the tool intended, so this is a stale genuine scanner rather than unvetted code - which makes it a quietly weaker answer rather than a loud failure.

**With neither binary available**, the fallback is not a clean result and not nothing either: `git log -p` piped through high-signal credential patterns - `security/secrets-in-code` is where they are written down - covers the same history at much lower recall, and reporting it as a partial pass with the recall limit named beats reporting an unscanned history as clean.

## Severity

**Critical** - a live secret committed to the repo's history.

## Fix

Findings here usually require credential rotation and possibly history rewrite; flag both.

## Review lens

**Secret verification** - is a flagged secret real and live (vs. a placeholder / env-var name / rotated value)? For confirmed leaks, was rotation done, not just deletion?
