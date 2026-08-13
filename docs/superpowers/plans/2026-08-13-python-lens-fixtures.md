# Seeded Python fixtures - build phase implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the generator, the expectations record and the harness for the seeded Python fixture round, so that PR 2 can run all 27 `python:` tooling entries against planted ground truth.

**Architecture:** One pure module holds the fixture definition and its expectations, so a seeded finding cannot exist in the tree and be missing from the expectations. A generator renders that definition into five gitignored fixture trees, each a git repository. A harness holds each check record's prescribed invocation verbatim and classifies what comes back. Rendering the expectations to Markdown follows the repository's existing generated-doc pattern: edit the module, re-render, `--check` in CI.

**Tech Stack:** Python 3.12, `uv`, pytest, ruff. The fixture managers are `uv`, `pip`, `poetry`, `pipenv` and PEP 751 `pylock.toml`.

## Global Constraints

- This plan covers **PR 1 only**, which is `Part of #45`. No check record is corrected here: a correction with no observed output behind it is the failure mode the round exists to remove.
- Fixture trees are **never committed**. `fixtures/` goes in `.gitignore`.
- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow lines you did not change.
- No em-dash (U+2014) anywhere under `docs/superpowers/`. Use ` - `.
- Never commit environment-specific values: absolute personal paths, hostnames, emails, profile names.
- Every script ships with unit tests over its pure helpers, loaded through `tests/scripts/conftest.py`, which already puts `scripts/` on `sys.path`.
- No bare `except Exception: pass`. Every exception is reported with type and message, logged, or re-raised.
- Run Python via `uv run`. Prepend `caffeinate` to any command that waits.
- Commit at the end of every task with `Refs #45`.

## Verified ground truth

These were checked against OSV and PyPI on 2026-08-13 before this plan was written. Do not substitute a package without re-checking it the same way.

| Package | Pin | Seeds | Evidence |
|---|---|---|---|
| `jinja2` | `3.1.2` | vulnerable, transitive root | OSV returns 10 advisories over 5 distinct CVEs: CVE-2024-22195, CVE-2024-34064, CVE-2024-56201, CVE-2024-56326, CVE-2025-27516. Requires `MarkupSafe`, giving depth 2. Latest is 3.1.6 |
| `packaging` | `20.9` | stale | 0 advisories. Latest is 26.3, six majors ahead |
| `Unidecode` | `1.4.0` | copyleft | Classifier `License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)`. Pure Python, `requires_dist` is null. **This is the latest release**, which makes it the freshness check's false-positive control |
| `six` | `1.10.0` | declared and never imported | 0 advisories. Latest is 1.17.0 |
| `markupsafe` | not declared | imported without being declared | Arrives transitively through `jinja2` |

The advisory expectation is a **floor**: at least those five CVEs. New advisories against a frozen pin only ever arrive, so an exact count goes stale silently while a floor does not.

**Why not `jinja2==2.11.3`,** which carries four of the same CVEs and was this plan's first choice: it declares `MarkupSafe>=0.23` unbounded, so a fresh resolution takes markupsafe 3.0.3, and 2.11.3 imports `soft_unicode`, removed in markupsafe 2.1. The seeded package then fails at **collection**, taking out every `target-execution` expectation at once - and pinning `markupsafe<2.1` to fix it would declare the dependency whose whole purpose is to be undeclared. This was found by both Task 1 reviewers independently, and it is the shape of defect the round exists to find: the pin was verified against OSV and PyPI without anyone co-installing the set and importing it.

## File structure

- `scripts/python_fixture_spec.py` - pure. The dependency set, the seeded source tree, the manifest rendering and the expectations. Shells out to nothing.
- `scripts/build_python_fixtures.py` - effectful. Writes the five trees.
- `scripts/render_python_fixture_expectations.py` - renders the expectations Markdown, `--check` compares.
- `scripts/run_python_fixture_lens.py` - the harness: the verbatim invocation table and the pure classification helpers.
- `tests/scripts/test_python_fixture_spec.py`, `tests/scripts/test_python_fixture_harness.py`.
- `docs/audit/python-fixture-expectations.md` - generated, never hand-edited.

---

### Task 1: The fixture definition - dependencies and seeded source

**Files:**
- Create: `scripts/python_fixture_spec.py`
- Test: `tests/scripts/test_python_fixture_spec.py`

**Interfaces:**
- Produces: `PARTITIONS`, `FULL_PARTITION`, `Dependency`, `DEPENDENCIES`, `SourceFile`, `SOURCE_FILES`, `source_tree()`.

- [ ] **Step 1: Write the failing test**

```python
from python_fixture_spec import DEPENDENCIES, PARTITIONS, SOURCE_FILES, source_tree


def test_every_seed_is_carried_by_exactly_one_dependency():
    seeds = [s for d in DEPENDENCIES for s in d.seeds]
    assert sorted(seeds) == sorted(set(seeds))
    assert "vulnerable" in seeds and "copyleft" in seeds


def test_the_undeclared_import_is_imported_and_not_declared():
    undeclared = [d for d in DEPENDENCIES if not d.pin]
    assert [d.name for d in undeclared] == ["markupsafe"]
    assert undeclared[0].imported is True


def test_the_unused_dependency_is_declared_and_never_imported():
    unused = [d for d in DEPENDENCIES if d.pin and not d.imported]
    assert [d.name for d in unused] == ["six"]
    body = "\n".join(f.body for f in SOURCE_FILES)
    assert "import six" not in body


def test_the_five_partitions_are_named():
    assert PARTITIONS == ("uv", "pip", "poetry", "pipenv", "pylock")


def test_source_tree_maps_paths_to_bodies():
    tree = source_tree()
    assert "src/fixture_app/domain/model.py" in tree
    assert tree["src/fixture_app/domain/model.py"].startswith('"""')
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/scripts/test_python_fixture_spec.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'python_fixture_spec'`

- [ ] **Step 3: Write the module**

