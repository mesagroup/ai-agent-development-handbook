# Coverage-floor clause Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the handbook clause requiring a project to decide its unit-test coverage floor upfront, register it in the traceability matrix, and adopt a floor for this project so the clause is not aspirational on day one.

**Architecture:** Three coupled artifacts and one config line. The handbook gains a `###` subsection under `## TDD`; the traceability matrix gains a row for it and is regenerated; `pyproject.toml` gains `fail_under`. No Python source changes, so no new unit tests: the matrix's own validator and existing test suite are the gate.

**Tech Stack:** Markdown, YAML, `scripts/render_handbook_traceability.py`, `pyproject.toml` / `coverage.py`.

**Design:** `docs/superpowers/specs/2026-07-30-coverage-floor-clause-design.md`

## Global Constraints

- **No em-dashes (U+2014) anywhere in `docs/engineering/`.** Use commas, colons, semicolons, or parentheses. This is house style for the handbook and is not negotiable.
- **One paragraph per source line in Markdown.** Never hard-wrap prose. Do not reflow neighbouring lines you did not change.
- **Handbook voice is direct imperative prose, not RFC 2119 keywords.** MUST/SHOULD belong to SOPs, not to handbook parts.
- **The clause text is fixed by the approved spec.** Reproduce it verbatim from this plan. Do not rewrite, condense, or "improve" the wording.
- **No environment-specific values** in any committed file (no absolute machine paths, personal profiles, hostnames).
- Commit messages explain **why**, not just what. No Claude credits.
- The `test-audit` skill is **out of scope**. Its Coverage-dimension update is deferred to the wave-1 sweep. Do not edit `.agents/skills/test-audit/`.

---

### Task 1: Handbook clause and matrix row

**Files:**
- Modify: `docs/engineering/implementation-disciplines.md` (insert at line 30, after the `### Chase caught regressions, not coverage percentage` subsection ends and before `## Prompt and SOP engineering`)
- Modify: `docs/audit/handbook-traceability.yaml` (add a row after `implementation-disciplines/tdd-b`, before `implementation-disciplines/prompt-and-sop-engineering-a`)
- Regenerate: `docs/audit/handbook-traceability.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: matrix row id `implementation-disciplines/tdd-c`. Task 2 does not depend on it.

**Ordering note:** the new subsection goes *after* "Chase caught regressions, not coverage percentage", not before. The reader must meet the "do not chase the number" caveat before the "state a floor" requirement, otherwise the clause reads as the number-chasing that subsection warns against.

- [ ] **Step 1: Insert the handbook subsection**

Insert at line 30 of `docs/engineering/implementation-disciplines.md`, preserving one blank line before and after. Each paragraph is a single unwrapped source line.

```markdown
### Decide the unit-test coverage floor upfront, and record it where it runs

Unit-test coverage, the proportion of your code that the test suite actually executes, is the number everyone asks for and no handbook can supply: 90% on a thin CRUD service and 90% on a parser mean different things. So this handbook names no percentage, and requires the *decision* instead. State a required floor, state what that floor is measured over, and put both somewhere that executes, the coverage config or the CI gate rather than a wiki page. An unstated floor is not a lenient one, it is an unfalsifiable one: it turns "is 62% good?" into a question nobody can answer, and leaves every later argument about coverage to whoever cares most that day.

The denominator is part of the decision, because a floor without one says nothing: 80% measured over a source tree that quietly excludes the parsers is not 80%. Exclusions are a stated choice, and load-bearing deterministic logic is never a legitimate one. Justify a deliberately low floor rather than leaving it unexplained; a nice-to-have target above the floor is optional, as long as the floor is what CI enforces.

A whole-project floor is the minimum, not the strong form. Pair it with a floor on the changed lines, which the whole-project number cannot substitute for: against a large well-covered base, an entire feature can ship untested before the aggregate number moves.
```

- [ ] **Step 2: Verify no em-dash was introduced**

Run: `grep -n $'—' docs/engineering/implementation-disciplines.md`
Expected: no output (exit 1 from grep is success here).

- [ ] **Step 3: Add the matrix row**

Add to `docs/audit/handbook-traceability.yaml`, immediately after the `implementation-disciplines/tdd-b` row and before `implementation-disciplines/prompt-and-sop-engineering-a`:

```yaml
- id: implementation-disciplines/tdd-c
  section: "TDD"
  claim: Decide the unit-test coverage floor upfront rather than assuming a number - state a required floor and what it is measured over, record both somewhere executable (coverage config or CI gate) rather than aspirational, treat exclusions as part of the decision and never exclude load-bearing deterministic logic, justify a deliberately low floor, and pair the whole-project floor with a floor on changed lines.
  class: static
  severity: important
  checks:
    - skill: test-audit
      dimension: "Coverage reach"
