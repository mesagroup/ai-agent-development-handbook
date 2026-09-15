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

Secrets/PII written to logs or error messages, overly broad exception handling that hides security failures, tokens or personal identifiers in URLs. The identifier case is named because a token is a credential and a personal identifier is not, and the row that hands the call site here disclaims both - so an identifier in a URL would otherwise be claimed by nobody.

## Tooling fallback

Needs reading - no scanner or grep target in this domain's evidence pass covers this pattern; read the logging and exception-handling call sites near secret- or PII-bearing variables, and any outbound URL construction, for exposure.

**This check is the call site; the stored copy is `data-protection/stored-artifact-pii`'s.** The boundary has to be said rather than assumed, or one gap gets reported twice with its fix split across two owners: a payload reaching a log statement, a token in a URL, an exception message carrying a record is this row, and the trace, run record, eval dataset or fixture that still holds it after the call returned is that one. Do not scan stored artifacts here, and do not treat a clean result here as covering them - a call site cleared for exposure says nothing about what a previous run already wrote to disk.
