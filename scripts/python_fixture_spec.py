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

import re
from dataclasses import dataclass

# The date every `Dependency.evidence` string below was measured. It is rendered
# into the published expectations record, so a reader can tell how old the
# numbers are without opening the git history.
VERIFIED_ON = "2026-08-13"

PARTITIONS = ("uv", "pip", "poetry", "pipenv", "pylock")

# The partition that carries every `python:` entry. Every other partition carries
# the `deps` records plus pytest-cov, which is tiered `target-execution` and so
# fails if either half of that partition's materialization route is broken.
# It is `uv` because uv is how the whole fixture set is built: it resolves the
# tree, exports the requirements and PEP 751 partitions directly, and runs the
# poetry and pipenv lock steps as one-shot commands. The partition that has to
# answer every check is the one whose toolchain can build every fixture.
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


def _by_name(name: str) -> Dependency:
    """The one dependency with this name, or a failure naming what is there.

    Used where an expectation needs a specific pin's own evidence. Raising
    rather than returning None matters: a silent miss would leave the claim that
    reads the evidence quietly empty, which is the shape of a seed that has gone
    missing without anything noticing.
    """
    for dependency in DEPENDENCIES:
        if dependency.name == name:
            return dependency
    raise ValueError(
        f"no dependency named {name!r}; have {[d.name for d in DEPENDENCIES]}"
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

# Every branch below is an explicit `if`/`elif`, never a conditional expression.
# Ruff's C901 does not walk a ternary and radon does, so a seed leaning on one
# measures differently in the two engines - and C901 fires on `>` rather than
# `>=`, so a function landing exactly on ruff's default of 10 passes in silence
# while radon reports it over. Replacing a branch here with `x if c else y`
# lowers ruff's count and can retire the seed without failing anything.
_COMPLEXITY = '''"""One function over the default complexity threshold of every seeded tool."""


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
        if e > 0:
            total += 8
        else:
            total += 9
    elif d > 0 and e > 0:
        total += 10
    elif d > 0:
        total += 11
    else:
        total += 12
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
empty list and fails. The shuffle seed that reverses them is measured when the
fixture is built and recorded in the build smoke record, never guessed.
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
    SourceFile(
        f"src/{PACKAGE}/domain/model.py",
        _MODEL,
        ("cycle", "layering", "pass-through"),
    ),
    SourceFile(f"src/{PACKAGE}/infra/__init__.py", "", ()),
    SourceFile(f"src/{PACKAGE}/infra/store.py", _STORE, ("cycle", "pass-through")),
    SourceFile(f"src/{PACKAGE}/complexity.py", _COMPLEXITY, ("complexity",)),
    SourceFile(
        f"src/{PACKAGE}/unsafe.py",
        _UNSAFE,
        ("dangerous-calls", "injection", "crypto", "unsafe-io", "undocumented"),
    ),
    SourceFile(f"src/{PACKAGE}/deadcode.py", _DEADCODE, ("dead-code", "single-caller")),
    SourceFile(f"src/{PACKAGE}/render.py", _RENDER, ("undeclared-import",)),
    SourceFile(
        f"src/{PACKAGE}/invariant.py",
        _INVARIANT,
        ("property-gap", "mutation-survivor", "uncovered-branch", "single-caller"),
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


# The construct in the seeded source that each positive seed is planted as. A
# seed name and an expectation naming a function are both survivable: deleting
# the `eval` out of `run_expression` leaves the name, the file and the seed list
# all intact, and every claim naming it still reads true - which is a planted
# finding that has quietly stopped being planted, indistinguishable at review
# from a fixture that still seeds it. Each marker must occur in some file
# carrying that seed, so the construct cannot leave without the suite saying so.
SEED_MARKERS = {
    # Both of these seeds are carried by two files, one per direction, and a
    # marker only has to occur in some carrying file - so a single marker would
    # be satisfied by whichever direction survived. One marker per direction.
    "cycle": (f"import {PACKAGE}.infra.store", f"import {PACKAGE}.domain.model"),
    "layering": (f"import {PACKAGE}.infra.store",),
    "pass-through": (
        f"return {PACKAGE}.infra.store.read(",
        f"return {PACKAGE}.domain.model.load(",
    ),
    "complexity": ("def classify",),
    "dangerous-calls": ("eval(",),
    "injection": ("shell=True", "SELECT * FROM"),
    "crypto": ("md5(",),
    # `xml.etree` alone would match the import line and so survive the parse
    # call being deleted, which is the whole failure this mapping exists to
    # catch. Every marker names the construct, never the import that enables it.
    "unsafe-io": ("extractall(", "ElementTree.fromstring("),
    "undeclared-import": ("import markupsafe",),
    # The mutation, not the declaration: `_SEEN` alone survives the append being
    # deleted, and the append is what makes the pair order-dependent.
    "order-dependence": ("_SEEN.append(",),
    "slow-test": ("time.sleep(",),
    "mutation-survivor": ("def clamp",),
    "uncovered-branch": ("def clamp",),
}

# The seeds that are the absence of something, which no marker can express: a
# missing module docstring, a function nobody calls, a second caller that does
# not exist, a property test nobody wrote. Named rather than left out of
# SEED_MARKERS, because absence and oversight look identical in a mapping - a
# test holds these two collections to a partition of every planted seed, so a
# new seed has to be classified rather than defaulting into silence.
ABSENCE_SEEDS = ("undocumented", "dead-code", "single-caller", "property-gap")


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

# The seeded package's file count, for the over-decomposition expectation. Files
# rather than modules: the empty package `__init__.py` files are counted here
# because a graph tool counts them as nodes too, and calling them modules would
# overstate what the package actually decomposes into.
_SRC_FILE_COUNT = sum(1 for f in SOURCE_FILES if f.path.startswith(f"src/{PACKAGE}/"))

# The files under src/ that import the seeded package by its own name. deptry
# treats a src-layout package's self-imports as third-party and emits one DEP003
# per importing module, so this is the size of that expected false-positive set.
# Derived, because seeding another module that closes over the cycle would change
# the number and a typed-in one would then understate the tool's output.
_SRC_FILES_IMPORTING_PACKAGE = tuple(
    f.path
    for f in SOURCE_FILES
    if f.path.startswith(f"src/{PACKAGE}/") and f"import {PACKAGE}" in f.body
)

# The CVEs behind the `vulnerable` seed, read out of the pin's own evidence
# rather than restated. A floor written as a typed-in number drifts from the
# evidence the moment a pin is re-verified, and the two would then disagree with
# nothing to say which was current.
_JINJA2_CVES = tuple(
    sorted(set(re.findall(r"CVE-\d{4}-\d+", _by_name("jinja2").evidence)))
)

# The three forms an expectation can take. Named here rather than only in the
# test that checks them, because the renderer and the PR 2 harness both have to
# branch on this vocabulary and a third copy is a third thing to keep in step.
FORMS = ("exact", "floor", "absence")


@dataclass(frozen=True)
class Expectation:
    """What a check must observe on a partition, and why that form.

    `claim` is prose because the observation is prose: what a reader needs is
    the thing to look for, not a number a later tool version invalidates.

    `partitions` is a scope rather than a convenience. A check whose answer
    differs by partition is written as one entry per scope, the scopes disjoint,
    not as one entry with a hedge, so that a run against one partition has
    exactly one right answer to fail against.

    `ungranted` is the second axis, and it exists because the round runs every
    entry under two grant states. It is set on exactly the entries whose answer
    the grant moves. `claim` is the answer with the grant; this is
    the answer without it, and it is set on exactly the checks where the two
    differ - which is derivable rather than a judgement call, so a test derives
    it. On a record declaring `tooling:`, a check whose every Python tool
    carries a `needs` tier answers something different ungranted, and that
    record's `ungranted_note` already says what. Where the note is the `none`
    sentinel the ungranted answer is `no-evidence (not-permitted)` and needs no
    restating here; where some Python tool needs no grant at all, `claim`
    already holds in both states. Which schema a record declares does not decide
    whether the grant moves its answer: what decides it is whether every Python
    tool the record offers carries a tier, and whether the record still says
    something answers without one. The two schemas say that second thing in
    different places - `ungranted_note` on one, an untiered answering route on
    the other, which is commonly a route carrying no tool at all and so
    invisible in the projected `tooling`/`needs` pair - and the test that
    derives this field reads whichever place the record's own schema uses.
    So whether this field is set is decided by a record's tools and its
    answering routes and never by which schema it declares, which is why the
    paragraph names no record here: the set that carries the axis moves with
    every migration, and a list of it would read as exhaustive one task later.
    Reconciling this paragraph against the entries by stripping the axis from a
    routes record is the move to avoid: it flips the derivation the other way
    and regrades every ungranted run of that check. Without
    this field a correct ungranted run of `deps/hygiene` - which reports DEP001
    where the granted run reports DEP003 - would be graded against the granted
    answer and recorded as a tool defect.
    """

    check: str
    partitions: tuple[str, ...]
    form: str
    claim: str
    seeds: tuple[str, ...]
    ungranted: str = ""

    def __post_init__(self) -> None:
        if self.form not in FORMS:
            raise ValueError(
                f"unknown form {self.form!r} for {self.check}; expected one of {FORMS}"
            )
        unknown = sorted(set(self.partitions) - set(PARTITIONS))
        if unknown:
            raise ValueError(
                f"not partitions: {unknown} for {self.check}; expected names from {PARTITIONS}"
            )


EXPECTATIONS = (
    Expectation(
        "deps/vulnerabilities",
        _ALL,
        "floor",
        f"at least {len(_JINJA2_CVES)} distinct CVEs against jinja2 "
        f"{_by_name('jinja2').pin}: {', '.join(_JINJA2_CVES)}. The floor is read out of "
        "the pin's own evidence rather than typed, so re-verifying the pin moves the "
        "floor with it instead of leaving the two to disagree. A floor rather than an "
        "exact count for two reasons: new advisories against a frozen pin only ever "
        "arrive, and tools report advisories rather than CVEs, several advisories "
        "mapping to one CVE - so a report of either satisfies this and the run records "
        "which unit it counted in",
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
        "the same claim. The pins are in the clone, so the registry route the record "
        "prescribes answers this without the tree: the project endpoint reports the "
        "latest release, which is the comparison the tiered tools would have made. A "
        "partition reporting no-evidence here has skipped a route the record says "
        "survives a withheld grant, and that is the failure to look for",
    ),
    Expectation(
        "deps/licenses",
        _ALL,
        "exact",
        "Unidecode 1.4.0 is reported under a GPLv2+ licence. A copyleft entry the "
        "check must surface rather than a count",
        ("copyleft",),
        "the same claim, from the registry rather than from an installed METADATA. "
        "Unidecode declares its licence as a classifier rather than as an SPDX "
        "expression, so this doubles as the control for the record's instruction to "
        "read all three metadata channels: a route reading only license_expression "
        "reports the one copyleft dependency in the set as unlicensed, which is a "
        "false clean rather than a miss",
    ),
    Expectation(
        "deps/transitive-licenses",
        _ALL,
        "floor",
        "at least markupsafe appears as a transitive component with a licence, "
        "since it is never declared and arrives through jinja2",
        ("transitive-root",),
        "the same route as deps/licenses, applied to the whole locked graph rather "
        "than the declared set, and conditional on the partition's lockfile pinning "
        "that graph. Where it pins only the direct dependencies there is nothing to "
        "enumerate markupsafe from, and the record names that as not a clean result "
        "for the partition rather than as a pass. The run records which partitions "
        "fell which way; a partition reported clean here without a transitive pin set "
        "is the false clean this axis exists to catch",
    ),
    Expectation(
        "deps/hygiene",
        ("pipenv",),
        "exact",
        "deptry finds no dependency specification at all and raises "
        "DependencySpecificationNotFoundError. A Pipfile is not a format it reads, so "
        "this partition has no hygiene lens the harness can run on any grant: deptry "
        "is the only command the record offers for Python, and the manifest-and-"
        "lockfile read it also offers is a reading procedure rather than a command "
        "this round executes. That is a finding about the family rather than about the "
        "fixture, and is why this partition gets its own entry rather than being "
        "folded into the one the other partitions share",
        (),
        "the same, and for the same reason: the format is unreadable to deptry with "
        "the tree or without it, so this is the one entry here the grant cannot move",
    ),
    Expectation(
        "deps/hygiene",
        _partitions_except("pipenv"),
        "exact",
        "run as `deptry .` with its default excludes, six is reported "
        "declared-and-unused (DEP002) and markupsafe is reported as a transitive "
        f"dependency being imported (DEP003). A further {len(_SRC_FILES_IMPORTING_PACKAGE)} "
        f"DEP003 rows name {PACKAGE}'s own modules, one per file under src/ that "
        "imports the package by name, because deptry treats a src-layout package's "
        "self-imports as third-party. They are expected output rather than a seed, and "
        "the run records them as the tool's behaviour on this layout instead of "
        "configuring them away, since suppressing them would hide a false positive an "
        "audited project would also meet. The scan root is stated because the answer "
        "moves with it - `deptry src` makes the package local and those rows vanish - "
        "and the record prescribes no root, which is a gap in the record",
        ("declared-unused", "undeclared-import"),
        "six is still DEP002, but markupsafe is reported DEP001 (missing) rather than "
        "DEP003, because nothing without the tree tells deptry that markupsafe ships "
        "under jinja2. That is the record's own note - the scanner misreports in both "
        "directions at once - and it is the reason this axis is written down at all: "
        "graded against the granted claim, a correct ungranted run reads as a tool "
        "defect",
    ),
    Expectation(
        "deps/inventory",
        (FULL_PARTITION,),
        "exact",
        "`uv export --format=cyclonedx1.5 --frozen` emits CycloneDX 1.5 listing the "
        f"{len(declared())} declared dependencies plus markupsafe and pyparsing, both "
        "transitive. The record names this command for a uv-locked partition, "
        "cyclonedx-py having no uv subcommand, so the route is the record's rather "
        "than the audit's invention. The harness carries it as the prescribed command "
        "of its cyclonedx-py entry for this partition, and puts nothing in front of "
        "it: the command names its own runner, so fronting it with the fetch that "
        "entry's tool name resolves to would obtain a package it never calls. No "
        "component carries a "
        "licences field, which is a family finding rather than a fixture gap: no route "
        "this record offers populates licences on any partition, so an SBOM is not "
        "where this family's licence evidence comes from and deps/licenses owns it "
        "alone",
        (),
    ),
    Expectation(
        "deps/inventory",
        ("pip",),
        "exact",
        f"`cyclonedx-py requirements` emits exactly the {len(declared())} declared "
        "dependencies and nothing else: a requirements.txt carries no transitive "
        "resolution, so markupsafe is absent, and no component carries a licences "
        "field. Both absences are correct tool behaviour on this input rather than "
        "misses, which is why this partition is written as its own entry - an SBOM "
        "expectation naming markupsafe would grade a working tool against a claim its "
        "input cannot support",
        (),
    ),
    Expectation(
        "deps/inventory",
        ("pipenv",),
        "exact",
        "`cyclonedx-py pipenv` reads Pipfile.lock and emits CycloneDX 1.6 listing the "
        f"{len(declared())} declared dependencies plus markupsafe and pyparsing. No "
        "licences field, as on every other route here",
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
        "deps/inventory",
        ("pylock",),
        "exact",
        "none of this record's prescribed SBOM routes reads PEP 751. `uv export "
        "--frozen` refuses, because this partition carries no uv.lock by construction; "
        "cyclonedx-py has no pylock subcommand; and its requirements subcommand pointed "
        "at pylock.toml does not refuse either - it reads the TOML as requirement lines "
        "and emits a document that fails its own 1.6 schema validation, exiting "
        "non-zero having written nothing usable. A family finding, and the sharpest one "
        "this partition exists to produce: the record's Python fallback names no route "
        "for the lock format PEP 751 standardises, and the nearest tool produces "
        "garbage rather than an error a caller could distinguish from a tool that found "
        "nothing. Scoped to this record's own routes on purpose - the format is "
        "readable, `uv pip install -r pylock.toml` resolves the partition and is how it "
        "is materialized, so the gap is in the inventory tooling rather than in the "
        "ecosystem's support for the format",
        (),
    ),
    Expectation(
        THIN_EXTRA_CHECK,
        _ALL,
        "exact",
        f"the two guard branches of {PACKAGE}.invariant.clamp are among the uncovered "
        "set rather than the whole of it: the seeded suite imports only render and "
        "invariant, so every module no test imports reports at zero as well. Written "
        "as membership because a report listing all of them is correct output, and an "
        "expectation naming only clamp would read that correctness as over-reporting. "
        "On a thin partition this doubles as proof the materialization route works, "
        "since pytest-cov is tiered target-execution and answers nothing unless the "
        "tree resolved and the suite ran",
        ("uncovered-branch",),
        "the reach measurement does not survive the withheld grant, but the check is "
        "not no-evidence: what is excluded from measurement is readable in the clone, "
        "and this fixture configures no [tool.coverage.run] source or omit and no "
        "[tool.coverage.report] exclude_lines. So the expected ungranted answer is "
        "that nothing is excluded, with the reach half unmeasured - and a run "
        "recording no-evidence for the whole check has skipped the half the record "
        "says survives",
    ),
    Expectation(
        "arch/complexity",
        _FULL,
        "exact",
        f"{PACKAGE}.complexity.classify is over the default threshold of every tool "
        "the record names: ruff C901 computes 12 against its default of 10, radon "
        "rates it C at 13, and xenon fails --max-absolute B on it. The two engines "
        "differ by one because ruff does not walk conditional expressions, so the seed "
        "is written with explicit branches throughout and both clear their thresholds "
        "with margin rather than one landing exactly on its default, where C901's `>` "
        "would let it pass in silence",
        ("complexity",),
    ),
    Expectation(
        "arch/complexity-gate",
        _FULL,
        "absence",
        "no complexity threshold is configured anywhere in the fixture, so the expected "
        "finding is the absence of a gate rather than a hit. This is why arch/complexity "
        "is seeded above every tool's default rather than fixed by configuring one: a "
        "threshold added to make that check fire would falsify this one",
        (),
    ),
    Expectation(
        "arch/cycles",
        _FULL,
        "exact",
        f"one cycle, between {PACKAGE}.domain.model and {PACKAGE}.infra.store",
        ("cycle",),
    ),
    Expectation(
        "arch/layering",
        _FULL,
        "exact",
        f"{PACKAGE}.domain.model imports {PACKAGE}.infra.store, which is the "
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
        "exact",
        "the record's Python fallback triggers on modules whose functions only forward "
        f"to another module, and the fixture has exactly two: {PACKAGE}.domain.model.load "
        f"forwards to {PACKAGE}.infra.store.read, and {PACKAGE}.infra.store.load_via_domain "
        f"forwards to {PACKAGE}.domain.model.load. The package is {_SRC_FILE_COUNT} files "
        "under src/, which supplies the long tail of one-symbol modules the same "
        "fallback names. Both are Minor on the record's own band, and neither becomes a "
        "finding without the read the record requires before a count counts - so the "
        "expected observation is the pair, not a verdict on them",
        ("pass-through",),
    ),
    Expectation(
        "arch/over-abstraction",
        _FULL,
        "exact",
        "three triggers from the record's Python fallback, which says one call site is "
        f"the trigger for a single-function module: {PACKAGE}.deadcode.never_referenced "
        f"has zero call sites and {PACKAGE}.invariant.clamp has one. The third is "
        "clamp's low and high parameters, each bound to a single distinct value across "
        "that one call site, which the same fallback calls an unexercised knob. All "
        "Minor, and as with over-decomposition the record requires a read before a "
        "count becomes a finding",
        ("single-caller",),
    ),
    Expectation(
        "arch/martin-metrics",
        _FULL,
        "exact",
        "neither module in the cycle lands in a zone. The record defines I = Ce/(Ca+Ce), "
        "and a mutual cycle forces Ca = Ce = 1 on both sides, so I = 0.5 for each; the "
        "fixture declares no ABC, Protocol or @abstractmethod anywhere, so A = 0 and "
        "D = |A + I - 1| = 0.5. That is the main sequence, not the zone of pain (A and "
        "I both near 0) or of uselessness (both near 1). A cycle is the mechanism that "
        "pulls modules towards the main sequence, so no cycle can ever seed this "
        "metric's subject. Nothing here is planted for it: a fixture gap rather than a "
        "family finding, since the tool is not being asked something it fails to answer",
        (),
    ),
    Expectation(
        "arch/hidden-coupling",
        _FULL,
        "absence",
        "nothing is seeded outside the import graph. Both edges of the cycle are plain "
        "top-level import statements, which is exactly why arch/cycles sees them, and "
        "the fixture's only module-level mutable state is read within its own module. "
        "The record's subject is coupling that does not travel through an import, so a "
        "report here is a false positive and the check's real subject is a fixture gap",
        (),
    ),
    Expectation(
        "arch/dead-code",
        _FULL,
        "floor",
        f"{PACKAGE}.deadcode.never_referenced appears among the unused symbols. A "
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
        f"the eval call in {PACKAGE}.unsafe.run_expression",
        ("dangerous-calls",),
    ),
    Expectation(
        "security/injection",
        _FULL,
        "exact",
        f"the shell=True subprocess in {PACKAGE}.unsafe.run_shell and the "
        f"string-formatted SQL in {PACKAGE}.unsafe.query",
        ("injection",),
    ),
    Expectation(
        "security/crypto",
        _FULL,
        "exact",
        f"the md5 digest in {PACKAGE}.unsafe.digest",
        ("crypto",),
    ),
    Expectation(
        "security/unsafe-io",
        _FULL,
        "exact",
        f"the unchecked tarfile.extractall in {PACKAGE}.unsafe.unpack and the bare "
        f"xml.etree parse in {PACKAGE}.unsafe.parse_document. These are seeded for this "
        "check specifically: its record scopes itself to XXE, archive extraction and "
        "symlink following, none of which eval, shell=True, built SQL or md5 are, so "
        "without them bandit's shell rule would fire and make the check look exercised "
        "while its own subject went untested",
        ("unsafe-io",),
    ),
    Expectation(
        "docs/docstring-coverage",
        _FULL,
        "exact",
        f"{PACKAGE}.unsafe is the one non-empty module under src/ with no module "
        f"docstring, so it carries the seed. It is not alone: {len(_FILES_WITHOUT_MODULE_DOCSTRING)} "
        "of the seeded files have no module docstring, the others being the empty "
        "package __init__ files and those seeded test files that open with code, so a "
        "per-file report names them too and the expectation is that unsafe.py is among "
        "them rather than the only one. Written that way because naming one file would "
        "make correct output read as over-reporting. Function-level coverage is low "
        "across the whole seeded package rather than in that file alone, so the "
        "percentage each tool reports is recorded at the run rather than predicted here",
        ("undocumented",),
    ),
    Expectation(
        "test/determinism",
        _FULL,
        "exact",
        "tests/test_order.py fails under a randomized order and passes in file order. "
        "The shuffle seed that reproduces the failure is measured when the fixture is "
        "first built and recorded in the build smoke record, never guessed: it is a "
        "property of pytest-randomly's ordering rather than of this definition, so "
        "stating a value here would be the guess the round exists to remove",
        ("order-dependence",),
        "the grep axis answers without the tree, and finds nothing: the seeded suite "
        "calls no time.time(), no datetime.now(), no unseeded random. and no network. "
        "Order-dependence itself goes unmeasured, which the record names as exactly "
        "the half a withheld grant costs - so the expected ungranted answer is a clean "
        "grep axis and an unmeasured order axis, not no-evidence for the check",
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
        "the I/O axis answers without the tree and finds nothing: the seeded suite "
        "makes no network, filesystem or database call, and raises no timeout in "
        "configuration. The duration evidence is what the grant buys, so the record "
        "prescribes answering on the I/O axis rather than reporting the check "
        "no-evidence as a whole",
    ),
    Expectation(
        "test/mutation",
        _FULL,
        "floor",
        f"at least one surviving mutant in {PACKAGE}.invariant.clamp, whose two guard "
        "branches no test asserts. A floor because the count moves with the operator set",
        ("mutation-survivor",),
    ),
    Expectation(
        "test/property-based-gap",
        _FULL,
        "exact",
        f"{PACKAGE}.invariant.clamp has an obvious invariant, low <= result <= high, "
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
