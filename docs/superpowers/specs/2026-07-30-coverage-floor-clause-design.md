# Coverage-floor clause design (lidia-tech/lidia-agents#551)

**Status:** approved 2026-07-30. Implements wave 0 of [#1](https://github.com/mesagroup/ai-agent-development-handbook/issues/1), after [lidia-tech/lidia-agents#552](https://github.com/lidia-tech/lidia-agents/issues/552).

## Problem

The handbook's TDD section requires that new code ships with tests and does not lower coverage. It says nothing about what coverage level a project should hold itself to, and neither does `test-audit`.

A universal percentage carved into the handbook would be wrong: 90% on a thin CRUD service and 90% on a parser mean different things, and a number the handbook picks becomes a number people game. But the *absence* of any clause means a project can pass both the handbook and `test-audit` while never having decided what it is aiming for, and an auditor arriving at a foreign codebase has nothing to compare the measured number against.

Three findings from exploration shaped the design.

**`test-audit` is already written for a world where the floor exists.** Its status scale is `meets-floor / below-floor / untested`, §1 tells the auditor to establish "any coverage floor the contributor guide or CI enforces", and §4 rates dropping below "a required floor" as Critical. With no floor stated anywhere, that machinery has an undefined input and silently degrades to judging a bare number, which is exactly what the skill's own core principle forbids.

**Half the issue's open questions were already answered by our own artifacts.** The handbook already says to measure coverage on the diff, so diff *measurement* was never in question, only a diff *floor*. And once the clause says a floor must be stated, "no stated floor" is a violation by construction rather than a separate policy call.

**The clause has to survive a tension with its neighbour.** Part 2 contains "Chase caught regressions, not coverage percentage", arguing a high number is a false safety net "worse than an honest low number". A clause requiring a floor can easily read as contradicting it. The clause is therefore framed as a **decision record**, not a quality measure, and is placed directly beside that subsection so the two are read together.

## Decisions

### 1. Shape: whole-project floor required, diff floor recommended

The auditable minimum is a stated, executable whole-project floor, plus the existing no-lowering ratchet. The clause names a floor on changed lines as the stronger form and says why, without requiring it.

This trades some prevention for auditability, deliberately. Diff coverage prevents the real failure better, because its denominator is the change and therefore cannot be diluted by the rest of the repo. But a whole-project floor is *statically readable*: `fail_under = 80` in `pyproject.toml` can be read off a foreign codebase in seconds, whereas confirming a project truly enforces diff coverage means reading workflow files, and measuring it means running their suite against a base ref. Since #1 (auditing external codebases) is the epic this feeds, static readability wins the MUST and prevention takes the SHOULD.

**Rejected: whole-project floor as the only content.** The handbook already contains the sentence that refutes it, saying to measure on the diff *because* "'don't lower overall coverage' can hide new code that shipped untested behind a large well-covered base." Shipping floor-plus-ratchet as the whole clause would put the new text in tension with the sentence a few lines above it.

The gaming analysis that produced this, on current repo numbers (14610/21914 = 66.67%):

| Lever | Effect |
|---|---|
| Ratchet resolution | New uncovered lines lower coverage by only `C x N/T`. Moving the reported integer needs roughly 56 statements from the current position, about 334 from a safer one. A medium function to an entire feature ships before the gate notices, and the threshold shifts week to week with the repo's position relative to the rounding boundary. |
| Dilution | 500 lines of trivially-covered plumbing beside 100 lines of untested parser logic *raises* overall coverage. Floor and ratchet both pass; the untested part is the load-bearing part. |
| Denominator | Growing `omit`, adding `# pragma: no cover`, or deleting dead untested code to bank headroom. |
| Assertion-free tests | Defeats any coverage metric. Orthogonal, and already owned by the "Chase caught regressions" subsection and `test-audit`'s Assertion strength dimension. |

Diff coverage closes the first two structurally. It does not close the last two, which is why the ratchet and the assertion-strength clause both remain.

### 2. Granularity: one floor plus a stated denominator; tiers optional

Require the floor and what it is measured over. Exclusions are part of the decision, and load-bearing deterministic logic may never be one. Tier-specific floors are permitted, not required.

The issue asked about per-tier floors. Exploration pointed elsewhere: `coverage.py` has no per-path `fail_under`, so tier floors need multiple runs or extra tooling, which fights the executable-and-statically-readable property that the shape decision just made governing. A tier map is also gerrymanderable, since untested code can simply be moved into the low-floor tier.

The denominator is the stronger lever for the same cost. `fail_under = 80` with `omit = ["*/parsers/*"]` is not 80%, and both keys sit in the same config block, so requiring the denominator to be stated closes the dilution vector while remaining a single-glance read.

### 3. "No stated floor" is a finding

Answered by construction: the clause requires stating a floor, so its absence violates the clause. This gives `test-audit`'s existing `below-floor` status a defined input for the first time.

### 4. Dogfooding: this project adopts a floor in the same change

`fail_under = 65` in `[tool.coverage.report]`, against a measured 66.67% in CI and 66.88% locally. That spread between environments is itself part of the argument below.

Shipping a normative clause the originating project violates is the precise "aspirational, not enforced" failure the clause exists to prevent. Dogfooding also tests that the clause is adoptable at all. CI already runs `pytest --cov=lidia_agents` under `set -o pipefail`, and pytest-cov honours `fail_under`, so this is one config line with no workflow change. Our `omit` is already tests-only, so the denominator is honest as-is.

Set at 65 rather than at the measured value, giving about 563 statements of headroom (`14610/0.65 - 21914`). A floor pinned tight against current coverage reddens CI on ordinary variation rather than on a real regression, and a gate that fires on noise gets raised or ignored, which is how a floor becomes aspirational. The shoulder buys room for the clause to be adopted without immediately fighting in-flight work.

This makes the floor a genuine floor rather than a ratchet: the "do not lower coverage" rule is what catches the slow slide, and the floor catches the cliff. Raising it later as coverage improves is a deliberate act, which is the point of requiring the number to be stated.

## The clause

A new `###` subsection in `docs/engineering/implementation-disciplines.md`, under `## TDD`, placed beside "Chase caught regressions, not coverage percentage".

It names unit-test coverage explicitly in both the heading and the first clause, because this handbook overloads "coverage" in two other senses: the traceability matrix's coverage-hole check, and Part 6's ground-truth `recall / coverage / consistency`.

Text as approved:

> ### Decide the unit-test coverage floor upfront, and record it where it runs
>
> Unit-test coverage, the proportion of your code that the test suite actually executes, is the number everyone asks for and no handbook can supply: 90% on a thin CRUD service and 90% on a parser mean different things. So this handbook names no percentage, and requires the *decision* instead. State a required floor, state what that floor is measured over, and put both somewhere that executes, the coverage config or the CI gate rather than a wiki page. An unstated floor is not a lenient one, it is an unfalsifiable one: it turns "is 62% good?" into a question nobody can answer, and leaves every later argument about coverage to whoever cares most that day.
>
> The denominator is part of the decision, because a floor without one says nothing: 80% measured over a source tree that quietly excludes the parsers is not 80%. Exclusions are a stated choice, and load-bearing deterministic logic is never a legitimate one. Justify a deliberately low floor rather than leaving it unexplained; a nice-to-have target above the floor is optional, as long as the floor is what CI enforces.
>
> A whole-project floor is the minimum, not the strong form. Pair it with a floor on the changed lines, which the whole-project number cannot substitute for: against a large well-covered base, an entire feature can ship untested before the aggregate number moves.

Handbook conventions that bind the final text: no em-dashes, one paragraph per source line, direct imperative prose rather than RFC 2119 keywords (those are for SOPs).

## The matrix row

A third row under the existing TDD section, so it adds no `##` heading and creates no coverage hole in `handbook-traceability.yaml`.

```yaml
- id: implementation-disciplines/tdd-c
  section: "TDD"
  claim: Decide the unit-test coverage floor upfront rather than assuming a number - state a required floor and what it is measured over, record both somewhere executable (coverage config or CI gate) rather than aspirational, treat exclusions as part of the decision and never exclude load-bearing deterministic logic, justify a deliberately low floor, and pair the whole-project floor with a floor on changed lines.
  class: static
  severity: important
  gap:
    recommendation: extend-skill
    note: "test-audit is the owner ... the declaration belongs to that skill's wave-1 sweep pass (#7 + #5 + #8)."
```

`class: static` because a stated floor is readable from a config snapshot. `severity: important` matches the `tdd-b` row it sits beside; `critical` is reserved for rows whose violation causes direct harm, and a missing decision does not.

**The row maps nothing and gaps everything**, corrected during review after an initial draft mapped it to `test-audit` / Coverage reach. The matrix's own Near-miss rule says to refuse a mapping and gap the whole claim when the cited dimension would *pass* the violation. Coverage reach measures line and branch coverage per module, so it passes a project that never stated a floor, and passes one that omits its parsers from the denominator, because excluded code is absent rather than uncovered. That is the very exclusion this clause forbids. `extend-skill` rather than `new-domain`, because `test-audit` is the natural owner and already carries the floor concept outside its Dimensions section, which the gap taxonomy names explicitly.

Mapping it would also have made the spec contradict itself: the scope boundary below defers the `test-audit` update, while a full mapping asserts the clause is already checked.

## Scope boundary

The `test-audit` Coverage-dimension update is **not** implemented here. It is recorded against that skill's wave-1 sweep pass (#7 + #5 + #8), which rewrites the skill anyway; doing it here would touch the skill twice, which is what merging the sweep was meant to avoid.

## Files

| File | Change |
|---|---|
| `docs/engineering/implementation-disciplines.md` | New `###` subsection under `## TDD` |
| `docs/audit/handbook-traceability.yaml` | New row `implementation-disciplines/tdd-c` |
| `docs/audit/handbook-traceability.md` | Regenerated from the YAML |
| `pyproject.toml` | `fail_under = 65` in `[tool.coverage.report]` |

Gates: `render_handbook_traceability.py --check`, `mkdocs build --strict`, `check_site_links.py`, the handbook artifact render, and CI's own coverage gate now that it has a floor.
