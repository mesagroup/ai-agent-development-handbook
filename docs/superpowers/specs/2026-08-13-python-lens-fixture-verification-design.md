# Seeded Python fixtures for the audit lens - design

Issue #45, under epic #44.

## Problem

Every `python:` tooling entry in the skill family was authored from the tools' own documentation and has never been executed. The [TypeScript lens smoke run](../../audit/typescript-lens-smoke-run.md) is what happened when the `typescript:` and `any:` entries were finally run: it corrected the majority of them, and its second target - a pnpm workspace, after an npm one - corrected four further claims that no npm target could have exposed, including one defect the npm half's own fix had introduced. That settles the general principle for this repository: a tooling entry is unverified until a partition using that package manager has run it.

Computed from the tree at the time of writing: **26 check records carry a `python:` entry, across 5 domains, naming 27 distinct tools.** None has ever run.

This round closes that with seeded fixtures rather than by waiting for a real target of each kind to appear. A fixture has planted ground truth, so completeness becomes checkable: against a real repository an audit can only ask whether a command ran and returned something plausible, and a tool that runs cleanly while reporting half the truth passes. That is the defect class this exercise keeps finding - `pnpm outdated` reporting 10 of 254 declared dependencies looked exactly like success.

## Scope decisions

Three decisions were taken before design, and each widens or narrows what follows.

**Every `python:` entry, family-wide.** Issue #45's acceptance criteria name `arch`, `deps`, `test` and `security`, which misses `docs-audit/docstring-coverage` and its `pydocstyle` and `interrogate` entries, and never lists `tach`, `vulture` or `safety`. The TypeScript round's four-domain scope was not a decision to exclude `docs`: that domain has no `typescript:` entry to run. Scope here is all 26 records and all 27 tools, so the family is closed rather than four fifths of it.

**One full fixture, four deps-only fixtures.** Only the deps commands and the tree-materialization route are package-manager-sensitive. Every correction the pnpm round produced was a deps command or a repository layout, and none touched the equivalents of `ruff`, `bandit` or `pytest`. So the uv fixture carries the whole 27-tool matrix under both grant states, and the `pip`, `poetry`, `pipenv` and `pylock` fixtures carry the six `deps` records plus one non-deps tool each, which exists to prove that partition's own materialization route works rather than to re-test the tool. That tool is `pytest-cov`, chosen because it is tiered `target-execution` and therefore fails if either half of the route is broken: it needs the tree materialized by that partition's manager, and it needs the target's own suite to run against it.

**Two PRs.** The build phase is deterministic and its size is known; the run phase's size is not knowable until the run happens, and #29's correction rate suggests most of the 26 records get touched. PR 1 is the generator, the spec module, the expectations record and the harness. PR 2 is the run, the corrections and the verification record.

## Architecture

Four committed units, no new runtime code path. The fixture trees themselves are never committed.

### `scripts/python_fixture_spec.py` - the definition

A pure module. It holds one logical dependency set, one set of seeded source findings, the rendering of both into five manifest formats, and the expected result per check per fixture.

The fixture tree and its expectations are produced from this same definition. That is the point of the module rather than an implementation convenience: expectations kept in a second file are free to drift from the tree, and a seeded finding present in the tree but absent from the expectations reads exactly like a tool that correctly found nothing.

Pure, so `tests/scripts/` can exercise it, per the repository's rule that scripts are not exempt from unit tests. It shells out to nothing.

### `scripts/build_python_fixtures.py` - the generator

Effectful. Writes `fixtures/python/<partition>/` for the five partitions, into a gitignored directory. Committed as a script rather than described in prose, per #44's constraint: a scratch directory does not survive a session and this work spans several.

**Each fixture is a git repository with everything committed.** Two reasons, both load-bearing. Semgrep limits its scan to files tracked by git and says so only in a note, so an untracked fixture tree would make all four `security` checks pass vacuously - the exact false clean this exercise exists to catch. And `git status --porcelain` empty before and after, which #44 requires as the read-only check, is only meaningful inside a repository.

**Each fixture is provisioned from its own pinned manager, with one stated exception.** Python has no `corepack`, so the generator states its route per partition rather than using whichever manager the machine happens to carry, and records the version it used. The exception is `uv` itself, which is how the generator runs at all: pinning a second copy of it through a one-shot runner would exercise a uv no caller of the script uses, so the host's uv is used and its measured version recorded in every tree it builds. Every other manager is pinned.

The trees are pure outputs: regenerating replaces them, and nothing reads state that only a previous run could have written. A fixture directory is therefore disposable, which also keeps this clear of the hazard where ignored paths exist only in the checkout that created them.

### `scripts/run_python_fixture_lens.py` - the harness

Manually invoked. Never runs in CI: `cdxgen` alone took about nine minutes on the TypeScript target, mutation runs take minutes each, and every entry here needs network.

