# `deptry` becomes a gate, and the layout it has to be taught

Issue #14. `deps/hygiene` prescribes `deptry` and nothing in this repository runs it, so the check that would have caught the extraction's own undeclared `markdown` import only fires when a human invokes the skill.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate. Every decision below records the alternative it rejected and how it was settled, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## Four measurements, taken before designing anything

**The blocker is four times the size the issue states.** #14 names one false positive. Run on `main`, `deptry` reports **eight DEP001s across five files, naming four distinct modules**: `audit_checks`, `build_python_fixtures`, `python_fixture_spec` and `run_python_fixture_lens`. Every one is a sibling in `scripts/`, imported as a top-level name because `scripts/` is `sys.path[0]` at runtime and is put on the path by `tests/scripts/conftest.py` under pytest. The diagnosis in the issue is exactly right and its instance list was partial, so the configuration has to describe the layout rather than the one name.

**`deptry` exits 1 when it finds something**, so it needs no wrapper to work as a gate step.

**Widening the scan to `tests/` is wrong, and this is measured rather than argued.** `deptry`'s default excludes carry `tests`. Removing it produces 29 issues instead of 8: the first-party DEP001s the configuration fixes, plus **eight DEP004s calling `pytest` a misplaced dev dependency** - which is `deptry` treating the test suite as production code, exactly what the default exclude prevents. So the gate covers `scripts/` because that is correct, and the limit belongs in the PR body rather than left for a reader to assume away.

**Nothing is reported as an unused declaration today**, so declaring `deptry` in the dev group will not make it flag itself for never being imported. Re-checked after adding it rather than trusted.

## The record's own measurements were right, and they decide how CI invokes it

`deps-audit/checks/hygiene.md` says `deptry` "reads installed distribution metadata, so it must run inside the project's own environment", carries `in_env: true` and `needs: resolved-tree`, and warns that `deptry .` "exits 1 with an empty stdout and its whole DEP002/DEP001 report on stderr, so a caller reading stdout, or treating the non-zero exit as the tool having failed, loses a real finding rather than an absence of one".

Both verified here: zero bytes on stdout, all eight findings on stderr. So the CI step declares `deptry` in the dev group and runs `uv run deptry .` inside the synced environment, which is the `in_env` shape the record prescribes and is pinned by the lockfile. Rejected: `uv run --with deptry deptry .`, which works but resolves the tool at run time, so the gate's version drifts with the index rather than with the lockfile - the same objection the runner rule makes to fetching a tool a project could declare.

## `known_first_party` names every module in `scripts/`, and a test keeps it that way

The configuration lists all eight module stems in `scripts/` rather than only the four that currently trip the rule. A module in `scripts/` is first-party by construction, so a list of what happens to be imported today would be a snapshot, and the next sibling import would fail CI for a defect that does not exist.

That list is still a second copy of the directory, so a test holds it against the directory: adding a script without adding its name fails. This is the consistency property moving into the validator, which is what this repository does with such lists rather than trusting a reviewer to notice.

## Criterion 3 is satisfied by a test rather than by a red CI run, and that is a substitution to record

The criterion asks to "undeclare a dependency, watch CI fail, restore". Done literally that is three pushes, two extra reviewer cycles, and a red check run left in the PR's history that reads as a broken branch - and it proves the gate worked **once, on one commit**.

So the non-vacuity check is a test: it copies the project to a temporary directory, removes a declared dependency the code imports, runs `deptry` there, and asserts it exits non-zero and names the module. It asserts no particular finding code, because whether the removed dependency is still installed in the caller's environment decides between `DEP003` and `DEP001`, and that is a fact about the caller rather than about the gate. It runs on every push rather than once. The other way a gate like this dies - `known_first_party` widened until it swallows a real third-party name - is caught by the equality check against `scripts/` instead, since an exempted name is one that matches no module there.

The manual demonstration was also run locally and its output is in the PR body, so the criterion's own evidence is on the record. What is *not* claimed is a red CI run: if that specific artifact is wanted it is one commit away, and the PR body says so rather than implying the test is what the criterion asked for.

## One record edit, for a reason the criterion did not anticipate

Criterion 4 asks for `deps/hygiene` to be updated "if the configuration changes what the check reads". The configuration changes what `deptry` reports **in this repository** and nothing about what the check reads in a target, so on its own terms the answer is no.

What operationalising it did surface is a fact about the tool that an auditor needs and the record does not carry: **`deptry` reports a sibling module imported as a top-level name as a missing dependency**, and on a target whose scripts sit on `sys.path` that is a false finding rather than a hygiene defect. This repository is now the worked instance, at eight occurrences. A record whose note already measures deptry's exit code and output stream is the right place for it, and reporting those DEP001s as findings about a target would be the same class of error the note's stdout warning prevents.

## What changes

- **`pyproject.toml`**: `deptry` joins the dev group; a `[tool.deptry]` section names every module in `scripts/` as first-party.
- **`.github/workflows/ci.yml`**: a `Dependency hygiene` step running `uv run deptry .`, placed with the other integrity gates, with a comment recording that the report lands on stderr so a future edit does not redirect it away.
- **`tests/test_deptry_gate.py`**: the first-party list covers `scripts/`, the workflow actually invokes the tool, and the gate is non-vacuous.
- **`.agents/skills/deps-audit/checks/hygiene.md`**: one clause on the first-party false positive.

## What this does not do

- **It does not scan `tests/`**, for the measured reason above.
- **It does not add a lockfile-drift or licence gate.** `deptry` answers unused, missing, transitive and misplaced; the other `deps` checks are the skill's to run.
- **It does not change any other CI job or the `check` job's name**, which is what the branch protection and the reviewer comparison read.

## Verification

The four gates, the new tests, `deptry` itself clean on this branch, and a stale-prose pass by an agent that has not seen the change - scoped to every sentence that says what CI runs or that lists the repository's gates, since that set just grew.
