---
id: security/sensitive-data
domain: security
locality: local
handbook:
  - implementation-disciplines/coding-hygiene-rules-that-surface-at-review-a
  - observability/make-errors-diagnosable
  - data-protection/personal-data-does-not-belong-in-the-trail
---

# Sensitive-data handling

Secrets/PII written to logs or error messages, overly broad exception handling that hides security failures, tokens in URLs.

## Tooling fallback

Needs reading - no scanner or grep target in this domain's evidence pass covers this pattern; read the logging and exception-handling call sites near secret- or PII-bearing variables, and any outbound URL construction, for exposure.
