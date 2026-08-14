# Python lens smoke run

Every `python:` tooling entry in `arch`, `deps`, `docs`, `security` and `test` was authored from the tools' own documentation and had never been executed against real Python targets under both grant states. This record is what happened when they were, on **2026-08-14**. It exists because a docs-only pass cannot catch the defect where a name resolves, a command runs, and the output is unusable or wrong at exit 0.

The subject here is the **skill family**, not the fixture partitions: what appears below is tool behaviour, aggregate counts, and the corrections the run forced. [The build smoke record](python-fixture-build-smoke.md) is the sibling document for the fixture machinery itself - what was generated, which seed each planted construct produced when a tool was pointed at it directly, and the measured `pytest-randomly` shuffle seed. This record grades a different thing: whether each check record's own prescribed invocation, run under the grant state its `needs` tiers imply, reaches that same answer.

## The run

Five partitions, each declaring the same logical dependency set (`jinja2` 3.1.2, `packaging` 20.9, `Unidecode` 1.4.0, `six` 1.10.0 declared-and-unused, `markupsafe` undeclared-and-imported) in a different manifest and lock format, rebuilt from this branch's merged main so their provenance needs no qualification:

- `uv` - `uv.lock`, and the one partition that carries every `python:` entry in the family (26 of the 26 checks), because it is the toolchain the whole fixture set is built through.
- `pip` - `requirements.txt`, no separate lock format.
- `poetry` - `poetry.lock`, pinned to `poetry@2.4.1` by the generator, PEP 621 `[project]` metadata rather than legacy `[tool.poetry]`.
- `pipenv` - `Pipfile.lock`, pinned to `pipenv@2026.7.1`.
- `pylock` - `pylock.toml` (PEP 751), generated from a `uv.lock` that is deleted before commit.

`pip`, `poetry`, `pipenv` and `pylock` each carry 7 of the 26 checks: the six `deps/*` checks plus `test/coverage-reach`, which exists on those partitions to prove the materialization route itself works rather than to re-test a tool.

Both grant states ran against every partition:

- **`none`** - a read-only clone with no environment resolved, which is what every `ungranted_note` makes a claim about.
- **`target-execution`** (which implies `resolved-tree`) - the same clone materialized through the partition's own manager (`uv sync --frozen`, `pip install -r` into a `uv venv --seed`, `poetry install`, `pipenv sync`, `uv pip install -r pylock.toml`).

`git status --porcelain` was empty at every one of the five fixture trees before and after the full matrix. Materialization happened in a scratch copy outside the fixture root; a package a check needed for itself (a coverage provider, an ESLint-equivalent) went into a copy the check owns, never into the shared materialized tree.

### Versions

The results carry a top-level `versions` map, captured through the same launcher each invocation uses, so a `uvx`-fetched tool reports the version `uvx` actually resolved. Where a probe itself fails - `pytest-cov`'s `importlib.metadata` lookup under the `none` grant, before anything is installed - the failure text is recorded rather than the key dropped, which is itself informative: an absent tool reads as an absent tool, not as a version nobody asked for.

| Tool | Version |
|---|---|
| `python` | 3.13.12 (Clang 21.1.4) |
| `uv` | 0.12.4 (77803aa22, 2026-08-13) |
| `pip` | 26.2.1 |
| `poetry` | 2.4.1 (pinned by the generator) |
| `pipenv` | 2026.7.1 (pinned by the generator) |
| `pip-audit` | 2.10.1 |
| `safety` | 3.8.1 (version probe only - see Still open) |
| `pip-licenses` | 5.5.5 |
| `cyclonedx-py` | 7.3.1 |
| `deptry` | 0.25.1 |
| `pytest-cov` | 7.1.0 (fails its own version probe under `none`: no package metadata to read before install) |
| `coverage.py` | 7.15.4 with C extension |
| `pytest-randomly` | 4.1.0 |
| `pytest-rerunfailures` | 16.5 |
| `pytest-timeout` | 2.4.0 |
| `mutmut` | 3.7.0 |
| `cosmic-ray` | 8.7.0 |
| `hypothesis` | 6.165.7 |
| `ruff` | 0.16.3 |
| `radon` | 6.0.1 |
| `xenon` | 0.9.3 |
| `import-linter` | 2.13 |
| `pydeps` | v3.0.7 |
| `grimp` | 3.15 |
| `tach` | 0.35.0 |
| `vulture` | 2.16 |
| `pydocstyle` | 6.3.0 |
| `interrogate` | 1.7.0 |
| `bandit` | 1.9.4 |
| `semgrep` | 1.173.0 |