```

Note: `class: static` because a stated floor is readable from a config snapshot. `severity: important` matches the sibling `tdd-b`. The `dimension` string must match `test-audit`'s dimension heading exactly, because `validate()` cross-checks it against the skill file; `"Coverage reach"` is correct and is already used by `tdd-b`.

- [ ] **Step 4: Validate the matrix before regenerating**

Run: `uv run python scripts/render_handbook_traceability.py --check`
Expected: FAIL, reporting `handbook-traceability.md is stale`. This confirms the row parsed and validated (a schema or dimension error would print a different message and must be fixed first).

- [ ] **Step 5: Regenerate the rendered matrix**

Run: `uv run python scripts/render_handbook_traceability.py`
Then: `uv run python scripts/render_handbook_traceability.py --check`
Expected: exit 0.

- [ ] **Step 6: Run the documentation gates**

```bash
uv run mkdocs build --strict
uv run python scripts/check_site_links.py site
uv run scripts/render_handbook_artifact.py --out /dev/null
```
Expected: all succeed. (`docs/engineering/` is excluded from the site build, so the artifact render is the gate that actually exercises the changed file.)

- [ ] **Step 7: Run the matrix unit tests**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add docs/engineering/implementation-disciplines.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md
git commit -m "docs(lidia-tech/lidia-agents#551): require deciding the unit-test coverage floor upfront"
```

The message body must explain why the clause requires the decision rather than a number, and why it sits after "Chase caught regressions".

---

### Task 2: Adopt a coverage floor for this project

**Files:**
- Modify: `pyproject.toml` (`[tool.coverage.report]`, currently at line ~146)

**Interfaces:**
- Consumes: nothing. Independent of Task 1.
- Produces: an enforced CI coverage gate.

**Context the implementer needs:** CI runs `uv run pytest tests/ --cov=lidia_agents ... | tee` under `set -o pipefail` (`.github/workflows/ci.yml`). `pytest-cov` honours `fail_under` from `[tool.coverage.report]`, so this one line turns on the gate with no workflow change. Current measured coverage is 66.67% (14610/21914 statements). The existing `omit` is tests-only, which is an honest denominator and must not be widened.

- [ ] **Step 1: Add the floor**

In `pyproject.toml`, change:

```toml
[tool.coverage.report]
show_missing = true
```

to:

```toml
[tool.coverage.report]
show_missing = true
# The handbook requires a stated, executable floor (Part 2, "Decide the
# unit-test coverage floor upfront"). Set below the measured 66.67% on
# purpose: a floor pinned tight against current coverage reddens CI on
# ordinary variation rather than on a real regression, and a gate that
# fires on noise gets raised or ignored. The "do not lower coverage" rule
# catches the slow slide; this catches the cliff.
fail_under = 65
```

- [ ] **Step 2: Verify the gate is wired and currently passes**

Run: `uv run pytest tests/ --cov=lidia_agents --cov-report=term-missing -q`
Expected: PASS, with a `Required test coverage of 65% reached` line (or no coverage failure). Record the reported total.

- [ ] **Step 3: Verify the gate actually bites**

Temporarily set `fail_under = 99`, re-run the command from Step 2, and confirm it now FAILS with a coverage error. Then restore `fail_under = 65` and re-run to confirm PASS.

This step exists because a threshold that is never observed failing is indistinguishable from one that is not wired up. Do not skip it, and do not commit the temporary value.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore(lidia-tech/lidia-agents#551): adopt a stated unit-test coverage floor of 65%"
```

The message body must state the measured coverage, why the floor sits below it, and that CI needed no workflow change.

---

## Self-review notes

- **Spec coverage:** clause text (Task 1 Step 1), matrix row with severity (Task 1 Step 3), dogfooded floor (Task 2), `test-audit` deferral (Global Constraints, out of scope). All four issue acceptance criteria are reachable.
- **No new Python code**, so the "new code ships with tests" rule adds no work here; the matrix validator plus its existing test file are the safety net, and Task 2 Step 3 supplies the negative test for the new gate by observation.
- **Type consistency:** the only cross-artifact identifier is the matrix `dimension` string `"Coverage reach"`, which must match `test-audit`'s heading and is validated mechanically by `--check`.