```python
"""Definition of the seeded Python fixtures.

One dependency set, one seeded source tree, five manifest renderings and one
expectations table, all from this module. The fixture tree and the expectations
are produced from the same definition on purpose: expectations kept in a second
file are free to drift, and a seed present in the tree but missing from the
expectations reads exactly like a tool that correctly found nothing.

Pure. Nothing here touches the filesystem, the network or a subprocess.
"""

from dataclasses import dataclass

PARTITIONS = ("uv", "pip", "poetry", "pipenv", "pylock")

# The partition that carries every `python:` entry. The other four carry the
# six `deps` records plus pytest-cov, which is tiered `target-execution` and so
# fails if either half of that partition's materialization route is broken.
FULL_PARTITION = "uv"

PACKAGE = "fixture_app"


@dataclass(frozen=True)
class Dependency:
    """One entry in the shared dependency set.

    `pin` is empty for the dependency the fixture imports without declaring,
    which arrives transitively instead.

    `module` is the name the source imports, which is not always the name the
    manifest declares - `Unidecode` is declared under that name and imported as
    `unidecode`. Keeping both means a test can assert that an `imported=True`
    entry really is imported somewhere in the seeded tree.
    """

    name: str
    pin: str
    imported: bool
    module: str
    seeds: tuple[str, ...]
    evidence: str


DEPENDENCIES = (
    Dependency(
        "jinja2",
        "3.1.2",
        True,
        "jinja2",
        ("vulnerable", "transitive-root"),
        "OSV: 10 advisories over CVE-2024-22195, CVE-2024-34064, CVE-2024-56201, "
        "CVE-2024-56326 and CVE-2025-27516; requires MarkupSafe, which is what makes "
        "it the transitive root",
    ),
    Dependency(
        "packaging",
        "20.9",
        True,
        "packaging",
        ("stale",),
        "no advisories; latest is 26.3, six majors ahead",
    ),
    Dependency(
        "Unidecode",
        "1.4.0",
        True,
        "unidecode",
        ("copyleft",),
        "classifier: GNU General Public License v2 or later (GPLv2+); pure Python, "
        "declares no dependencies of its own",
    ),
    Dependency(
        "six",
        "1.10.0",
        False,
        "six",
        ("declared-unused",),
        "no advisories; declared and never imported, which is deptry DEP002",
    ),
    Dependency(
        "markupsafe",
        "",
        True,
        "markupsafe",
        ("undeclared-import",),
        "arrives through jinja2 and is imported directly, which is deptry DEP003",
    ),
)


@dataclass(frozen=True)
class SourceFile:
    path: str
    body: str
    seeds: tuple[str, ...]


# The import cycle uses the `import a.b.c` form in both directions rather than
# `from a.b import c`. A cycle written with `from` raises ImportError on the
# partially-initialized module; the plain form binds the top-level package and
# defers attribute lookup to call time, so the cycle is real for the graph
# tools and the suite still runs.
_MODEL = '''"""Domain model. Imports infra, which is the layering violation."""

import fixture_app.infra.store


def load(key):
    return fixture_app.infra.store.read(key)
'''

_STORE = '''"""Infrastructure store. Imports the domain model, closing the cycle."""

import fixture_app.domain.model

_DATA = {"a": 1}


def read(key):
    return _DATA.get(key)


def load_via_domain(key):
    return fixture_app.domain.model.load(key)
'''

_COMPLEXITY = '''"""One function over any reasonable complexity threshold."""


def classify(a, b, c, d, e):
    total = 0
    if a > 0:
        if b > 0:
            if c > 0:
                total += 1
            else:
                total += 2
        elif d > 0:
            total += 3
        else:
            total += 4
    elif b > 0:
        if c > 0:
            total += 5
        elif d > 0:
            total += 6
        else:
            total += 7
    elif c > 0:
        total += 8 if e > 0 else 9
    elif d > 0:
        total += 10
    else:
        total += 11
    return total
'''

_UNSAFE = '''import hashlib
import subprocess


def run_expression(expr):
    return eval(expr)


def run_shell(name):
    return subprocess.run("ls " + name, shell=True, check=False)


def digest(value):
    return hashlib.md5(value.encode()).hexdigest()


def query(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = '%s'" % user_id)
'''

_DEADCODE = '''"""Nothing imports or calls this."""


def never_referenced(value):
    return value * 2
'''

_RENDER = '''"""Uses jinja2, Unidecode, markupsafe and packaging.

markupsafe is imported without being declared; it arrives through jinja2.
"""

import jinja2
import markupsafe
import packaging.version
import unidecode


def render(name):
    template = jinja2.Template("hello {{ name }}")
    return template.render(name=markupsafe.escape(unidecode.unidecode(name)))


def version_is_recent(raw):
    return packaging.version.Version(raw) >= packaging.version.Version("1.0")
'''

_INVARIANT = '''"""A function with an obvious invariant and no property test."""


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value
'''

_TEST_RENDER = '''from fixture_app import render


def test_render_greets():
    assert "hello" in render.render("Jose")
'''

_TEST_ORDER = '''"""An order-dependent pair, green in file order.

test_appends runs first by default and leaves the module-level list populated,
so test_reads passes. Under a shuffle that reverses them, test_reads sees an
empty list and fails. The seed that reverses them is recorded in the
expectations rather than guessed.
"""

_SEEN = []


def test_appends():
    _SEEN.append(1)
    assert _SEEN == [1]


def test_reads():
    assert _SEEN == [1]
'''

_TEST_SLOW = '''import time


def test_slow_but_passing():
    time.sleep(2)
    assert True
'''

_TEST_PARTIAL = '''from fixture_app import invariant


def test_clamp_passes_through():
    assert invariant.clamp(5, 0, 10) == 5
'''

SOURCE_FILES = (
    SourceFile(f"src/{PACKAGE}/__init__.py", "", ()),
    SourceFile(f"src/{PACKAGE}/domain/__init__.py", "", ()),
    SourceFile(f"src/{PACKAGE}/domain/model.py", _MODEL, ("cycle", "layering")),
    SourceFile(f"src/{PACKAGE}/infra/__init__.py", "", ()),
    SourceFile(f"src/{PACKAGE}/infra/store.py", _STORE, ("cycle",)),
    SourceFile(f"src/{PACKAGE}/complexity.py", _COMPLEXITY, ("complexity",)),
    SourceFile(f"src/{PACKAGE}/unsafe.py", _UNSAFE, ("dangerous-calls", "injection", "crypto", "unsafe-io", "undocumented")),
    SourceFile(f"src/{PACKAGE}/deadcode.py", _DEADCODE, ("dead-code",)),
    SourceFile(f"src/{PACKAGE}/render.py", _RENDER, ("undeclared-import",)),
    SourceFile(f"src/{PACKAGE}/invariant.py", _INVARIANT, ("property-gap", "mutation-survivor", "uncovered-branch")),
    SourceFile("tests/test_render.py", _TEST_RENDER, ()),
    SourceFile("tests/test_order.py", _TEST_ORDER, ("order-dependence",)),
    SourceFile("tests/test_slow.py", _TEST_SLOW, ("slow-test",)),
    SourceFile("tests/test_partial.py", _TEST_PARTIAL, ("mutation-survivor", "uncovered-branch")),
)


def source_tree() -> dict[str, str]:
    """Map every seeded path to its body."""
    return {f.path: f.body for f in SOURCE_FILES}
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/scripts/test_python_fixture_spec.py -q`
Expected: PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format .
git add scripts/python_fixture_spec.py tests/scripts/test_python_fixture_spec.py
git commit -m "feat: define the seeded Python fixture dependency set and source tree