## Result per entry

`ok`/`met` means the entry produced the evidence its `## Severity` section or the published expectation asks for. `no-evidence` carries the reason the engine requires. `no command form` means the check's real route is a script, a library call, or a prose grep-and-read pass rather than a command line, so nothing here is broken - see the honesty limit below.

### Arch and docs (`uv` partition)

| Entry | No grant | `target-execution` |
|---|---|---|
| `ruff`, `radon`, `xenon` (`arch/complexity`) | **ok** - `ruff` computes `C901 classify is too complex (12 > 10)`, `radon` rates it C at 13, `xenon` exits 1 on `--max-absolute B` with its finding on stderr | ok, unchanged - untiered |
| `ruff`/`radon`/`xenon` (`arch/complexity-gate`) | no command form - the primary route is reading the project's own configured threshold, and this fixture configures none | unchanged |
| `import-linter`, `pydeps`, `grimp` (`arch/cycles`) | no-evidence - no `.importlinter` contract in the clone; `grimp` is a library, not a command | `pydeps --show-cycles` alone exits 0 with empty stdout and stderr over a tree with a real two-module cycle; only `--show-dot` prints the cycle as text |
| `import-linter`, `tach`, `grimp` (`arch/layering`) | no command form for all three: the contract format, `tach`'s own configuration and `grimp`'s status as a library leave nothing to invoke | unchanged |
| `grimp`, `pydeps` (`arch/coupling`) | no command form - computed from the same edge set / offered only as a picture | unchanged |
| `grimp` (`arch/over-decomposition`) | no command form - computed from the edge set | unchanged |
| `grimp` (`arch/over-abstraction`) | no command form - fan-in computed from the same edge set `arch/layering` builds | unchanged |
| `grimp` (`arch/martin-metrics`, opt-in) | no command form - Ca/Ce/I/A/D computed from the graph, not reported by a tool | unchanged |
| `grimp` (`arch/hidden-coupling`) | no command form - a grep-and-read pass for tells the import graph would not show | unchanged |
| `vulture` (`arch/dead-code`) | **ok** - `never_referenced` among 10 unused functions at 60% confidence | ok, unchanged |
| `ruff`, `pydocstyle`, `interrogate` (`docs/docstring-coverage`) | **ok** - `unsafe.py` named among 7 files with no module docstring; `interrogate` fails its own 80% floor at 21.2% | ok, unchanged (byte-identical stdout to `none`) |

### Test (`uv` partition, `test/coverage-reach` on all five)

| Entry | No grant | `target-execution` |
|---|---|---|
| `pytest-cov`, `coverage.py` (`test/coverage-reach`) | both `no-evidence (not-permitted)`; the record's own ungranted reading pass - nothing is excluded, since the fixture configures no `[tool.coverage.run]`/`exclude_lines` - has no run represented in the results | **ok on all five partitions**, byte-identical: `TOTAL 69 57 26 2 15%` (`pytest-cov`), `TOTAL 31 3 90%` (`coverage.py`), `clamp`'s two guard branches among the uncovered lines on every one |
| `pytest-randomly` (`test/determinism`) | `no-evidence (not-permitted)`; the grep-for-nondeterminism reading pass the record prescribes has no run represented, though the constructs it would look for are in fact absent | **met** - an auto-picked seed (2522150928) reproduced the seeded order-dependent failure, `test_reads` asserting `[] == [1]` |
| `pytest-timeout` (`test/isolation`) | `no-evidence (not-permitted)`; same reading-pass gap | **met** - `--timeout=1` failed `test_slow_but_passing` with `Failed: Timeout (>1.0s) from pytest-timeout.` |
| `mutmut`, `cosmic-ray` (`test/mutation`, opt-in) | `no-evidence (not-permitted)` - the record's own `ungranted_note` is the explicit `none` sentinel, so a fully no-evidence check here is exactly correct | **missed** - see below |
| `hypothesis` (`test/property-based-gap`, opt-in) | no command form - the check's evidence is a manual read the harness never performs | unchanged |

