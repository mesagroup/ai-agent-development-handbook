---
id: ci/branch-protection
domain: ci
locality: global
optin: true
handbook: []
handbook_note: >-
  implementation-disciplines.md's gate-enforcement clause ("confirm the
  gate against the branch-protection rules, not the badge") already
  grounds `ci/gate-enforcement`, and that clause asks only whether an
  intended check is required there - not for a standing, repo-admin-level
  audit of the whole branch-protection and deployment-environment-approval
  configuration as its own subject (review-count requirements, admin
  bypass, who can push directly, environment-level approvers). Citing the
  same clause a second time for this broader sweep would be the near miss
  the matrix's own rule forbids; the handbook never asks for that full
  sweep on its own terms.
tooling:
  any: [gh]
---

# Branch-protection & environment review

A full pass over repo/branch protection rules and deployment-environment approvals (needs repo-admin API access) - enable via argument or ask the user; needed to fully verify gate enforcement.