Refs #45"
```

---

### Task 2: Manifest rendering for the five partitions

**Files:**
- Modify: `scripts/python_fixture_spec.py`
- Test: `tests/scripts/test_python_fixture_spec.py`

**Interfaces:**
- Consumes: `DEPENDENCIES`, `PACKAGE` from Task 1.
- Produces: `render_manifests(partition: str) -> dict[str, str]`, raising `ValueError` on an unknown partition.

Only the declared dependencies reach a manifest; the undeclared one has an empty `pin` and is skipped everywhere. Lock files are **not** rendered here - each manager generates its own in Task 5, which is the point of having five partitions.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from python_fixture_spec import PARTITIONS, render_manifests


def test_every_partition_renders_a_manifest():
    for partition in PARTITIONS:
        files = render_manifests(partition)
        assert files, partition
        assert all(body.strip() for body in files.values()), partition


def test_the_undeclared_dependency_reaches_no_manifest():
    for partition in PARTITIONS:
        for body in render_manifests(partition).values():
            assert "markupsafe" not in body.lower(), partition


def test_each_partition_uses_its_own_manifest_format():
    assert "pyproject.toml" in render_manifests("uv")
    assert "requirements.txt" in render_manifests("pip")
    assert "tool.poetry" in render_manifests("poetry")["pyproject.toml"]
    assert "Pipfile" in render_manifests("pipenv")


def test_an_unknown_partition_is_rejected_by_name():
    with pytest.raises(ValueError, match="conda"):
        render_manifests("conda")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/scripts/test_python_fixture_spec.py -q`
Expected: FAIL with `ImportError: cannot import name 'render_manifests'`

- [ ] **Step 3: Implement**

```python
def declared() -> tuple[Dependency, ...]:
    """The dependencies a manifest names. Excludes the undeclared-import seed."""
    return tuple(d for d in DEPENDENCIES if d.pin)


_PROJECT_HEADER = f'''[project]
name = "{PACKAGE}"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
'''


def _pep621_pyproject() -> str:
    lines = [f'    "{d.name}=={d.pin}",' for d in declared()]
    return (
        _PROJECT_HEADER
        + "\n".join(lines)
        + '\n]\n\n[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n'
    )


def _poetry_pyproject() -> str:
    lines = [f'{d.name} = "{d.pin}"' for d in declared()]
    return (
        f'[tool.poetry]\nname = "{PACKAGE}"\nversion = "0.1.0"\n'
        f'description = "Seeded audit fixture"\nauthors = []\n'
        f'packages = [{{ include = "{PACKAGE}", from = "src" }}]\n\n'
        "[tool.poetry.dependencies]\npython = \"^3.12\"\n"
        + "\n".join(lines)
        + '\n\n[build-system]\nrequires = ["poetry-core"]\nbuild-backend = "poetry.core.masonry.api"\n'
    )


def _pipfile() -> str:
    lines = [f'{d.name} = "=={d.pin}"' for d in declared()]
    return (
        "[[source]]\nurl = \"https://pypi.org/simple\"\nverify_ssl = true\nname = \"pypi\"\n\n"
        "[packages]\n" + "\n".join(lines) + '\n\n[requires]\npython_version = "3.12"\n'
    )


def _requirements() -> str:
    return "\n".join(f"{d.name}=={d.pin}" for d in declared()) + "\n"


def render_manifests(partition: str) -> dict[str, str]:
    """Return {relative path: content} for one partition's declared manifests.

    Lock files are absent by design: each manager generates its own, which is
    the difference the five partitions exist to exercise.
    """
    if partition not in PARTITIONS:
        raise ValueError(f"unknown partition {partition!r}; expected one of {PARTITIONS}")
    if partition in ("uv", "pylock"):
        return {"pyproject.toml": _pep621_pyproject()}
    if partition == "pip":
        return {"requirements.txt": _requirements(), "pyproject.toml": _pep621_pyproject()}
    if partition == "poetry":
        return {"pyproject.toml": _poetry_pyproject()}
    return {"Pipfile": _pipfile()}
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/scripts/test_python_fixture_spec.py -q`
Expected: PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format .
git add scripts/python_fixture_spec.py tests/scripts/test_python_fixture_spec.py
git commit -m "feat: render the fixture dependency set into five manifest formats

Refs #45"
```

---

### Task 3: The expectations table

**Files:**
- Modify: `scripts/python_fixture_spec.py`
- Test: `tests/scripts/test_python_fixture_spec.py`

**Interfaces:**
- Produces: `Expectation`, `EXPECTATIONS`, `expectations_for(partition) -> tuple[Expectation, ...]`, `DEPS_CHECKS`.

`form` is one of `exact`, `floor`, `absence`. A count that moves with a tool's version takes `floor`; `absence` is for a finding whose expected shape is that nothing is configured, which is `arch/complexity-gate`.

- [ ] **Step 1: Write the failing test**

```python
from python_fixture_spec import (
    DEPS_CHECKS,
    EXPECTATIONS,
    FULL_PARTITION,
    PARTITIONS,
    SOURCE_FILES,
    expectations_for,
)


def test_every_expectation_names_a_known_partition_and_form():
    for e in EXPECTATIONS:
        assert set(e.partitions) <= set(PARTITIONS), e.check
        assert e.form in ("exact", "floor", "absence"), e.check


def test_every_seed_anywhere_in_the_definition_is_expected_by_some_check():
    """Both seed sources, not just the source tree.

    Five of the six dependency seeds never appear in SOURCE_FILES, so unioning
    only the tree would leave `vulnerable`, `stale`, `copyleft`,
    `transitive-root` and `declared-unused` unguarded - which is most of what
    the deps half of the round is for.
    """
    from python_fixture_spec import DEPENDENCIES

    seeded = {s for f in SOURCE_FILES for s in f.seeds} | {
        s for d in DEPENDENCIES for s in d.seeds
    }
    expected = {s for e in EXPECTATIONS for s in e.seeds}
    assert seeded - expected == set(), "planted and unexpected"
    assert expected - seeded == set(), "expected and unplanted"


def test_the_deps_checks_run_on_every_partition():
    for check in DEPS_CHECKS:
        matching = [e for e in EXPECTATIONS if e.check == check]
        assert matching, check
        assert set(PARTITIONS) <= {p for e in matching for p in e.partitions}, check


def test_the_thin_partitions_carry_deps_plus_coverage_only():
    """Every thin partition, not one of them.

    Checking `poetry` alone leaves the other three free to carry anything, and
    the scoping corrections landed on `pipenv` rather than on `poetry`.
    """
    for partition in set(PARTITIONS) - {FULL_PARTITION}:
        checks = {e.check for e in expectations_for(partition)}
        assert checks == set(DEPS_CHECKS) | {THIN_EXTRA_CHECK}, partition


def test_the_full_partition_carries_every_check_any_partition_carries():
    """A set equality, not a size comparison.

    `len(full) > len(thin)` cannot fail on the thing that would actually be
    wrong: a check scoped to the thin partitions and omitted from the full one,
    which is the partition meant to carry every `python:` entry in the family.
    """
    assert {e.check for e in expectations_for(FULL_PARTITION)} == {
        e.check for e in EXPECTATIONS
    }


def test_the_vulnerability_expectation_is_a_floor_naming_its_cves():
    e = next(x for x in EXPECTATIONS if x.check == "deps/vulnerabilities")
    assert e.form == "floor"
    assert "CVE-2024-22195" in e.claim
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/scripts/test_python_fixture_spec.py -q`
Expected: FAIL with `ImportError: cannot import name 'DEPS_CHECKS'`

- [ ] **Step 3: Implement**

```python
DEPS_CHECKS = (
    "deps/inventory",
    "deps/vulnerabilities",
    "deps/freshness",
    "deps/licenses",
    "deps/transitive-licenses",
    "deps/hygiene",
)