### Security (`uv` partition)

| Entry | No grant | `target-execution` |
|---|---|---|
| `bandit`, `ruff` (`security/dangerous-calls`) | **met** - both quote the `eval` call at `unsafe.py:8` | met, unchanged - untiered |
| `bandit`, `ruff`, `semgrep` (`security/injection`) | **met** - all quote the `shell=True` subprocess and the string-built SQL | met, unchanged |
| `bandit`, `ruff`, `semgrep` (`security/crypto`) | **met** - all quote the md5 digest | met, unchanged |
| `bandit`, `ruff` (`security/unsafe-io`) | **met** - both quote `tarfile.extractall` and the bare `xml.etree` parse; `semgrep`'s registry rulesets carry no rule for either | met, unchanged |

### Deps (all five partitions)

| Entry | No grant | `target-execution` |
|---|---|---|
| `pip-audit` (`deps/vulnerabilities`), `pylock` | **met** - `pip-audit --locked .` reads `pylock.toml` and reports 5 PYSEC advisories on jinja2 3.1.2 | met, byte-identical stdout to `none` |
| `pip-audit`, `pip`/`uv` | no-evidence - `ensurepip` dies with `SIGABRT` (host fact, see below) | no-evidence, same host fault |
| `pip-audit`, `poetry`/`pipenv` | no-evidence - the record names no route for a poetry-only or Pipfile-only lock with no requirements export | unchanged |
| `safety`, all five | never invoked on any partition or grant - the record prescribes no command for it (see Still open) | unchanged |
| `uv pip list --outdated` / `pip list --outdated` (`deps/freshness`), all five | no-evidence - the record's per-package registry route has no run represented | **met on all five**, byte-identical: `pip list --outdated` and the corrected `uv pip list --outdated --python <path-to-venv-python>` both report jinja2, packaging and six stale, Unidecode correctly absent |
| `pip-licenses` (`deps/licenses`), all five | no-evidence - registry route unrepresented | **met on all five** - Unidecode 1.4.0 reported under `GNU General Public License v2 or later (GPLv2+)` |
| `pip-licenses` (`deps/transitive-licenses`), all five | no-evidence - same gap | **met on all five** - MarkupSafe 3.0.3 present as an undeclared transitive component with a licence |
| `deptry` (`deps/hygiene`), `pip`/`poetry`/`pylock`/`uv` | no-evidence - gated out; the record's own manifest-plus-lockfile ungranted reading pass has no run represented | **met** - `DEP002 'six'`, `DEP003 'markupsafe'`, plus two `DEP003` rows naming `fixture_app`'s own src-layout modules |
| `deptry`, `pipenv` | no-evidence, and for the same reason as target-execution | no-evidence - `deptry.exceptions.DependencySpecificationNotFoundError`: it has no reader for `Pipfile`/`Pipfile.lock` at all |
| `cyclonedx-py requirements` (`deps/inventory`), `pip` | met - 4 declared dependencies, no licences field | met, byte-identical |
| `cyclonedx-py pipenv`, `pipenv` | met - 4 declared plus `markupsafe` and `pyparsing`, no licences field | met, byte-identical |
| `cyclonedx-py poetry`, `poetry` | met, in the sense the failure is the expected one - `CRITICAL \| CDX > 'name'`, exit 1, no SBOM, against PEP 621 `[project]` metadata | met, identical failure |
| `cyclonedx-py requirements` on `pylock.toml`, `pylock` | met, in the same sense - no route this record offers reads PEP 751; pointed at `pylock.toml` the requirements subcommand emits a document that fails its own 1.6 schema validation | met, identical failure |
| `uv export --format=cyclonedx1.5 --frozen` (supplied route), `uv` | met - a well-formed CycloneDX 1.5 document, 6 components (4 declared plus `markupsafe` and `pyparsing`), validated clean against `cyclonedx-python-lib`'s own `JsonStrictValidator` | met, byte-identical |

