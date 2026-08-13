"""Definition of the seeded Python fixtures (#45).

One dependency set, one seeded source tree, five manifest renderings and one
expectations table, all from this module. The fixture tree and the expectations
are produced from the same definition on purpose: expectations kept in a second
file are free to drift, and a seed present in the tree but missing from the
expectations reads exactly like a tool that correctly found nothing.

Every pin below carries an `evidence` string, and each was checked against OSV
and PyPI on VERIFIED_ON rather than recalled. Re-checking one means querying
those two sources again and updating both the pin and its evidence, because a
pin whose advisories nobody re-read is the unverified claim this whole round
exists to remove.

Pure. Nothing here touches the filesystem, the network or a subprocess.
"""

from dataclasses import dataclass

# The date every `Dependency.evidence` string below was measured. It is rendered
# into the published expectations record, so a reader can tell how old the
# numbers are without opening the git history.
VERIFIED_ON = "2026-08-13"

PARTITIONS = ("uv", "pip", "poetry", "pipenv", "pylock")

# The partition that carries every `python:` entry. The other four carry the
# `deps` records plus pytest-cov, which is tiered `target-execution` and so
# fails if either half of that partition's materialization route is broken.
# The `deps` records are counted from DEPS_CHECKS rather than stated here, so
# the claim cannot go stale when a record is added to that domain.
FULL_PARTITION = "uv"

PACKAGE = "fixture_app"

# The interpreter floor is one fact each manifest format spells its own way
# (`requires-python = ">=x.y"`, `python_version = "x.y"`), so it is named once
# and interpolated rather than written out per format, where the copies would be
# free to disagree.
PYTHON_FLOOR = "3.12"

# Every partition installs the seeded package under this version. It is the
# fixture's own version, unrelated to any dependency pin, and it is named here
# so that the manifest renderers and the build metadata cannot drift apart.
PACKAGE_VERSION = "0.1.0"


@dataclass(frozen=True)
class Dependency:
    """One entry in the shared dependency set.

    `pin` is empty for the dependency the fixture imports without declaring,
    which arrives transitively instead.

    `module` is the name the source imports, which is not always the name the
    manifest declares - `Unidecode` is declared under that name and imported as
    `unidecode`. Keeping both means a test can assert that an `imported=True`
    entry really is imported somewhere in the seeded tree, which is the half of
    the single-definition promise the seed lists alone cannot keep.
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
        "it the transitive root. 2.11.3 carries four of the same CVEs and is not "
        "usable here: it imports soft_unicode, removed in markupsafe 2.1, so the "
        "seeded package would not import at all",
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
    """One file written into every fixture tree.

    `seeds` names the findings this file is planted to produce, and every name
    in it has to appear in some expectation: a seed nothing expects is a
    planted finding no run would notice going missing.
    """

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

# security/unsafe-io scopes itself to XXE, unchecked archive extraction,
# world-writable temp files and symlink following - none of which `eval`,
# `shell=True`, string-built SQL or md5 are. Without a surface in that scope the
# check would look exercised because bandit's shell rule fires, while its own
# subject went untested, and a clean result would then be recorded as a hole in
# the family rather than a gap in the fixture. So extractall and a bare XML
# parse are seeded for it specifically.
_UNSAFE = """import hashlib
import subprocess
import tarfile
import xml.etree.ElementTree


def run_expression(expr):
    return eval(expr)


def run_shell(name):
    return subprocess.run("ls " + name, shell=True, check=False)


def digest(value):
    return hashlib.md5(value.encode()).hexdigest()