# The one non-deps check the thin partitions run. pytest-cov is tiered
# `target-execution`, so it fails if either half of that partition's
# materialization route is broken: the tree, and the suite running against it.
THIN_EXTRA_CHECK = "test/coverage-reach"

_ALL = PARTITIONS
_FULL = (FULL_PARTITION,)


@dataclass(frozen=True)
class Expectation:
    """What a check must observe on a partition, and why that form.

    `claim` is prose because the observation is prose: what a reader needs is
    the thing to look for, not a number a later tool version invalidates.
    """

    check: str
    partitions: tuple[str, ...]
    form: str
    claim: str
    seeds: tuple[str, ...]


EXPECTATIONS = (
    Expectation(
        "deps/vulnerabilities",
        _ALL,
        "floor",
        "at least 5 advisories against jinja2 3.1.2, covering CVE-2024-22195, "
        "CVE-2024-34064, CVE-2024-56201, CVE-2024-56326 and CVE-2025-27516. A floor "
        "because new advisories against a frozen pin only ever arrive",
        ("vulnerable",),
    ),
    Expectation(
        "deps/freshness",
        _ALL,
        "exact",
        "every declared dependency except Unidecode is outdated, packaging 20.9 most "
        "obviously at six majors behind 26.3. Unidecode 1.4.0 is the latest release "
        "and is the control: a route that reports it outdated is producing a false "
        "positive, which an all-four expectation could never have caught. Named by "
        "the exception rather than by a count, since which dependency is the control "
        "is stable where the size of the set is not",
        ("stale",),
    ),
    Expectation(
        "deps/licenses",
        _ALL,
        "exact",
        "Unidecode 1.4.0 is reported under a GPLv2+ licence. A copyleft entry the "
        "check must surface rather than a count",
        ("copyleft",),
    ),
    Expectation(
        "deps/transitive-licenses",
        _ALL,
        "floor",
        "at least markupsafe appears as a transitive component with a licence, "
        "since it is never declared and arrives through jinja2",
        ("transitive-root",),
    ),
    Expectation(
        "deps/hygiene",
        ("pipenv",),
        "exact",
        "deptry finds no dependency specification at all and raises "
        "DependencySpecificationNotFoundError. A Pipfile is not a format it reads, so "
        "this partition has no hygiene lens on any grant - which is a finding about "
        "the family rather than about the fixture, and is why the check is scoped "
        "away from this partition instead of being expected to answer here",
        (),
    ),
    Expectation(
        "deps/hygiene",
        tuple(p for p in _ALL if p != "pipenv"),
        "exact",
        "six is reported declared-and-unused (deptry DEP002) and markupsafe is "
        "reported as a transitive dependency being imported (deptry DEP003). Two "
        "further DEP003 rows name fixture_app's own modules, because deptry treats a "
        "src-layout package's self-imports as third-party; they are expected output "
        "rather than a seed, and the run records them as the tool's behaviour on this "
        "layout instead of configuring them away, since suppressing them would hide a "
        "false positive an audited project would also meet",
        ("declared-unused", "undeclared-import"),
    ),
    Expectation(
        "deps/inventory",
        tuple(p for p in _ALL if p != "poetry"),
        "floor",
        "an SBOM listing at least the four declared dependencies plus markupsafe, "
        "with a licence field populated for Unidecode",
        (),
    ),
    Expectation(
        "deps/inventory",
        ("poetry",),
        "exact",
        "cyclonedx-py's poetry subcommand fails with CRITICAL | CDX > 'name' and "
        "writes no SBOM, because it reads name from [tool.poetry] and this partition "
        "carries PEP 621 metadata, which is the form poetry 2 pushes projects towards "
        "and the form that emits no deprecation warning. Measured both ways on one "
        "tree with one tool: the legacy all-in-[tool.poetry] manifest produces a valid "
        "CycloneDX 1.6 document, so the finding is that the subcommand has no route "
        "for PEP 621 poetry metadata rather than no poetry route at all. Recorded "
        "before the run precisely so PR 2 cannot mistake the narrow claim for the "
        "broad one",
        (),
    ),
    Expectation(
        THIN_EXTRA_CHECK,
        _ALL,
        "exact",
        "coverage reports the two unreached branches of fixture_app.invariant.clamp; "
        "on a thin partition this doubles as proof that the materialization route works",
        ("uncovered-branch",),
    ),
    Expectation(
        "arch/complexity",
        _FULL,
        "exact",
        "fixture_app.complexity.classify is reported over threshold by every tool that "
        "carries one",
        ("complexity",),
    ),
    Expectation(
        "arch/complexity-gate",
        _FULL,
        "absence",
        "no complexity threshold is configured anywhere in the fixture, so the expected "
        "finding is the absence of a gate rather than a hit",
        (),
    ),
    Expectation(
        "arch/cycles",
        _FULL,
        "exact",
        "one cycle between fixture_app.domain.model and fixture_app.infra.store",
        ("cycle",),
    ),
    Expectation(
        "arch/layering",
        _FULL,
        "exact",
        "fixture_app.domain.model imports fixture_app.infra.store, which is the "
        "layering violation",
        ("layering",),
    ),
    Expectation(
        "arch/coupling",
        _FULL,
        "floor",
        "the two modules in the cycle are each other's dependents, so neither is a leaf",
        ("cycle",),
    ),
    Expectation(
        "arch/over-decomposition",
        _FULL,
        "floor",
        "the seeded package's module count, interpolated from SOURCE_FILES, is far "
        "below any over-decomposition threshold, so the expected result is a clean row "
        "and a hit here is a false positive. Interpolated rather than written out, "
        "since a stated number goes stale the first time a seed is added - and a claim "
        "that merely says it is computed, while stating nothing, is the same defect "
        "wearing the fix's language",
        (),
    ),
    Expectation(
        "arch/over-abstraction",
        _FULL,
        "floor",
        "no abstraction with a single implementation is seeded, so a hit here is a false "
        "positive rather than a find",
        (),
    ),
    Expectation(
        "arch/martin-metrics",
        _FULL,
        "floor",
        "the cycle puts both of its modules in the zone of pain or uselessness, "
        "whichever the tool's own formula selects",
        ("cycle",),
    ),
    Expectation(
        "arch/hidden-coupling",
        _FULL,
        "floor",
        "the call-time attribute access across the cycle is reachable from the graph, "
        "so a tool that reports nothing has missed the deferred edge",
        ("cycle",),
    ),
    Expectation(
        "arch/dead-code",
        _FULL,
        "floor",
        "fixture_app.deadcode.never_referenced appears among the unused symbols. A "
        "floor rather than an exact claim because several other seeded functions are "
        "also never called - the seeded suite exercises the package thinly on purpose "
        "- so a tool naming only this one and a tool naming every function both "
        "satisfy the check, and the run records which it was",
        ("dead-code",),
    ),
    Expectation(
        "security/dangerous-calls",
        _FULL,
        "exact",
        "the eval call in fixture_app.unsafe.run_expression",
        ("dangerous-calls",),
    ),
    Expectation(
        "security/injection",
        _FULL,
        "exact",
        "the shell=True subprocess in run_shell and the string-formatted SQL in query",
        ("injection",),
    ),
    Expectation(
        "security/crypto",
        _FULL,
        "exact",
        "the md5 digest in fixture_app.unsafe.digest",
        ("crypto",),
    ),
    Expectation(
        "security/unsafe-io",
        _FULL,
        "exact",
        "the unchecked tarfile.extractall in fixture_app.unsafe.unpack and the bare "
        "xml.etree parse in parse_document. These are seeded for this check "
        "specifically: its record scopes itself to XXE, archive extraction and symlink "
        "following, none of which eval, shell=True, built SQL or md5 are, so without "
        "them bandit's shell rule would fire and make the check look exercised while "
        "its own subject went untested",
        ("unsafe-io",),
    ),
    Expectation(
        "docs/docstring-coverage",
        _FULL,
        "exact",
        "fixture_app.unsafe is the one non-empty module under src/ with no module "
        "docstring, so it is the file a docstring tool must name. It is not the only "
        "file lacking one: the three empty __init__.py files and three of the four "
        "test files have none either, so a tool naming those as well is reporting "
        "correctly rather than over-reporting. The count is interpolated from "
        "SOURCE_FILES, and the percentage each tool reports is recorded at the run "
        "rather than predicted here",
        ("undocumented",),
    ),
    Expectation(
        "test/determinism",
        _FULL,
        "exact",
        "tests/test_order.py fails under the shuffle seed recorded here and passes in "
        "file order. The seed is measured when the fixture is first built, never guessed",
        ("order-dependence",),
    ),
    Expectation(
        "test/isolation",
        _FULL,
        "exact",
        "tests/test_slow.py::test_slow_but_passing sleeps SLOW_TEST_SECONDS and so "
        "exceeds a pytest-timeout of ISOLATION_TIMEOUT_SECONDS, while passing with no "
        "timeout configured. Both are module constants rather than literals, because "
        "the sleep and the timeout are one fact and lowering either alone would retire "
        "the seed in silence - and both values are interpolated into the claim, since "
        "a reader of the published record cannot otherwise tell whether the sleep "
        "still exceeds the timeout, which is the seed's only load-bearing fact",
        ("slow-test",),
    ),
    Expectation(
        "test/mutation",
        _FULL,
        "floor",
        "at least one surviving mutant in fixture_app.invariant.clamp, whose two guard "
        "branches no test asserts. A floor because the count moves with the operator set",
        ("mutation-survivor",),
    ),
    Expectation(
        "test/property-based-gap",
        _FULL,
        "exact",
        "fixture_app.invariant.clamp has an obvious invariant, low <= result <= high, "
        "and no property test anywhere in the fixture",
        ("property-gap",),
    ),
)


