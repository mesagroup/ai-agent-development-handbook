---
id: ci/action-supply-chain
domain: ci
locality: local
handbook:
  - security-supply-chain/treat-the-pipeline-as-a-privileged-environment
routes:
  - lang: any
    kind: command
    tool: zizmor
    registry: pypi
    argv: [zizmor, "<workflow>"]
    applies_when: >-
      The CI platform is GitHub Actions, whose workflow and action definitions are what the tool reads.
    note: >-
      `zizmor <workflow>` for trigger/injection/permission/pinning findings;
      capture the rule id + `file:line`. A PyPI package, so `uvx zizmor` obtains
      it whatever the partition's language; without a `GH_TOKEN` it runs in
      offline mode.
  - lang: any
    kind: command
    tool: pinact
    argv: [pinact, run, "--check"]
    own_runner: true
    disposition: alternative
    applies_when: >-
      The CI platform is GitHub Actions, whose workflow and action definitions are what the tool reads.
    note: >-
      `pinact run --check` reports every `uses:` not pinned to a full commit
      SHA and exits non-zero where something needs pinning; `pinact run`
      without the flag rewrites the pins, which is the fix rather than the
      measurement. A standalone binary in no language registry, installed in
      advance; the check calls the GitHub API to resolve each tag unless run
      with `--no-api`, so a `GITHUB_TOKEN` keeps it clear of the rate limit.
  - lang: any
    kind: procedure
    applies_when: >-
      The CI platform is GitHub Actions, whose workflow syntax this reading names.
    note: >-
      **Action pinning:** check each `uses:` for a full-SHA pin vs a tag.
---

# Action supply chain

Third-party actions pinned to a mutable tag/branch (`@v4`, `@main`) instead of a full commit SHA; unvetted/abandoned actions; actions from untrusted publishers.

## Severity

**Important** - a third-party action pinned to a mutable tag in a privileged workflow.

**Minor** - an unpinned action in a non-privileged workflow.

## Fix

**Pin the supply chain:** pin third-party actions to a full commit SHA (with a comment naming the version), and adopt `pinact`/Dependabot to keep pins current.

## Review lens

**Supply-chain integrity** - are actions pinned to immutable SHAs, and does the pin correspond to the intended version (no typosquat / wrong repo)?
