# Plan: `deptry` runs in CI

Issue #14. Design: [../specs/2026-09-10-deptry-becomes-a-gate-design.md](../specs/2026-09-10-deptry-becomes-a-gate-design.md).

In the order that keeps the tool clean at every step: teach it the layout first, then declare it, then gate on it, then hold all three with tests.

## 1. `pyproject.toml` teaches it the layout

`[tool.deptry]` with `known_first_party` naming every module stem in `scripts/`, not only the four that trip the rule today - a module there is first-party by construction, and a list of what is imported this week would fail CI on the next sibling import.

`deptry` joins the `dev` dependency group in the same edit, so the gate's version comes from the lockfile rather than from whatever the index serves at run time.

Then re-run it: the eight DEP001s should be zero, and `DEP002` should stay at zero rather than `deptry` flagging itself for never being imported.

## 2. `.github/workflows/ci.yml` gates on it

One step, `uv run deptry .`, beside the other integrity gates rather than inside the lint step, because a reader scanning the job should see what each gate answers. A comment records that the whole report lands on **stderr** with an empty stdout, which `deps/hygiene` measured and this branch re-verified, so a later edit does not pipe it somewhere and silence the gate while leaving it green.

The `check` job keeps its name. Branch protection and the check-set comparison both read it.

## 3. `tests/test_deptry_gate.py` holds the three things that can rot

- **The first-party list covers `scripts/`.** Parsed from `pyproject.toml` and compared against the directory, so adding a script without naming it fails here rather than in CI on someone else's branch.
- **The workflow invokes the tool.** A configuration nothing runs is the state this issue exists to end, and it is invisible once the config looks right.
- **The gate is non-vacuous.** Copy the project to a temporary directory, undeclare a dependency the code imports, run `deptry` there, assert it exits non-zero and names the module. Criterion 3's demonstration made permanent instead of performed once. Which finding code comes back depends on whether the removed dependency is still installed in the caller's environment, so the test asserts neither. What catches `known_first_party` being widened to swallow a real third-party name is the equality check rather than this one, since an exempted name is one that matches no module in `scripts/`.

## 4. `deps-audit/checks/hygiene.md` gains one clause

Not because the configuration changed what the check reads - it did not - but because operationalising the tool surfaced a fact an auditor needs and the record lacks: `deptry` reports a sibling module imported as a top-level name as a missing dependency, which on a target whose scripts sit on `sys.path` is false. This repository is the worked instance at eight occurrences.

## 5. Gates and the prose pass

`uv run pytest tests/ -q`, `ruff check`, `ruff format --check`, both integrity renderers with `--check`, and `uv run deptry .` clean.

Then the stale-prose pass, dispatched to a subagent that has not seen the implementation and given the worktree root to confirm, scoped to every sentence that says what CI runs or enumerates this repository's gates - `CLAUDE.md`'s commands block first, since that set just grew.