def expectations_for(partition: str) -> tuple[Expectation, ...]:
    """Every expectation that applies to one partition."""
    if partition not in PARTITIONS:
        raise ValueError(f"unknown partition {partition!r}; expected one of {PARTITIONS}")
    return tuple(e for e in EXPECTATIONS if partition in e.partitions)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/scripts/test_python_fixture_spec.py -q`
Expected: PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format .
git add scripts/python_fixture_spec.py tests/scripts/test_python_fixture_spec.py
git commit -m "feat: state the expected result per check per fixture partition

Refs #45"
```

**Review findings folded back (landed as `eca1ff9`).** The spec-compliance reviewer materialized the tree and ran the tools rather than reasoning about them, which is why these were catchable at all. Four claims were false of the tree Tasks 1 and 2 build: `arch/complexity` sat one decision point below ruff's default and so would have recorded a correct run as a miss; `deps/inventory` claimed licences no route populates and transitives a `requirements.txt` cannot carry; `arch/martin-metrics` claimed a zone a mutual cycle makes arithmetically unreachable; `arch/hidden-coupling` asked the check to report something its record defines as out of scope. `arch/over-decomposition` and `arch/over-abstraction` both said a hit was a false positive while their records name triggers this fixture meets, so both are now hits with the records' read requirement stated.

Two structural additions the later tasks depend on:

- **`Expectation.ungranted`** - the round runs every entry under two grant states and several answers differ, deptry's DEP001-versus-DEP003 most sharply. Which entries carry it is derived from the records, never judged per entry: every Python tool tiered plus a non-`none` `ungranted_note`. Task 4 renders it; Task 6 grades against it.
- **`SEED_MARKERS` / `ABSENCE_SEEDS`** - the code-quality reviewer deleted the `eval` out of `run_expression` and the suite stayed green, because the module, the function, the seed list and every claim naming it all survived. A marker names the construct rather than the import that enables it, and the two collections partition every planted seed so a new one has to be classified rather than defaulting into silence.

The shuffle seed for `test/determinism` is recorded in the build smoke record that Task 7 writes, not in this module: it is a property of pytest-randomly's ordering rather than of the definition, and a placeholder constant would otherwise land in a published commit.

---

### Task 4: The expectations record, its gate and its README row

**Files:**
- Create: `scripts/render_python_fixture_expectations.py`
- Create: `docs/audit/python-fixture-expectations.md` (generated)
- Modify: `docs/audit/README.md`, `.github/workflows/ci.yml`, `CLAUDE.md`
- Test: `tests/scripts/test_python_fixture_spec.py`

**Interfaces:**
- Consumes: `EXPECTATIONS`, `DEPENDENCIES`, `PARTITIONS` from Tasks 1-3.
- Produces: `render() -> str`, and a `--check` flag that exits 1 on drift.

Follow `scripts/render_handbook_traceability.py`'s conventions: `--check` prints nothing and exits 0 on success. Read that script before writing this one.

- [ ] **Step 1: Write the failing test**

```python
import importlib.util
from pathlib import Path

_RENDERER = Path(__file__).resolve().parents[2] / "scripts" / "render_python_fixture_expectations.py"


def _load():
    spec = importlib.util.spec_from_file_location("render_expectations", _RENDERER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_rendered_table_names_every_expectation():
    from python_fixture_spec import EXPECTATIONS

    text = _load().render()
    for e in EXPECTATIONS:
        assert e.check in text


def test_the_rendered_table_carries_the_verified_evidence_per_dependency():
    from python_fixture_spec import DEPENDENCIES

    text = _load().render()
    for d in DEPENDENCIES:
        assert d.name in text
        assert d.evidence[:30] in text


def test_the_committed_record_matches_the_module():
    generated = _load().render()
    on_disk = (Path(__file__).resolve().parents[2] / "docs" / "audit" / "python-fixture-expectations.md").read_text()
    assert on_disk == generated
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/scripts/test_python_fixture_spec.py -q`
Expected: FAIL with `FileNotFoundError` on the renderer path

- [ ] **Step 3: Write the renderer**

Render, in order: a header saying the file is generated and must not be hand-edited, naming `VERIFIED_ON` so a reader can date the evidence without opening the history; the dependency table with pin, seeds and evidence; a partition table saying which checks each partition carries; and the expectation table with check, partitions, form and claim. Emit exactly one trailing newline. Support `--check` by comparing `render()` against the file on disk, printing a diff to stderr and exiting 1 on mismatch, printing nothing and exiting 0 on match.