def query(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = '%s'" % user_id)


def unpack(archive_path, destination):
    with tarfile.open(archive_path) as archive:
        archive.extractall(destination)


def parse_document(raw):
    return xml.etree.ElementTree.fromstring(raw)
"""

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

_TEST_RENDER = """from fixture_app import render


def test_render_greets():
    assert "hello" in render.render("Jose")
"""

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

# The sleep and the timeout the check runs with are one fact in two places, so
# they are named here and interpolated rather than written twice. Lowering the
# sleep below the timeout would silently retire the seed.
SLOW_TEST_SECONDS = 2
ISOLATION_TIMEOUT_SECONDS = 1

_TEST_SLOW = f"""import time


def test_slow_but_passing():
    time.sleep({SLOW_TEST_SECONDS})
    assert True
"""

_TEST_PARTIAL = """from fixture_app import invariant


def test_clamp_passes_through():
    assert invariant.clamp(5, 0, 10) == 5
"""

SOURCE_FILES = (
    SourceFile(f"src/{PACKAGE}/__init__.py", "", ()),
    SourceFile(f"src/{PACKAGE}/domain/__init__.py", "", ()),
    SourceFile(f"src/{PACKAGE}/domain/model.py", _MODEL, ("cycle", "layering")),
    SourceFile(f"src/{PACKAGE}/infra/__init__.py", "", ()),
    SourceFile(f"src/{PACKAGE}/infra/store.py", _STORE, ("cycle",)),
    SourceFile(f"src/{PACKAGE}/complexity.py", _COMPLEXITY, ("complexity",)),
    SourceFile(
        f"src/{PACKAGE}/unsafe.py",
        _UNSAFE,
        ("dangerous-calls", "injection", "crypto", "unsafe-io", "undocumented"),
    ),
    SourceFile(f"src/{PACKAGE}/deadcode.py", _DEADCODE, ("dead-code",)),
    SourceFile(f"src/{PACKAGE}/render.py", _RENDER, ("undeclared-import",)),
    SourceFile(
        f"src/{PACKAGE}/invariant.py",
        _INVARIANT,
        ("property-gap", "mutation-survivor", "uncovered-branch"),
    ),
    SourceFile("tests/test_render.py", _TEST_RENDER, ()),
    SourceFile("tests/test_order.py", _TEST_ORDER, ("order-dependence",)),
    SourceFile("tests/test_slow.py", _TEST_SLOW, ("slow-test",)),
    SourceFile(
        "tests/test_partial.py",
        _TEST_PARTIAL,
        ("mutation-survivor", "uncovered-branch"),
    ),
)


def source_tree() -> dict[str, str]:
    """Map every seeded path to its body."""
    return {f.path: f.body for f in SOURCE_FILES}


def declared() -> tuple[Dependency, ...]:
    """The dependencies a manifest names. Excludes the undeclared-import seed."""
    return tuple(d for d in DEPENDENCIES if d.pin)


# One partition declares the shared set in exactly one file. Two files both
# naming the set would let each tool pick whichever format it prefers, and a
# partition whose format is never the one read has stopped exercising the lens
# it exists for while still producing a full, plausible result - the failure the
# round is built to catch, arriving from the fixture rather than from the tool.
#
# That is why the `pip` and `pipenv` partitions carry a `setup.py` rather than a
# `pyproject.toml` for their build metadata. The seeded package is src-layout,
# so materializing a partition has to install the project and not only its
# dependencies, which needs a build manifest; but a `[project]` table declares a
# dependency list even when the key is absent, and an absent list is the claim
# that there are none. `setup.py` carries `package_dir` and `packages` and no
# `install_requires`, so it makes the project installable while declaring
# nothing, leaving `requirements.txt` and the `Pipfile` as the only declaration
# in their trees.
_SETUP_PY = f'''"""Build metadata only, so that the src-layout package installs.

The dependency set is declared in this partition's own manifest format rather
than here: `install_requires` would be a second declaration of the same set, and
a tool reading it would report this partition's format as untested while looking
like it had run.
"""

from setuptools import find_packages, setup

setup(
    name="{PACKAGE}",
    version="{PACKAGE_VERSION}",
    python_requires=">={PYTHON_FLOOR}",
    package_dir={{"": "src"}},
    packages=find_packages(where="src"),
)
'''


def _pep621_pyproject() -> str:
    """PEP 621 metadata with a static dependency list, for `uv` and `pylock`."""
    pins = "\n".join(f'    "{d.name}=={d.pin}",' for d in declared())
    return (
        "[project]\n"
        f'name = "{PACKAGE}"\n'
        f'version = "{PACKAGE_VERSION}"\n'
        f'requires-python = ">={PYTHON_FLOOR}"\n'
        "dependencies = [\n"
        f"{pins}\n"
        "]\n"
        "\n"
        "[build-system]\n"
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
    )


def _poetry_pyproject() -> str:
    """PEP 621 metadata whose dependency list is dynamic and comes from poetry.

    The declaration lives in `[tool.poetry.dependencies]`, which is the table
    the poetry lens exists to read, and `dynamic = ["dependencies"]` is what
    makes that table the source rather than a second copy of a static
    `[project]` list. Poetry's older all-in-`[tool.poetry]` form declares the
    same thing but reports its metadata keys as deprecated, so a partition built
    on it would be testing a route poetry is retiring.
    """
    # Quoted keys, so a distribution name containing a dot stays one key rather
    # than parsing as a nested table that TOML accepts and poetry misreads.
    pins = "\n".join(f'"{d.name}" = "{d.pin}"' for d in declared())
    return (
        "[project]\n"
        f'name = "{PACKAGE}"\n'
        f'version = "{PACKAGE_VERSION}"\n'
        'description = "Seeded audit fixture"\n'
        f'requires-python = ">={PYTHON_FLOOR}"\n'
        'dynamic = ["dependencies"]\n'
        "\n"
        "[tool.poetry]\n"
        f'packages = [{{ include = "{PACKAGE}", from = "src" }}]\n'
        "\n"
        "[tool.poetry.dependencies]\n"
        f"{pins}\n"
        "\n"
        "[build-system]\n"
        # The floor is load-bearing rather than tidy: PEP 621 metadata with a
        # dynamic dependency list is what poetry-core 2 added.
        'requires = ["poetry-core>=2.0"]\n'
        'build-backend = "poetry.core.masonry.api"\n'
    )


def _pipfile() -> str:
    """A Pipfile whose `[packages]` pins use pipenv's `"==x.y.z"` string form.

    No `[requires]` table. Pipenv's `python_version` there is an exact
    interpreter requirement rather than the floor every other format states, so
    including it would make this the one partition that refuses to materialize
    on a host whose interpreter is newer - a fixture failing for a reason that
    has nothing to do with what it is testing. The floor is stated by `setup.py`,
    which this partition renders alongside the Pipfile.

    Keys are quoted so that a distribution name containing a dot stays one key
    instead of parsing as a nested table.
    """
    pins = "\n".join(f'"{d.name}" = "=={d.pin}"' for d in declared())
    return (
        "[[source]]\n"
        'url = "https://pypi.org/simple"\n'
        "verify_ssl = true\n"
        'name = "pypi"\n'
        "\n"
        "[packages]\n"
        f"{pins}\n"
    )


def _requirements() -> str:
    return "".join(f"{d.name}=={d.pin}\n" for d in declared())


def render_manifests(partition: str) -> dict[str, str]:
    """Return {relative path: content} for one partition's declared manifests.

    Lock files are absent by design: each manager generates its own, which is
    the difference the five partitions exist to exercise.
    """
    if partition not in PARTITIONS:
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {PARTITIONS}"
        )
    if partition in ("uv", "pylock"):
        return {"pyproject.toml": _pep621_pyproject()}
    if partition == "poetry":
        return {"pyproject.toml": _poetry_pyproject()}
    if partition == "pip":
        return {"requirements.txt": _requirements(), "setup.py": _SETUP_PY}
    if partition == "pipenv":
        return {"Pipfile": _pipfile(), "setup.py": _SETUP_PY}
    # Unreachable while PARTITIONS and the branches above agree. Adding a name
    # to PARTITIONS and no rendering for it lands here rather than falling
    # through to whichever branch happened to be written last, which would give
    # the new partition another partition's manifest and no error.
    raise ValueError(
        f"partition {partition!r} is named in PARTITIONS but has no manifest rendering"
    )


# The `deps` records are the ones every partition runs, because a dependency
# lens reads the partition's own manifest and lock format and so answers a
# different question in each of the five. Listed here rather than derived from
# the `deps/` prefix in EXPECTATIONS so that the thin-partition scoping has a
# name to be written against; a test holds the two views equal.
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


def _partitions_except(*excluded: str) -> tuple[str, ...]:
    """Every partition but the named ones.

    Written as a subtraction over PARTITIONS rather than as a literal tuple for
    two reasons. A literal stops tracking PARTITIONS, so a sixth partition would
    drop out of a scoped check with nothing to say so; and a misspelled
    exclusion silently returns every partition, which is the opposite of what
    the caller asked for - the expectation would then claim the one partition it
    was written to exclude. Both scoped checks here exclude exactly one
    partition for a stated reason, so getting that name wrong inverts the claim.
    """
    unknown = sorted(set(excluded) - set(PARTITIONS))
    if unknown:
        raise ValueError(f"not partitions: {unknown}; expected names from {PARTITIONS}")
    return tuple(p for p in PARTITIONS if p not in excluded)


# Every file the fixture writes without a module docstring. The docstring seed
# lives in one of them, but a per-file report names them all, so the expectation
# is written against this rather than against the seeded file alone.
_FILES_WITHOUT_MODULE_DOCSTRING = tuple(
    f.path for f in SOURCE_FILES if not f.body.startswith('"""')
)