## What the run found

### 1. `mutmut` cannot establish a baseline on this fixture

The granted `mutmut run` generated 10 mutants in 77ms, then moved to its clean-tests baseline - its own check that the unmutated suite passes before it will trust any mutant result - and that baseline failed: `test_appends` asserted `_SEEN == [1, 1]` where the plain suite (same partition, `test/coverage-reach` row) shows `[1]` and `5 passed`. `mutmut` printed `Failed to run clean test` and stopped: zero mutants tested, zero survivors, zero killed. The module-level `_SEEN` list that carries the `order-dependence` seed accumulates across `mutmut`'s single-process re-run, so `test_appends` runs twice in one process and sees the state left by the first run. `test/mutation`'s own record now states this as current behaviour: a suite carrying module-level state that accumulates across a single process can fail `mutmut run` at exactly this stage, reported as `Failed to run clean test` with zero mutants tested rather than as a suite defect. The claim the check exists to establish - at least one surviving mutant in `fixture_app.invariant.clamp` - was not reached on this fixture. The seed stays: removing it would erase the evidence that the family has a hole here.

### 2. `xenon`'s designed non-zero exit carries a real finding, on stderr

`xenon --max-absolute B src` exits 1 and writes `ERROR:xenon:block "src/fixture_app/complexity.py:4 classify" has a rank of C` to stderr with empty stdout. That is `xenon`'s designed behaviour for a threshold breach, not a tool failure, and `arch/complexity`'s record now states both facts: the finding lives on stderr, and the non-zero exit is the threshold-breach signal. `ruff` and `radon` independently confirm the same complexity hit on this fixture, so the check reads `met` regardless; on a partition where `xenon` were the only complexity tool available, reading its exit code as a failure would convert a genuine hit into a reported absence.

### 3. `pydeps --show-cycles` has no textual output channel at all

On the `uv` partition, `pydeps --show-cycles src/fixture_app` returns exit 0 with empty stdout and empty stderr over a tree carrying a real two-module cycle (`fixture_app.domain.model` and `fixture_app.infra.store`). The tool draws its answer onto an SVG side-file rather than printing it, so "ran, exit 0, nothing on either stream" is this invocation's behaviour whether or not a cycle exists - indistinguishable to any caller that reads only the streams. `pydeps --show-cycles --show-dot` prints the underlying dot source as text, showing both directed edges of the cycle explicitly. `arch/cycles`'s record now appends `--show-dot` to the prescribed invocation for exactly this reason.

### 4. `deps/inventory` has a working uv route, a poetry gap, and no licence field anywhere

`uv export --format=cyclonedx1.5 --frozen` is the record's existing "or the tool's native SBOM export" clause, now named concretely: it produces a CycloneDX 1.5 document that `cyclonedx-python-lib`'s own `JsonStrictValidator` accepts with no errors. `cyclonedx-py poetry` fails on both grants with `CRITICAL | CDX > 'name'`, exit 1, no SBOM written, because it reads the project name from `[tool.poetry]` only, and this partition's PEP 621 `[project]` metadata is the layout poetry 2 pushes projects toward without raising a deprecation warning - the ordinary case, not an edge case. `cyclonedx-py requirements` pointed at `pylock.toml` neither refuses nor reads PEP 751: it reads the TOML as requirement lines and emits a document that fails its own 1.6 schema validation, exiting non-zero having written nothing usable. No successful route on any partition - `requirements`, `pipenv`, or the uv export - populates a `licenses` field on any component; `deps/licenses` is this family's only source of licence evidence.

### 5. `deps/vulnerabilities`: pylock established, poetry and pipenv named as a gap, and a route added with its soundness scoped to the file it reads