The expectation table needs a second section for the grant axis, not a sixth column: `ungranted` is set on a minority of entries and prose long enough that a column would wrap unreadably. Render one row per entry that carries it, and state above the section how the rest are read - a check whose every Python tool needs a grant and whose record's `ungranted_note` is the `none` sentinel answers `no-evidence (not-permitted)` ungranted, and one with an untiered Python tool answers its `claim` in both states. Both are derived, so writing them out per entry would add copies to keep in step.

```python
"""Render docs/audit/python-fixture-expectations.md from the fixture spec.

Generated file: edit scripts/python_fixture_spec.py and re-render. `--check`
compares the two and is what stops them drifting apart; it prints nothing and
exits 0 when they agree, matching render_handbook_traceability.py.
"""

import argparse
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from python_fixture_spec import (  # noqa: E402
    DEPENDENCIES,
    EXPECTATIONS,
    FULL_PARTITION,
    PARTITIONS,
    expectations_for,
)

OUT_PATH = Path(__file__).resolve().parents[1] / "docs" / "audit" / "python-fixture-expectations.md"


def render() -> str:
    lines = [
        "# Python fixture expectations",
        "",
        "Generated by `scripts/render_python_fixture_expectations.py` from `scripts/python_fixture_spec.py`. Never edit this file: edit the module and re-render, and `--check` in CI is what holds the two together.",
        "",
        "The point of writing these down before the run is that a fixture whose expected output is not recorded in advance is just a smaller real target. Against a real repository an audit can only ask whether a command ran and returned something plausible; here the right answer is known first, so a tool that runs cleanly and reports half the truth fails instead of passing.",
        "",
        "## The shared dependency set",
        "",
        "Every partition declares the same logical set in its own manifest format, so one expectation table serves all five. Each pin was checked against OSV and PyPI before it was written down.",
        "",
        "| Package | Pin | Imported | Seeds | Evidence |",
        "|---|---|---|---|---|",
    ]
    for d in DEPENDENCIES:
        pin = f"`{d.pin}`" if d.pin else "*(undeclared)*"
        lines.append(
            f"| `{d.name}` | {pin} | {'yes' if d.imported else 'no'} | {', '.join(d.seeds)} | {d.evidence} |"
        )
    lines += [
        "",
        "## What each partition runs",
        "",
        f"`{FULL_PARTITION}` carries every `python:` entry in the family. The other four carry the `deps` records plus one `target-execution` check, which exists to prove that partition's own materialization route works rather than to re-test the tool.",
        "",
        "| Partition | Checks |",
        "|---|---|",
    ]
    for p in PARTITIONS:
        lines.append(f"| `{p}` | {len(expectations_for(p))} |")
    lines += [
        "",
        "## Expected result per check",
        "",
        "`exact` is a claim a correct tool cannot miss. `floor` is used where the count moves with the tool's version, so the expectation is a location and a minimum rather than a number that goes stale silently. `absence` is a check whose expected finding is that nothing is configured.",
        "",
        "| Check | Partitions | Form | Expected |",
        "|---|---|---|---|",
    ]
    for e in EXPECTATIONS:
        parts = "all" if set(e.partitions) == set(PARTITIONS) else ", ".join(f"`{p}`" for p in e.partitions)
        lines.append(f"| `{e.check}` | {parts} | {e.form} | {e.claim} |")
    lines += [
        "",
        "## A seed nothing detects",
        "",
        "A seeded finding that no tool reports is a finding about the skill family rather than a bug in the fixture. It is recorded as such and the seed stays, because removing it would erase the evidence that the family has a hole there.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare instead of writing")
    args = parser.parse_args()
    generated = render()
    if not args.check:
        OUT_PATH.write_text(generated)
        return 0
    current = OUT_PATH.read_text() if OUT_PATH.exists() else ""
    if current == generated:
        return 0
    sys.stderr.writelines(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            generated.splitlines(keepends=True),
            fromfile=str(OUT_PATH),
            tofile="rendered",
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Generate the record and verify the gate both ways**

```bash
uv run python scripts/render_python_fixture_expectations.py
uv run python scripts/render_python_fixture_expectations.py --check
echo "exit: $?"
```
Expected: the second command prints nothing and exits 0. Then confirm the gate can fail: append a character to the generated file, re-run `--check`, expect exit 1 and a diff on stderr, then re-render.

- [ ] **Step 5: Wire the gate and the docs**

Add to `.github/workflows/ci.yml`, after the traceability step, with a comment saying what drift it catches:

```yaml
      # The fixture definition and its published expectations are one artifact.
      # Editing the spec module without re-rendering fails here.
      - name: Fixture expectations integrity
        run: uv run python scripts/render_python_fixture_expectations.py --check
```

Add a row to the **Standing records** table in `docs/audit/README.md` - standing rather than verification, because it tracks the current definition rather than a dated observation. Add the render and `--check` commands to `CLAUDE.md`'s Commands block, and a `docs/audit/` bullet saying the file is generated.

- [ ] **Step 6: Run the full suite and commit**

```bash
uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .
git add scripts/render_python_fixture_expectations.py docs/audit/python-fixture-expectations.md docs/audit/README.md .github/workflows/ci.yml CLAUDE.md tests/scripts/test_python_fixture_spec.py
git commit -m "feat: publish the fixture expectations as a gated generated record

Refs #45"
```

---

### Task 5: The generator

**Files:**
- Create: `scripts/build_python_fixtures.py`
- Modify: `.gitignore`
- Test: `tests/scripts/test_python_fixture_build.py`

**Interfaces:**
- Consumes: `render_manifests`, `source_tree`, `PARTITIONS`.
- Produces: `plan_tree(partition) -> dict[str, str]` (pure), `lock_command(partition) -> tuple[str, ...]` (pure), and `build(partition, root)` (effectful).

Each fixture is a **git repository with everything committed**, for two reasons that both bite otherwise: Semgrep limits its scan to git-tracked files and says so only in a note, so an untracked tree would make all four `security` checks pass vacuously; and `git status --porcelain` empty before and after, which is the read-only check every run makes, is meaningless outside a repository.

Provision each manager from a pinned one-shot invocation rather than from whatever the machine carries, and record the version used in a `FIXTURE.md` inside each tree. `uv` is the exception and is used from the host: it is what runs the generator, so a pinned second copy would exercise a uv no caller uses. Its measured version is recorded the same way.

**The seeded package is src-layout, so materializing a partition has to install the project itself, not only its dependencies.** Running the suite against a tree where only the dependencies were installed fails at collection with `ModuleNotFoundError: No module named 'fixture_app'`, which looks exactly like a broken fixture rather than an incomplete install. Every partition therefore renders exactly one build manifest, and each partition's materialization route has to install through it rather than stopping at the dependencies. Confirmed by running the seeded suite both ways: without the package importable it is 2 collection errors, with it 5 passed.

**The build manifest is not a `pyproject.toml` everywhere, and the reason matters.** A `[project]` table carrying build metadata but no `dependencies` key is not silent about dependencies: it is an affirmative claim of zero, and deptry reads it in preference to `requirements.txt` and then reports the real dependencies as DEP001. So the `pip` and `pipenv` partitions carry a `setup.py` with no `install_requires` instead, which makes the package installable without competing with the partition's own declaration format. Task 2 verified each route end to end: `uv sync`; `poetry install`; `pip install -r requirements.txt` then `pip install -e . --no-deps`; `pipenv install` then `pipenv run pip install -e . --no-deps`, after which the `Pipfile` is byte-identical.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from build_python_fixtures import lock_command, plan_tree
from python_fixture_spec import PARTITIONS


def test_every_partition_plans_manifests_and_the_seeded_source():
    for partition in PARTITIONS:
        tree = plan_tree(partition)
        assert "src/fixture_app/unsafe.py" in tree, partition
        assert "tests/test_order.py" in tree, partition
        assert declaring_manifest(partition) in tree, partition


def test_each_partition_locks_with_its_own_manager():
    assert lock_command("uv")[0] == "uv"
    assert "poetry" in " ".join(lock_command("poetry"))
    assert "pipenv" in " ".join(lock_command("pipenv"))
    assert lock_command("pip") == ()


def test_an_unknown_partition_is_rejected_by_name():
    with pytest.raises(ValueError, match="conda"):
        plan_tree("conda")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/scripts/test_python_fixture_build.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'build_python_fixtures'`