# The seeded package's module count, for the over-decomposition expectation.
# Computed rather than stated: the claim there is that the package is far below
# any threshold, and a typed-in number stops being that claim the first time a
# seed is added.
_SRC_MODULE_COUNT = sum(1 for f in SOURCE_FILES if f.path.startswith(f"src/{PACKAGE}/"))


@dataclass(frozen=True)
class Expectation:
    """What a check must observe on a partition, and why that form.

    `claim` is prose because the observation is prose: what a reader needs is
    the thing to look for, not a number a later tool version invalidates.

    `partitions` is a scope rather than a convenience. A check whose answer
    differs by partition is written as two entries with disjoint scopes, not as
    one entry with a hedge, so that a run against one partition has exactly one
    right answer to fail against.
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
        "positive, which an expectation naming all of them could never have caught. "
        "Named rather than counted, because the count moves with the dependency set "
        "while which one is the control does not",
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
        _partitions_except("pipenv"),
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
        _partitions_except("poetry"),
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
        f"the seeded package is {_SRC_MODULE_COUNT} files under src/, far below any "
        "over-decomposition threshold, so the expected result is a clean row and a hit "
        "here is a false positive. The count is computed from SOURCE_FILES rather than "
        "typed in, since a typed-in one would go stale the first time a seed is added",
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
        f"docstring, so it carries the seed. It is not alone: {len(_FILES_WITHOUT_MODULE_DOCSTRING)} "
        "of the seeded files have no module docstring, the others being the empty "
        "package __init__ files and those seeded test files that open with code, so a "
        "per-file report names them too and the expectation is that unsafe.py is among "
        "them rather than the only one. Written that way because naming one file would "
        "correct output read as over-reporting. Function-level coverage is low across "
        "the whole seeded package rather than in that file alone, so the percentage "
        "each tool reports is recorded at the run rather than predicted here",
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
        f"tests/test_slow.py::test_slow_but_passing sleeps {SLOW_TEST_SECONDS}s and so "
        f"exceeds a pytest-timeout of {ISOLATION_TIMEOUT_SECONDS}s, while passing with "
        "no timeout configured. Both numbers are interpolated from the module constants "
        "the seeded file itself is written from, because the sleep and the timeout are "
        "one fact and lowering either alone would retire the seed in silence",
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
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {PARTITIONS}"
        )
    return tuple(e for e in EXPECTATIONS if partition in e.partitions)