`pip-audit --locked .` reads `pylock.toml` cleanly and reports 5 PYSEC advisories against jinja2 3.1.2 on both grants, satisfying the check's floor without touching a resolved tree. For a poetry-only or pipenv-only lock with no requirements export, the record names no route `pip-audit` can take at all; `poetry export` and `pipenv requirements` each exist and were not attempted here, so this stays a gap rather than a settled negative. A route was added for the case where a requirements file does exist: `pip-audit -r <requirements> --no-deps --disable-pip` avoids provisioning a virtualenv, with both flags documented for this pairing (`--no-deps` "requires all requirements are pinned to an exact version", `--disable-pip` "can only be used with hashed requirements files or if the `--no-deps` flag has been provided"). Its soundness depends on the shape of the file it reads, not on the flags: `uv export --frozen` on the uv fixture wrote 7 entries including the transitives `markupsafe` and `pyparsing`, so a route pointed at it audits everything the lock pins; the pip partition's own `requirements.txt` declares 4 direct pins and no transitives, so the identical flags there audit a strict subset and a transitive-only advisory would be invisible rather than reported as a gap.

### 6. `deps/freshness`: a false clean any real audit can hit

`uv pip list --outdated` can return empty output at exit 0 against a tree with stale packages in it, when the inner `uv` invocation is not told which interpreter to use. Measured in a scratch copy of the uv fixture after `uv sync --frozen`, not as an artifact of the ten-run matrix (the matrix, after the fix, only ever ran the corrected invocation): unqualified, `uv pip list --outdated` printed nothing at exit 0; qualified with `--python <path-to-venv-python>`, it reported jinja2 3.1.2 to 3.1.6, packaging 20.9 to 26.3, and six 1.10.0 to 1.17.0; `pip list --outdated` in the identical wrapper needed no such flag, because it introspects whichever interpreter it runs under rather than depending on venv-discovery logic. The record now names the interpreter explicitly on the uv route for this reason.

### 7. `deps/hygiene`: pipenv has no lens on either grant

`deptry` raises `deptry.exceptions.DependencySpecificationNotFoundError: No file called 'pyproject.toml' with a [tool.poetry.dependencies], [tool.pdm] or [project] section or file(s) called 'requirements.txt' found. Exiting.` against the pipenv partition under `target-execution`, and under `none` the check is simply gated out - but for the same underlying reason on each: `deptry` has no reader for `Pipfile` or `Pipfile.lock` at all, so this is not the ordinary "no grant, no answer" case the record's other four partitions share. The other four partitions produce the expected `DEP002 'six'` plus `DEP003 'markupsafe'`, plus two further `DEP003` rows naming `fixture_app`'s own src-layout modules - expected output on this layout rather than a seed, since `deptry` treats a src-layout package's self-imports as third-party.

### 8. `arch/over-abstraction`'s frontmatter named a tool its own prose never used

The record's `tooling.python` listed `[grimp, ruff]`, but the Python fallback paragraph names only `grimp` refs, AST counts and a grep for shim markers - `ruff` appears nowhere in the prose that is supposed to say what it checks. `ruff` was dropped from the record's Python tooling rather than given invented instructions, since there was no evidence for what it would check here.

### 9. The honesty limit: execution verifies a command, not a reading pass

Seven of the ten `arch` checks triaged here - `complexity-gate`, `cycles`'s companion tools, `layering`, `coupling`, `over-decomposition`, `over-abstraction`, `martin-metrics`, `hidden-coupling` - answer through a `grimp` script, a library call, or a prose grep-and-read pass, and have no CLI form at all for a harness that only runs literal shell commands to invoke. Several `deps` and `test` checks share the same shape on their ungranted route: `deps/freshness`, `deps/licenses`, `deps/transitive-licenses`, `deps/hygiene`, `test/determinism`, `test/isolation` and `test/coverage-reach` each name a registry lookup or a grep pass that survives a withheld grant, and none of those reading passes is represented in any results file, because the harness never performs one. This round therefore does not establish that every `ungranted_note` was tested; it establishes it for the entries that are command-shaped, and states the rest as a limit on what execution can verify rather than as a defect in the checks that carry it. Where the underlying fact was independently confirmed by reading the fixture directly - no `.importlinter` file, no non-deterministic construct in the seeded suite, no `[tool.coverage.run]` section - that confirmation is a note supporting the classification, never a substitute for the run producing evidence itself.