- [ ] **Step 3: Implement**

Write `plan_tree(partition)` as `render_manifests(partition) | source_tree()`, `lock_command(partition)` returning the pinned one-shot lock invocation per manager (`uv lock`, `uvx poetry lock`, `uvx pipenv lock`, `()` for pip whose requirements file is already the lock, and for `pylock` the `uv export --format pylock.toml --frozen` route this round is testing), and `build(partition, root)` which writes the tree, runs `git init` plus an initial commit, runs the lock command, and commits the lock.

**The `pylock` partition must not keep the `uv.lock` it was built from.** `uv export --format pylock.toml` needs an existing `uv.lock`, and this partition's `pyproject.toml` is byte-identical to the `uv` partition's - so leaving both files behind makes every lock-reading tool read `pylock` as a second `uv` run, and the one format `pip-audit --locked` actually reads goes untested while the results look complete. Delete `uv.lock` after the export and before the commit, and assert in the build that the committed tree carries `pylock.toml` and no `uv.lock`. Every subprocess call checks its return code and raises with the command and the captured stderr; nothing swallows an exception.

Add `fixtures/` to `.gitignore` with a comment saying the generator writes there and why the trees are not committed.

- [ ] **Step 4: Build all five and verify**

```bash
caffeinate uv run python scripts/build_python_fixtures.py --all
for p in uv pip poetry pipenv pylock; do
  echo "$p: $(git -C fixtures/python/$p status --porcelain | wc -l) dirty, $(git -C fixtures/python/$p ls-files | wc -l) tracked"
done
```
Expected: every partition reports 0 dirty and a non-zero tracked count. A dirty tree means the lock step wrote after the commit and must be fixed here, not worked around at run time.

- [ ] **Step 5: Run the suite and commit**

```bash
uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .
git add scripts/build_python_fixtures.py tests/scripts/test_python_fixture_build.py .gitignore
git commit -m "feat: generate the five seeded Python fixture partitions

Refs #45"
```

**Review findings folded back (landed as `cf08edc`, corrections above and in the spec).** The generated trees byte-match the definition on all five partitions, each is a clean committed git repository, `pylock` carries no `uv.lock`, and nothing materializes into any tree. Four deviations from this plan as written, recorded here because three of them were made during implementation and the fourth left two committed documents asserting something false of the code:

- **`uv` is used from the host, not pinned.** Step 1's provisioning line and the spec's "provisioned from its own pinned manager" both said every manager is pinned. The code pins poetry and pipenv only, and it is right to: uv is what runs the generator, so a pinned second copy would exercise a uv no caller uses. Both documents now state the exception, and the measured host version is recorded in every tree.
- **Step 1's tree assertion was wrong for `pip`.** It accepted `pyproject.toml` or `Pipfile` for every partition, and `render_manifests("pip")` returns neither - it returns `requirements.txt` and `setup.py`, which this same task's prose explains at length. Amended above to assert each partition's own declaring manifest, which is also the stronger claim.
- **`lock_command` was one command and `pylock` needs three steps** - lock, export, then delete the lock. Split into `prelock_commands` and `discard_after_lock`, both pure and both tested, rather than overloading one function with a partition special case.
- **`declaring_manifest` and `BUILD_METADATA` were added** because the first `FIXTURE.md` told its reader that pip and pipenv declare dependencies in `requirements.txt` *and* `setup.py`, which is the opposite of what `setup.py` is written to do - it carries build metadata and no `install_requires`, precisely so deptry cannot read it as a competing declaration.

One thing the review found that Task 7 should not re-litigate: the `pip` tree's `FIXTURE.md` calls `requirements.txt` "this partition's lock". It pins the declared set with `==` and nothing else, and the expectations record says in as many words that the partition has no transitive resolution - so the wording is corrected there rather than the record being loosened to match it.

---

### Task 6: The harness

**Files:**
- Create: `scripts/run_python_fixture_lens.py`
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Produces: `Invocation`, `INVOCATIONS`, `classify(returncode, stdout, stderr, tool_present) -> tuple[str, str]`, `tools_named_in_records() -> set[str]`.

The command table holds **each record's prescribed invocation verbatim**, keyed by check id, with the record's own sentence quoted beside it. That is the mechanism, not decoration: someone running these by hand repairs a broken command as they go and the repair never reaches the record, whereas here the deviation needed to make a tool work is a diff against the transcription.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from python_fixture_spec import DEPS_CHECKS
from run_python_fixture_lens import INVOCATIONS, classify, tools_named_in_records

SKILLS = Path(__file__).resolve().parents[2] / ".agents" / "skills"


def test_every_python_tool_in_the_family_is_invoked():
    assert {i.tool for i in INVOCATIONS} == tools_named_in_records()


def test_no_check_invokes_the_same_tool_twice():
    pairs = [(i.check, i.tool) for i in INVOCATIONS]
    assert len(pairs) == len(set(pairs))


def test_a_tool_answering_several_checks_is_invoked_once_per_check():
    ruff_checks = {i.check for i in INVOCATIONS if i.tool == "ruff"}
    assert {"arch/complexity", "docs/docstring-coverage"} <= ruff_checks


def test_every_invocation_quotes_its_record_verbatim():
    for inv in INVOCATIONS:
        domain, slug = inv.check.split("/")
        path = SKILLS / f"{domain}-audit" / "checks" / f"{slug}.md"
        text = path.read_text()
        assert text.count(inv.record_quote) == 1, f"{inv.check}: {inv.record_quote[:40]}"


def test_classify_maps_a_missing_tool_to_no_evidence():
    status, reason = classify(127, "", "command not found", tool_present=False)
    assert status == "no-evidence"
    assert reason == "tool-unavailable"


def test_classify_maps_a_nonzero_exit_from_a_present_tool_to_tool_failed():
    status, reason = classify(2, "", "boom", tool_present=True)
    assert (status, reason) == ("no-evidence", "tool-failed")


def test_classify_maps_clean_output_to_ok():
    assert classify(0, "findings", "", tool_present=True) == ("ok", "")