Its command table holds **each record's prescribed invocation verbatim**, keyed by check id. This is the design's main mechanism rather than a convenience. A person running the tools by hand naturally fixes a broken command as they go, and the fix then never reaches the record. Where the harness has to deviate from what the record prescribes in order to make a tool work, that deviation is the finding, and it is visible as a diff against the transcribed command.

The transcription is guarded rather than trusted: a test asserts that every `python:` tool named in every record appears in the harness table exactly once, in the style of the existing `test_a_tool_has_one_tier_across_the_family` guard. A tool added to a record and forgotten here fails the suite instead of silently going unexercised.

Command construction, result classification into the engine's vocabulary (`ok`, `no-evidence` with its reason, `not-applicable`), and matching an observation against an expectation are pure helpers and are unit-tested. The shelling out is not.

### `docs/audit/python-fixture-expectations.md` - the expectations record

Generated from the spec module, with a `--check` gate, in the same shape as the traceability matrix: edit the module, re-render, never edit the Markdown. #44 requires the expected count written down before the run, and a generated table makes it reviewable in PR 1 without committing a single fixture tree. The `--check` gate is what stops the table and the module drifting apart afterwards.

It is listed in [`docs/audit/README.md`](../../audit/README.md), which distinguishes standing records from verification records. This one is a standing record: it tracks the current definition, unlike the smoke-run record, which is a dated finding about tool behaviour.

## The shared dependency set

All five partitions declare the same logical set, expressed in five manifest formats, so the expectations are written once and every fixture diffs against the same ground truth:

- a **known-vulnerable pin**, for `deps/vulnerabilities`, recorded with the advisory id that must appear
- a **stale pin** several majors behind current, for `deps/freshness`
- a **copyleft-licensed package**, for `deps/licenses` and `deps/transitive-licenses`
- a **declared but never imported** dependency, for `deps/hygiene`
- an **imported but never declared** dependency, for the same check's other direction
- **transitive depth of at least two**, so `deps/transitive-licenses` has a question distinct from its direct sibling

The specific packages are chosen and verified when the generator is written, against the advisory database and against PyPI's own licence metadata. This document does not name them, because a package named here from memory is exactly the unverified claim the exercise exists to eliminate.

The vulnerable and stale pins live in generated, gitignored trees rather than in a committed manifest, so they raise no dependency alerts against this repository.

## The seeded source findings

One per domain lens, and **designed so that a default `pytest` run is green**. That constraint is load-bearing rather than tidy: `mutmut` requires a passing baseline suite, and a single failing test would poison the mutation, coverage and isolation results at once.

So the order-dependent pair is green in file order and fails only under a **named `pytest-randomly` seed**, recorded in the expectations. The slow test passes and merely exceeds a chosen `pytest-timeout` threshold. The surviving mutant lives in a function the suite calls but under-asserts.

The rest: a function over the complexity threshold; a two-module import cycle and a layering violation, for the graph tools; an unreferenced function, for `vulture`; `eval` on a variable, a `shell=True` subprocess, a string-formatted SQL query and an `md5` digest, for the four `security` checks; a public API with a known documented fraction, for `interrogate` and `pydocstyle`; an unreached branch, for a known coverage percentage; a function with an obvious invariant and no property test, for `test/property-based-gap`; and **no configured complexity threshold anywhere**, so `arch/complexity-gate`'s expected finding is an absence rather than a hit.

**Where a count is tool-version-dependent, the expectation is a location and a floor rather than an exact number.** Surviving mutants are the clearest case: the count moves with the mutation operator set, so "at least one survivor in this function" is a claim a later tool version cannot falsify for the wrong reason, and an exact number is one that goes stale silently. Exact counts are used only where the tool is deterministic about them.

**A seeded finding that no tool detects is a finding about the family, not a bug in the fixture.** It is recorded as such rather than removed, and the fixture keeps the seed.

## Grant states

Two: ungranted, and `target-execution`.

A `resolved-tree`-only state is deliberately not run, because it would produce identical output to the granted state for every tool it applies to. `target-execution` implies `resolved-tree` and the tree is materialized in both, so the only difference between the two granted states is whether the target's own suite runs - which no `resolved-tree`-tiered tool does. The TypeScript round ran the same two states for the same reason.

Both states are run for every entry, so each `ungranted_note` is tested as a separate claim from each `needs` tier rather than assumed.

## Read-only discipline

`audit-core` bars installing into the target under any grant, and the fixtures are treated as targets rather than as scratch:

- `git status --porcelain` at the fixture is confirmed empty before and after every run
- the tree is materialized in a copy that does not resolve under the fixture root, never in the fixture
- a package a check needs for itself goes into a copy that check owns, never into the shared materialized tree, because a package the audit added is never evidence about the target
- lock files are read, not refreshed: `uv export --frozen` rather than the default, and the equivalent for each other manager

## The three named holes

Beyond executing 27 never-run tools, the round is expected to settle three specific claims. Each is stated here as a candidate to test, never as a conclusion.

