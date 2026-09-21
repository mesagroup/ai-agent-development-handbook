---
id: docs/coverage
domain: docs
locality: global
handbook:
  - documentation/aim-for-docs-that-stand-alone-drifted-docs-are-worse-than-none-a
  - documentation/keep-the-decision-trail-artifacts-b
  - documentation/audit-docs-like-a-test-suite-a
routes:
  - lang: any
    kind: procedure
    note: >-
      Detection is the shared source-map pass the skill header builds ("Build the
      source maps once, first") - no separate tool or fallback of its own.
---

# Coverage

For every code component, the doc(s) covering it and a status: **documented** (a real dedicated doc), **partial** (only a passing mention / entry-level note / design-spec, no prescriptive reference), or **gap** (nothing). The partial/gap rows are the fill-gaps work list.

## Severity

**Critical** - a doc that actively misdescribes the system (removed API still documented, wrong default/signature that would mislead a reader).

**Important** - an uncovered load-bearing component.

**Minor** - a partial that has a passing mention.

## Fix

Write the missing doc to the project's doc standard (Overview → Functional → Architecture → Configuration → See also, or whatever the extracted standard is), grounded in the source maps.

**Each doc-creation task ships its own index entry in the same commit** (forward-link-safe: no task links a doc a later task creates; the checker stays green per task). Only isolate index changes to a final task when the new docs sit under an existing directory-link that auto-covers them.

Ground each writing task in the source maps the skill header builds: the exact interfaces/facts to cover (with `file:line`), so the implementer verifies rather than invents.

## Review lens

**Source accuracy** - open the code and verify the docs' concrete claims (names, signatures, defaults, env vars, "does X now"). Highest-value catch: fabricated defaults, dropped flags, wrong import paths.

**Cross-doc consistency** - new docs agree with each other and with pre-existing docs.

**Doc-standard + conventions** - section order, markdown/style, no env-specific values.

**Coverage vs plan** - every planned gap/partial actually addressed; nothing silently dropped.