def test_the_deps_checks_are_all_represented():
    assert set(DEPS_CHECKS) <= {i.check for i in INVOCATIONS}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/scripts/test_python_fixture_harness.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'run_python_fixture_lens'`

- [ ] **Step 3: Implement**

`tools_named_in_records()` walks `.agents/skills/*/checks/*.md`, parses the frontmatter and returns the union of every `tooling.python` list - the same source the exact-set guard compares against, so a tool added to a record and forgotten here fails the suite.

`INVOCATIONS` carries one entry per **(check, tool) pair** rather than per tool, because a tool that answers several checks needs a different invocation for each: `ruff` selects `C901` for `arch/complexity`, the `S` ruleset for the four `security` checks and the `D` ruleset for `docs/docstring-coverage`, and collapsing those into one entry would test one rule selection and report it as three. The entry holds the check id, the tool, the argv transcribed from the record, the grant state it needs, and `record_quote`, a sentence that occurs **exactly once** in that record. Take each quote by reading the record, never from memory. Where a record names a tool without prescribing an argv - a reading pass such as `test/property-based-gap` - set `argv` to `()` and let the quote carry the reading procedure.

`classify` is pure and maps an observation into the engine's vocabulary: an absent tool is `no-evidence (tool-unavailable)`, a present tool exiting non-zero is `no-evidence (tool-failed)`, a withheld grant is `no-evidence (not-permitted)`, and anything else is `ok`. It never returns a status outside that vocabulary, because the whole point of the round is that the engine's scale does not grow.

The runner itself takes a partition and a grant state, runs the applicable invocations, and writes a results file into the fixture directory. It never writes into the fixture's tracked tree.

**Run a `deps` tool from inside the materialized environment, not through a one-shot runner, wherever the granted state provides one.** Task 2 measured the difference on the same tree: `uvx deptry` reported markupsafe as DEP001, and deptry run from inside the materialized environment reported it as DEP003, which is what the expectation claims. The two answers differ because the runner's sandbox cannot see what the target actually resolved, so the same command reports a missing dependency where the truth is a transitive one. A harness that gets this wrong makes a correct expectation fail and would send PR 2 off to "fix" a record that was right.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/scripts/test_python_fixture_harness.py -q`
Expected: PASS. The verbatim-quote test failing means a quote was paraphrased; fix the quote, never the record.

- [ ] **Step 5: Run the suite and commit**

```bash
uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .
git add scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
git commit -m "feat: transcribe every python: invocation into a guarded harness

The table holds each record's prescribed command verbatim so that a command
which has to be changed to work shows up as a diff against the record rather
than being quietly repaired by whoever runs it.

Refs #45"
```

---

### Task 7: The build smoke, and the measured seed

**Review findings folded back (landed as `2d130dd`).** Every measurement in the record was independently re-run and reproduced exactly, including the sweep. Three deviations from this task as written, all deliberate and all now the shipped behaviour:

- **The seed is not written into `scripts/python_fixture_spec.py` and the expectations record is not re-rendered**, contrary to the Files list and Step 5 below. It is not stable across plugin majors - seed 4 reverses the pair under pytest-randomly 4.1.0 and passes under 3.15.0 and 3.16.0, where the smallest reversing seed is 0 - so a generated record stating it would publish a number that stops being true on a plugin bump, with nothing to say so. The `test/determinism` expectation already points at the smoke record for exactly this reason.
- **The seed is measured in a scratch copy, not in `fixtures/python/uv`.** Step 1's snippet predates the read-only invariant the generator now enforces: running there writes `.venv` and `.pytest_cache` into a committed tree. Do not follow that snippet literally.
- **Step 2 points tools at the seeds directly rather than through the Task 6 harness.** The harness grades transcribed record commands under grant states, which is PR 2's job, and using it here would have invited the record correction PR 1 forbids.

One correction the review found in the published record rather than in the code: the README row compressed "observed by a tool, or by the reading pass the check record prescribes" into "the one seed no tool reached", which is false - three seeds are answered by a read, and a reader of the index would have come away believing 21 were tool-reported.

**Files:**
- Modify: `scripts/python_fixture_spec.py` (the recorded shuffle seed), `docs/audit/python-fixture-expectations.md` (re-rendered)
- Create: `docs/audit/python-fixture-build-smoke.md`

This is PR 1's gate: it proves the fixtures can produce their own ground truth, so PR 2 starts from a fixture that works rather than discovering it does not.

- [ ] **Step 1: Measure the shuffle seed**

The order-dependent pair is green in file order by construction. Find the smallest `pytest-randomly` seed that reverses the two tests in `tests/test_order.py`:

```bash
cd fixtures/python/uv
for s in $(seq 0 60); do
  if ! caffeinate uv run --with pytest-randomly pytest tests/test_order.py -p randomly -q --randomly-seed=$s >/dev/null 2>&1; then
    echo "seed $s reverses them"; break
  fi
done
```

Record the seed in the `test/determinism` expectation's `claim`, re-render the expectations record, and confirm `--check` passes. A measured seed, never a guessed one.

- [ ] **Step 2: Confirm every seed is detectable by at least one tool**

On the `uv` fixture, run one tool per seed and record what came back. At minimum: `ruff` for the complexity and dangerous-call seeds, `vulture` for dead code, `grimp` or `import-linter` for the cycle, `deptry` for both hygiene seeds, `pip-audit` for the advisories, `pip-licenses` for the copyleft entry, `interrogate` for the docstring seed, `pytest --cov` for the uncovered branches, and `pytest --timeout=1` for the slow test.

An undetected seed is recorded as a finding about the family and the seed stays. A seed that is undetectable because the fixture is malformed is fixed here.

- [ ] **Step 3: Write the smoke record**

`docs/audit/python-fixture-build-smoke.md`: what was built, each manager and the version used, the measured seed, and one line per seed saying which tool saw it. State plainly that this is a build smoke and **not** the verification round: no check record is corrected on its evidence, and PR 2 is where the entries are actually exercised under both grant states.

- [ ] **Step 4: Final gates**

```bash
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check; echo "traceability exit: $?"
uv run python scripts/render_python_fixture_expectations.py --check; echo "expectations exit: $?"
git status --short
```
Expected: tests pass, ruff clean, both gates silent at exit 0, and no fixture tree in `git status`.

- [ ] **Step 5: Commit**

```bash
git add docs/audit/python-fixture-build-smoke.md docs/audit/python-fixture-expectations.md scripts/python_fixture_spec.py docs/audit/README.md
git commit -m "docs: record the fixture build smoke and the measured shuffle seed

Refs #45"
```

---

## Self-review notes

- **Spec coverage.** Every PR 1 item in the spec's Delivery section maps to a task: spec module (1-3), generator (5), harness (6), expectations record and gate (4), unit tests (throughout), README row (4), `.gitignore` (5), build smoke (7).
- **Deferred to PR 2 by design:** the two grant-state runs, the record corrections, `docs/audit/python-lens-smoke-run.md`, and the three named holes. None of them can be specified before the observations exist.
- **The one measured value** in this plan is the shuffle seed, and it has a command that measures it rather than a number to invent.
