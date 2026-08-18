---
id: arch/complexity-gate
domain: arch
locality: global
optin: false
handbook: []
handbook_note: >-
  The structural-decay clause
  (codebase-structure/watch-for-structural-decay-beyond-layering) names
  complexity as a decay signal to watch and measure; it does not say a
  threshold must be configured or enforced in CI. The matrix already treats
  that enforcement question as separate territory: the sibling clause from the
  same doc section,
  codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-b
  ("so it is enforceable by an import-boundary linter in CI"), routes to
  ci-audit's `ci/gate-enforcement` check, not to arch. Grounding this check in
  the structural-decay clause instead would be the near miss the matrix's own
  rule forbids - passing a codebase that measures complexity but gates
  nothing.
routes:
  - lang: none
    kind: procedure
    note: >-
      Whether a threshold is set, and whether a CI job fails the build on it,
      is read from the partition's linter configuration and its CI workflow
      files, both present on a read-only clone, so the gate question is
      answered in full with no grant. Read the project's configured threshold
      before measuring, and treat its absence as a finding in its own right.
      The route names no tool and belongs to no language because the gate is a
      single repo-wide fact read off configuration, not a lens over source.
  - lang: python
    kind: subject
    tool: ruff
    note: >-
      The gate's subject rather than its instrument: running it measures code
      against a threshold, which is `arch/complexity`'s question, not this
      one. `C901` needs `mccabe` max-complexity set in `pyproject.toml`; if it
      is unset, passing a threshold on the command line yields clean numbers
      and silently hides the gap. What this check records is what the project
      itself enforces - a number it never configured is a number nothing holds
      it to.
  - lang: python
    kind: subject
    tool: radon
    note: >-
      The gate's subject rather than its instrument. Whichever tool the
      project runs, record the threshold it configured for that tool rather
      than one supplied here.
  - lang: python
    kind: subject
    tool: xenon
    note: >-
      The gate's subject rather than its instrument. Whichever tool the
      project runs, record the threshold it configured for that tool rather
      than one supplied here.
  - lang: typescript
    kind: subject
    tool: eslint
    needs: target-execution
    note: >-
      The gate's subject rather than its instrument: what this check records
      is whether the project configured a threshold for it, not what running
      it reports. The tier and the kind are independent claims - the tier says
      what the tool would require before it could answer anything, the kind
      says this check is not using it to answer. Both are true here, and the
      tier is what the record measures: on an uninstalled TypeScript tree
      ESLint aborts with `ERR_MODULE_NOT_FOUND` before it reaches a threshold
      at all. That abort is a missing `node_modules`, not a verdict on whether
      the gate is configured, so don't record it as either a clean or a
      failing threshold check.
  - lang: typescript
    kind: subject
    tool: eslint-plugin-sonarjs
    needs: target-execution
    note: >-
      The gate's subject rather than its instrument, and tiered for the same
      reason as ESLint above: it is what a configured cognitive-complexity
      threshold would be configured for, and it cannot run at all over an
      uninstalled tree.
---

# Complexity gate

Whether a complexity threshold is actually configured and enforced, not just measurable. `arch/complexity` catches a function whose complexity resists understanding; this check catches the case where nothing in the project would catch the next one - the threshold is unset, so every run of the underlying tool reports a clean pass regardless of what ships. This is a single repo-wide fact, true or false once for the whole project, not a per-function or per-package property.

## Severity

**Important** - the threshold is unconfigured, so complexity is ungated and a regression is never caught.

## Tooling fallback

**Read the project's configured threshold before measuring, and treat its absence as a finding in its own right.** `C901` needs `mccabe` max-complexity set in `pyproject.toml`; if it is unset, passing a threshold on the command line yields clean numbers and silently hides the gap. Whichever tool you run, record what the project itself enforces - a number it never configured is a number nothing holds it to. On an uninstalled TypeScript tree, ESLint aborts with `ERR_MODULE_NOT_FOUND` before it reaches a threshold at all - that abort is a missing `node_modules`, not a verdict on whether the gate is configured, so don't record it as either a clean or a failing threshold check.

## Fix

Configure an explicit threshold for whichever tool the project already uses (`mccabe` max-complexity in `pyproject.toml` for `ruff --select C901`, or the equivalent for `radon`/`xenon`/ESLint's `complexity` rule/`eslint-plugin-sonarjs`), then wire the check into CI as a required job so a regression fails the build rather than only surfacing in this audit's next run.

## Review lens

**Gate + threshold reality** - a threshold fix actually gates CI - the value lives in a job that fails the build, not only in a config file nothing runs - and the number chosen is a real ceiling, not one raised just high enough to pass the current codebase's worst offenders.