## Records corrected

Traceable to the observed output above; see the commits on issue #45.

| Record | Fixture | Correction |
|---|---|---|
| `deps/inventory` | poetry, pylock, uv | name the uv SBOM export concretely; state that `cyclonedx-py poetry` fails on PEP 621 metadata; state that no SBOM route populates a licence field |
| `deps/hygiene` | pipenv | state that `deptry` has no `Pipfile` reader at all, so the pipenv partition has no hygiene lens on either grant |
| `deps/freshness` | uv (scratch-copy measurement, see finding 6) | name the interpreter explicitly on the uv route (`--python <path>`), and why an unqualified invocation is not trustworthy |
| `deps/vulnerabilities` | pip, uv | add `pip-audit -r <requirements> --no-deps --disable-pip` as a route that skips virtualenv provisioning, scoped to the shape of the file it reads |
| `arch/cycles` | uv | append `--show-dot` to the prescribed `pydeps` cycle invocation, since the bare form has no textual output channel |
| `arch/over-abstraction` | uv | drop `ruff` from the Python tooling list, since the record's own prose never gave it instructions |
| `test/mutation` | uv | state that a bare `mutmut run` exit code is never itself a findings signal, and name the module-level-state failure mode observed here |
| `arch/complexity` | uv | state that `xenon`'s complexity finding lands on stderr, and that its non-zero exit is a designed threshold-breach signal rather than a failure |

## Still open

- **`safety`'s non-execution.** The record prescribes no command for `safety` at all: its own note is that the completeness it claims is only ever claimed about a scan of an installed environment, and that it requires authentication and is unusable in an unauthenticated audit whatever else is true. Every entry in the results carries `"ran": false, "why": "the record prescribes no command for this tool"` for `safety`, on every partition and grant - the version probe alone succeeded (`safety, version 3.8.1`), because that alone needs no authentication. This is a planned non-execution and an acceptance criterion, not a gap the run left open by omission.
- **`pip-audit --locked .`'s exclusivity claim is half established.** The record's claim is that it reads PEP 751 "and nothing else" - the pylock half is confirmed (5 PYSEC advisories on jinja2 3.1.2, read cleanly with nothing else present), but the other half - that it does not also read a `uv.lock` sitting beside a PEP 751 lock - was never exercised, because the uv partition's granted run took the supplied export-and-`-r` route instead of `--locked`, and hit the host fault below before reaching that question.
- **`ensurepip` dies with `SIGABRT` on the host that ran this**, under CPython 3.13, with and without `--no-deps`, whenever `pip-audit -r` needs to provision its own virtualenv. This is a property of the host, not a finding about `deps/vulnerabilities` or about `pip-audit`, and is recorded here for that reason and no other.
- **`test/mutation`'s floor claim - at least one surviving mutant in `fixture_app.invariant.clamp` - was not reached.** The order-dependence seed blocks the mutation-survivor seed, on this fixture, under `mutmut` 3.7.0's single-process re-run model; the seed stays, because removing it would erase the evidence that the family has a hole here.
- **`poetry export` and `pipenv requirements` remain untried as a vulnerabilities route.** Each ecosystem's own manager can produce a requirements-shaped export; neither was fed to `pip-audit -r` in this round, so `deps/vulnerabilities` on a poetry-only or pipenv-only lock is still recorded as a gap rather than a settled negative.
- **The reading-pass limit above bounds what this round proves.** Seven of the ten `arch` checks and the ungranted route of several `deps` and `test` checks have no representation in any results file, by design: a command-running harness cannot execute a script, a library call, or a prose read. This round establishes its floor and ceiling for the entries that are command-shaped; it does not claim to have tested the rest.
