---
id: arch/complexity-gate
domain: arch
locality: global
optin: false
handbook: []
handbook_note: >-
  The structural-decay clause (codebase-structure/watch-for-structural-decay-beyond-layering) names complexity as a decay signal to watch and measure; it does not say a threshold must be configured or enforced in CI. The matrix already treats that enforcement question as separate territory: the sibling clause from the same doc section, codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-b ("so it is enforceable by an import-boundary linter in CI"), routes to ci-audit's `ci/gate-enforcement` check, not to arch. Grounding this check in the structural-decay clause instead would be the near miss the matrix's own rule forbids - passing a codebase that measures complexity but gates nothing.
tooling:
  python: [ruff, radon, xenon]
  typescript: [eslint, eslint-plugin-sonarjs]
---

# Complexity gate

Whether a complexity threshold is actually configured and enforced, not just measurable. `arch/complexity` catches a function whose complexity resists understanding; this check catches the case where nothing in the project would catch the next one - the threshold is unset, so every run of the underlying tool reports a clean pass regardless of what ships. This is a single repo-wide fact, true or false once for the whole project, not a per-function or per-package property.

## Severity

**Important** - the threshold is unconfigured, so complexity is ungated and a regression is never caught.

## Tooling fallback

**Read the project's configured threshold before measuring, and treat its absence as a finding in its own right.** `C901` needs `mccabe` max-complexity set in `pyproject.toml`; if it is unset, passing a threshold on the command line yields clean numbers and silently hides the gap. Whichever tool you run, record what the project itself enforces - a number it never configured is a number nothing holds it to.

## Fix

Configure an explicit threshold for whichever tool the project already uses (`mccabe` max-complexity in `pyproject.toml` for `ruff --select C901`, or the equivalent for `radon`/`xenon`/ESLint's `complexity` rule/`eslint-plugin-sonarjs`), then wire the check into CI as a required job so a regression fails the build rather than only surfacing in this audit's next run.

## Review lens

**Gate + threshold reality** - a threshold fix actually gates CI - the value lives in a job that fails the build, not only in a config file nothing runs - and the number chosen is a real ceiling, not one raised just high enough to pass the current codebase's worst offenders.
