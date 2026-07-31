---
id: ci/action-supply-chain
domain: ci
locality: local
handbook:
  - security-supply-chain/treat-the-pipeline-as-a-privileged-environment
tooling:
  any: [zizmor, pinact]
---

# Action supply chain

Third-party actions pinned to a mutable tag/branch (`@v4`, `@main`) instead of a full commit SHA; unvetted/abandoned actions; actions from untrusted publishers.

## Severity

**Important** - a third-party action pinned to a mutable tag in a privileged workflow.

**Minor** - an unpinned action in a non-privileged workflow.

## Tooling fallback

`zizmor <workflow>` for trigger/injection/permission/pinning findings; capture the rule id + `file:line`.

**Action pinning:** check each `uses:` for a full-SHA pin vs a tag; `pinact` can report and fix.

## Fix

**Pin the supply chain:** pin third-party actions to a full commit SHA (with a comment naming the version), and adopt `pinact`/Dependabot to keep pins current.

## Review lens

**Supply-chain integrity** - are actions pinned to immutable SHAs, and does the pin correspond to the intended version (no typosquat / wrong repo)?