**`deps/inventory` has no uv route.** It prescribes `cyclonedx-py`'s `requirements`, `poetry` or `pipenv` subcommand, matching the partition's own dependency file. There is no uv subcommand among them, so a `uv.lock` partition has no stated SBOM route that works on a read-only clone - and uv is the ordinary modern layout. `uv export --format cyclonedx1.5 --frozen` is the candidate, and the record's own text already allows "the tool's native SBOM export" while prescribing only the `cyclonedx-py` subcommands. `uv 0.10.7` offers that format; whether its output satisfies what the record asks an SBOM for is what the run establishes.

**`deps/vulnerabilities` writes off uv targets.** The record states that `pip-audit --locked .` reads a PEP 751 `pylock.*.toml` "and nothing else", which leaves a uv-locked partition with no vulnerability lens on a read-only clone. `uv export --frozen --format requirements.txt` piped into `pip-audit -r` is the candidate. If it answers, this is the same correction the pnpm round made to `pnpm audit`: a check declared unanswerable that answers in full, which `audit-core` names as a false negative rather than a clean result.

**The pylock partition's own routes.** `uv export --format pylock.toml` and `pip lock` are both candidates for generating it, and the install route for such a partition is not something this document can name. The `pylock` fixture is the control against which the uv and poetry results are read, since it is the one format `--locked` does read, so establishing its generation and install routes is part of the round rather than a prerequisite to it.

## Non-goals

- **No CI job runs a fixture.** The cost and the network dependency are the reasons; the tests in CI cover the pure halves of the three modules.
- **`safety` is not executed.** It requires authentication and is unusable in an unauthenticated audit whatever else is true. Its non-execution is recorded with that reason, which the issue's acceptance criteria explicitly allow.
- **Not the JS/TS half.** Yarn Classic, Yarn Berry, Plug'n'Play and bun are #46.
- **Not a real Python target.** #10's sweep dry run stays a separate exercise; this round makes its entries trustworthy rather than replacing it.
- **No record is corrected in PR 1.** A correction with no observed output behind it is the failure mode this whole exercise exists to remove.

## Testing

`tests/scripts/test_python_fixture_spec.py` and a companion for the harness cover the pure halves: manifest rendering per format, the expectations table, the classification of an observation into the engine's status vocabulary, and the guard that every `python:` tool in the family appears in the harness command table exactly once.

The effectful halves are exercised by the build smoke in PR 1 rather than by CI: each fixture builds from a clean checkout, and each seeded finding is detectable by at least one tool. That smoke is what stops PR 1 merging a generator whose fixtures cannot produce their own ground truth.

## Delivery

**PR 1, `Part of #45`.** The spec module, the generator, the harness, the generated expectations record and its gate, the unit tests, the `docs/audit/README.md` row, the `.gitignore` entry, and the build smoke.

**PR 2, `Closes #45`,** branched from `main` after PR 1 merges rather than stacked on its branch. The run across five fixtures in both grant states, the record corrections traceable to observed output, and `docs/audit/python-lens-smoke-run.md` modelled on its TypeScript sibling, with its own README row.

PR 2 gets its own implementation plan, written once the fixtures exist. Its per-entry work cannot be specified in advance without inventing the observations it is supposed to make.

## Risks

- **Tool-version drift.** A verification record is a dated finding, not a standing one, and `docs/audit/README.md` already says so for its TypeScript sibling. The mitigation inside the round is the floor-and-location form for counts that move.
- **A candidate route fails.** Then the hole is recorded as still open with what was observed, which is a better state than the current one, where the record asserts an exclusion nobody has tested.
- **The harness encodes a prescription wrongly.** The exact-set guard catches a missing tool; a mistranscribed command is caught by reading the harness against the records, which is a review task on PR 1 rather than something a test can see.

## Acceptance criteria mapping

Issue #45's criteria map onto this design as follows, with the one widening noted.

| Criterion | Where it is met |
|---|---|
| A committed generator produces all five partitions with seeded findings and expected counts, from a clean checkout | `build_python_fixtures.py` plus the spec module; the build smoke in PR 1 is the proof |
| Every `python:` entry executed, or its non-execution explained | PR 2's run; `safety` is the one planned non-execution, with its reason |
| Both grant states run for every entry | Two states, ungranted and `target-execution`, with the reason a third adds nothing |
| The uv SBOM hole and the `pip-audit --locked` exclusion resolved with observed output | The three named holes above |
| Every seeded finding found, or its absence recorded | The expectations record, and the rule that an undetected seed is a finding about the family |
| Each correction traceable to observed output, naming the fixture | PR 2's verification record, in the shape of its TypeScript sibling |
| `docs/audit/README.md` updated; `sweep-obligations.md` checked if `audit-core` or `audit` changes | A row in PR 1 for the expectations record, a row in PR 2 for the smoke run; the ledger is checked in PR 2, where an engine-file correction could arise |

The widening: the criteria name four domains and this round covers five, adding `docs-audit/docstring-coverage`, and covers `tach`, `vulture` and `safety`, which the criteria's tool list omits.
