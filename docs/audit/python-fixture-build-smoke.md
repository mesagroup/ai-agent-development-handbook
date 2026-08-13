# Python fixture build smoke

The five seeded Python fixture partitions were generated, and every planted seed was put in front of a tool to see whether anything reports it. This record is what happened on **2026-08-14**. It is the gate on the fixture machinery rather than the verification round: it answers whether the fixtures can produce their own ground truth, so that the round which grades the `python:` tooling entries starts from a fixture that works instead of discovering that it does not.

**No check record is corrected on this evidence, and none was read for correction here.** The tools below were run directly, one per seed, chosen for the seed rather than transcribed from any record's prescribed command. Whether each record's own invocation answers its own check, under both grant states, is the round that follows, and a correction made here would be a correction with no graded observation behind it - the failure the round exists to remove. The one thing this record settles for the family is the shuffle seed, which is measured and cannot be derived.

The subject is the **fixture set**, the same way [the TypeScript lens smoke run](typescript-lens-smoke-run.md)'s subject is the skill family. Nothing here is a finding about any audited codebase.

## What was built

`uv run python scripts/build_python_fixtures.py --all` wrote all five partitions and printed the tracked file count for each. The generator refuses to return from a tree whose `git status --porcelain` is non-empty and compares each tree's own `git ls-files` against `committed_files(partition)`, so a build that returns has already asserted both.

| Partition | Tracked files | Lock artifact | Manager |
|---|---|---|---|
| `uv` | 17 | `uv.lock` | `uv 0.10.7`, from the host that ran the generator |
| `pip` | 17 | none | none; `requirements.txt` pins the declared set with `==` and the partition has no separate lock format |
| `poetry` | 17 | `poetry.lock` | `poetry@2.4.1`, pinned by the generator |
| `pipenv` | 18 | `Pipfile.lock` | `pipenv@2026.7.1`, pinned by the generator |
| `pylock` | 17 | `pylock.toml` | `uv 0.10.7`, from the host; the `uv.lock` the export reads is deleted before the commit |

`pipenv` carries one file more than its neighbours because it renders both a `Pipfile` and the `setup.py` that lets the src-layout package install without declaring a second copy of the dependency set. The host toolchain was **Python 3.12.10** and **uv 0.10.7**. `git status --porcelain` was empty in all five trees before this smoke and empty in all five afterwards, and `git status --short` at the handbook repository listed nothing, the fixture root being gitignored.

Every tool below ran against a **copy** of the `uv` partition made in a scratch directory outside the fixture root, materialized there with `uv sync --frozen`. Nothing resolved, installed or wrote inside a fixture tree, which is the same read-only invariant an audit run is held to against a real target.

## The measured shuffle seed

This is the one value the fixture definition cannot state, because it is a property of `pytest-randomly`'s ordering rather than of the seeded source. `tests/test_order.py` holds two tests that pass in file order and fail when reversed; a seed that reverses them has to be found by running them.

**Seed 4**, measured with:

```
uv run --frozen --with pytest-randomly pytest tests/test_order.py -p randomly -q --randomly-seed=4
```

under **pytest 9.1.1**, **pytest-randomly 4.1.0** and **Python 3.12.10**, the plugin versions resolved unpinned by `--with` on the date above. It is the smallest seed in 0..60 that fails. The failure is the seeded assertion and nothing else - `test_reads` runs first and asserts `[] == [1]` - which is what distinguishes a measured seed from any non-zero exit a collection or environment error would also produce. The same file passes at exit 0 both with the plugin disabled (`-p no:randomly`) and with the plugin absent.

**The seed is reproducible only under the recorded plugin version.** On `pytest-randomly` 3.15.0 and 3.16.0 seed 4 leaves the pair in file order and both tests pass; the smallest reversing seed on each of those is 0. So the number is not a stable property of the fixture and must not be quoted without the versions beside it. What is stable is that reversing seeds are common rather than rare: 32 of the 61 seeds in 0..60 reverse the pair under 4.1.0, so a run that finds no order dependence at one arbitrary seed has established very little.

## Every seed, and what saw it

22 distinct seeds are planted: 17 carried by the seeded source files and 6 by the dependency set, with `undeclared-import` carried by both. Both counts were computed from `SOURCE_FILES` and `DEPENDENCIES` in `scripts/python_fixture_spec.py` rather than counted by hand.

**21 of the 22 were observed** - by a tool, or by the reading pass their own check record prescribes in place of one. The exception is `mutation-survivor`, which is the subject of the next section.

| Seed | Tool | What came back |
|---|---|---|
| `complexity` | ruff 0.16.3, radon 6.0.1, xenon 0.9.3 | `C901 classify is too complex (12 > 10)`; radon rates `classify` **C (13)**; xenon exits 1 on `--max-absolute B`. All three thresholds cleared, as the expectations record predicts for each |
| `dangerous-calls` | ruff 0.16.3, bandit 1.9.4 | `S307` / `B307` on the `eval` in `unsafe.py:8` |
| `injection` | ruff 0.16.3, bandit 1.9.4 | `S602` / `B602` on `shell=True` at `unsafe.py:12`, and `S608` / `B608` on the built SQL at `unsafe.py:20` |
| `crypto` | ruff 0.16.3, bandit 1.9.4 | `S324` / `B324` on the md5 digest at `unsafe.py:16` |
| `unsafe-io` | ruff 0.16.3, bandit 1.9.4 | `S202` / `B202` on `extractall` at `unsafe.py:25`, and `S314` / `B314` on the bare `xml.etree` parse at `unsafe.py:29` |
| `undocumented` | ruff 0.16.3, interrogate 1.7.0 | `D100` names `unsafe.py` and, over the whole tree, three test modules; interrogate puts `unsafe.py` at **0% of 7** and the package at **25.0% of 24**, failing its own 80% floor |
| `cycle` | grimp 3.15 | a chain in each direction between `fixture_app.domain.model` and `fixture_app.infra.store`, over a graph of 10 modules |
| `layering` | import-linter 2.13 | `Contracts: 0 kept, 1 broken` |
| `pass-through` | reading pass | `domain.model.load` forwards to `infra.store.read`, and `infra.store.load_via_domain` forwards to `domain.model.load`; both function bodies are a single `return` of the other module's call |
| `dead-code` | vulture 2.16 | `never_referenced` among 10 unused functions at 60% confidence, which the expectation's floor form anticipates |
| `single-caller` | vulture 2.16, reading pass | `never_referenced` has zero call sites per vulture; `clamp` has exactly one, at `tests/test_partial.py:5`, where `low` and `high` are bound to `0` and `10` and to nothing else |
| `property-gap` | reading pass | no `hypothesis` import and no `@given` anywhere under `src/` or `tests/` |
| `undeclared-import` | deptry 0.25.1 | `DEP003 'markupsafe' imported but it is a transitive dependency` at `render.py:7` |
| `declared-unused` | deptry 0.25.1 | `DEP002 'six' defined as a dependency but not used in the codebase` |
| `vulnerable` | pip-audit 2.10.1 | **5 advisories against jinja2 3.1.2**, counted as PYSEC ids, whose aliases are exactly the five CVEs the expectation's floor names |
| `copyleft` | pip-licenses 5.5.5 | `Unidecode 1.4.0` under `GNU General Public License v2 or later (GPLv2+)` |
| `transitive-root` | pip-licenses 5.5.5 | `MarkupSafe 3.0.3` present with a licence (`BSD-3-Clause`), never declared and arriving through jinja2 |
| `stale` | uv 0.10.7 | `uv pip list --outdated` names jinja2 (3.1.2 to 3.1.6), packaging (20.9 to 26.3) and six (1.10.0 to 1.17.0), and **does not name Unidecode**, so the false-positive control holds |
| `uncovered-branch` | pytest-cov 7.1.0, coverage 7.15.4 | `invariant.py` at **60%**, lines 6 and 8 missing with 2 partial branches - `clamp`'s two guards - against 15% over the package |
| `order-dependence` | pytest-randomly 4.1.0 | the measured seed above |
| `slow-test` | pytest-timeout 2.4.0, pytest 9.1.1 | `Failed: Timeout (>1.0s)` on `test_slow_but_passing` under `--timeout=1`; `--durations` reports **2.01s** for it and the suite passes with no timeout configured |
| `mutation-survivor` | mutmut 3.7.0 | nothing - see below |

Three seeds are answered by a reading pass rather than by a tool, and that is what their expectations ask for: `pass-through`, `single-caller` and `property-gap` are all named in check records whose Python fallback requires a read before a count becomes a finding. The read is recorded above as the observation, not as a substitute for one.

Two details that would otherwise read as the wrong result:

- **The import-linter contract was written for this smoke**, since the fixture carries no `.importlinter` and one that shipped with it would be the check's own input rather than the fixture's. The contract puts `fixture_app.domain` above `fixture_app.infra`, so the edge it names as broken is `infra.store -> domain.model`. The mutual cycle means both edges exist, so a contract in either orientation breaks; the direction in the output is the one the contract chose, not a disagreement with the expectation's `domain -> infra` reading.
- **`deptry` was run from inside the materialized environment**, which is what makes markupsafe DEP003 rather than DEP001. Alongside the two seeds it reported the 2 further DEP003 rows naming `fixture_app`'s own modules that the expectations record predicts for a src-layout package, and no others - 4 issues in total, exactly the set written down in advance.

## What the smoke found

### `mutmut` cannot establish a baseline on this fixture, for two independent reasons

`mutmut run` is the command `test/mutation` prescribes for Python. On the `uv` partition it never reaches a mutant. It fails during its clean-test stage with:

```
tests/test_order.py::test_appends - assert [1, 1] == [1]
```

The module-level `_SEEN` list that carries the `order-dependence` seed has accumulated two entries, so `test_appends` ran twice in one process. This is mutmut's own execution model rather than anything about the collection: pytest given the same file twice deduplicates it and both tests pass. So **the `order-dependence` seed blocks the `mutation-survivor` seed**, and the interaction is a property of the two seeds meeting mutmut, not of either seed being wrong.

A second blocker sits behind the first. In a **modified copy** made outside the fixture - `tests/test_order.py` deleted and a `[tool.mutmut]` section added scoping `paths_to_mutate` to `invariant.py`, neither of which was done to any fixture tree - mutmut got past the baseline and failed differently: it copies the tree into a `mutants/` directory and runs from there, and the test modules then cannot import the package.

```
ImportError: cannot import name 'render' from 'fixture_app' (unknown location)
```

`mutants/src/fixture_app` exists in that copy, so the directory is there and is not on the import path that run uses. The apparent cause is that the src-layout package is installed editable pointing at the original `src/`, which `uv pip list` confirms, leaving `fixture_app` resolvable to the original location and not to the mutated one; that explanation is inferred from the error and the layout rather than measured. Either way the observation stands on its own: with the first blocker removed, `mutmut run` still produced no mutant here.

Neither blocker is a malformed fixture. Both are mutmut 3.7.0's execution model meeting properties the fixture plants on purpose - an order-dependent test pair, and a src layout that the `FIXTURE.md` written into every tree explains at length - and both would reproduce on a real target with the same two properties. So the seed stays: removing it would erase the evidence that the family has a hole here. `cosmic-ray`, the other tool `test/mutation` names, was not run, for the reason the harness already records against it - the record names it with no subcommand, and a session config written to make it run would be manufactured input rather than a transcription.

### The expectations written in advance held wherever a tool answered

Nothing in the 21 detected seeds contradicted [the expectations record](python-fixture-expectations.md). The cases where an exact prediction could have been wrong and was not are worth naming, because they are the ones that would have sent the following round to correct a record that was right: ruff's 12, radon's C at 13 and xenon's failure on `--max-absolute B` are each what that entry predicts for that engine; deptry's four rows are the two seeds plus the two src-layout artefacts and nothing else; `uv pip list --outdated` leaves Unidecode out, which is the whole reason a latest-release package is in the dependency set; and pip-audit's five advisory ids alias to the five CVEs the floor names.

This is a weaker claim than it looks and is stated as such. These tools were pointed at the seeds directly. Whether each record's own prescribed command, run under the grant state that record's `needs` tiers imply, reaches the same output is a different question and is the one the following round asks.

## Still open

- **The results file's `materialization` block is what a reader checks first.** The harness runs a partition's invocations whether or not its materialization step succeeded: a materialization that fails partway does not stop the run, and the invocations then execute against an unmaterialized copy. Every tool tiered `resolved-tree` or `target-execution` will report something in that state, and what it reports is not evidence about the fixture. So a row in `<partition>-<grant>.json` is only readable once the `materialization` block above it shows every command at exit 0. Reading the rows first is how a run that resolved nothing gets recorded as a family finding.
- **Only the `uv` partition was smoked for seeds.** The other four were built, verified against their planned file sets and left clean, and they carry the same seeded source, but no tool was run against `pip`, `poetry`, `pipenv` or `pylock` here. Those partitions exist to ask the dependency records a different question per manifest and lock format, and that question is asked in the following round.
- **Both grant states remain unrun.** Everything above was measured with the tree resolved. The ungranted answers written down in the expectations record - the `deps/hygiene` DEP001-versus-DEP003 split most sharply - have not been observed, and they are the half where a correct run graded against the granted answer reads as a tool defect.
- **`test/mutation` is expected to go unmet on the `uv` partition.** The harness holds `mutmut run` verbatim, so it will fail at the baseline for the interaction recorded above. That is the anticipated outcome of a known seed collision and should be read as such rather than as a fresh tool defect found by the run.
- **The shuffle seed will need re-measuring when the plugin moves.** It is recorded here with the three versions it was measured under, and it is already known to differ across `pytest-randomly` majors. Nothing fails when it goes stale, which is what makes this a dated record rather than a gated one.
