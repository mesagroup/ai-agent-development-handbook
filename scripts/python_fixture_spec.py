"""Definition of the seeded Python fixtures (#45) and TypeScript fixtures (#181).

For each language, one dependency set, one seeded source tree, the manifest
renderings of its partitions (five Python, two TypeScript) and one expectations
table, all from this module. The fixture tree and the expectations
are produced from the same definition on purpose: expectations kept in a second
file are free to drift, and a seed present in the tree but missing from the
expectations reads exactly like a tool that correctly found nothing.

Every pin below carries an `evidence` string, and each was checked against OSV
and PyPI on VERIFIED_ON rather than recalled. Re-checking one means querying
those two sources again and updating both the pin and its evidence, because a
pin whose advisories nobody re-read is the unverified claim this whole round
exists to remove.

The TypeScript half follows the Python one below, under its own verification
date, `TS_VERIFIED_ON`, because its pins were checked on a different day against
OSV and the npm registry. `PARTITIONS` and `EXPECTATIONS` stay the Python ones;
the TypeScript tables carry a `TS_` prefix, and `lang_of` says which a partition
name belongs to.

Pure. Nothing here touches the filesystem, the network or a subprocess.
"""

import json
import re
from dataclasses import dataclass

# The date every `Dependency.evidence` string below was measured. It is rendered
# into the published expectations record, so a reader can tell how old the
# numbers are without opening the git history.
VERIFIED_ON = "2026-08-13"

PARTITIONS = ("uv", "pip", "poetry", "pipenv", "pylock")

# The TypeScript partitions (#181), one per package manager a named TypeScript
# target uses. Named here, beside the Python tuple, because `Expectation`
# validates its scope against both and a partition name has to mean one
# language. `PARTITIONS` stays the Python tuple on purpose: the Python harness,
# renderer and tests all read it as "the Python partitions", and widening it
# would hand every one of them two partitions it has no manifest for.
TS_PARTITIONS = ("npm", "pnpm")


def lang_of(partition: str) -> str:
    """The language a partition belongs to, or a failure naming the partition.

    The two tuples are disjoint by construction, so a name is in at most one of
    them; a name in neither is a typo, and answering it with a default language
    would scope an expectation to a partition nothing builds.
    """
    if partition in PARTITIONS:
        return "python"
    if partition in TS_PARTITIONS:
        return "typescript"
    raise ValueError(
        f"unknown partition {partition!r}; expected one of {PARTITIONS + TS_PARTITIONS}"
    )


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


# The package-graph `deps` records are the ones every partition runs, because a
# dependency lens reads the partition's own manifest and lock format and so
# answers a different question in each of the five; the domain's model-surface
# records prescribe no command and have no fixture row. Listed here rather than derived from
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
    already holds in both states. Which schema a record declares decides how
    both halves of that are read, and neither half is schema-neutral. On a
    legacy record the tier is per tool, so the question is whether every Python
    tool the record offers carries one. On a routes record the tier is per
    route, and the question is whether every answering-kind, non-`forbidden`
    route *naming a tool* carries one - a tool with one tiered route and one
    untiered route does not put its language in that half, even though the
    projected `tooling`/`needs` pair says it does. The two schemas also say
    "something still answers" in different places - `ungranted_note` on one, an
    untiered answering route on the other, which is commonly a route carrying
    no tool at all and so invisible in the projected pair - and the test that
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

    `owed` is the third axis: what a tool's result on this check still needs
    before it is the check's answer, set on exactly the entries whose check has
    a Python route naming a tool that carries `alone_insufficient`, which a test
    derives from the records the way it derives `ungranted`. The harness writes
    the route's own field onto each results row and the grader prints it beside
    the observation; this is the same fact said about the fixture, so a reader
    of the grade sees that a scanner's hit on the seed is a candidate and what
    confirms it. It is prose because the confirmation is a reading, not a
    command this round runs, and it never changes a status: the row's status is
    the engine's, and what is owed is carried beside it.
    """

    check: str
    partitions: tuple[str, ...]
    form: str
    claim: str
    seeds: tuple[str, ...]
    ungranted: str = ""
    owed: str = ""

    def __post_init__(self) -> None:
        if self.form not in FORMS:
            raise ValueError(
                f"unknown form {self.form!r} for {self.check}; expected one of {FORMS}"
            )
        known = PARTITIONS + TS_PARTITIONS
        unknown = sorted(set(self.partitions) - set(known))
        if unknown:
            raise ValueError(
                f"not partitions: {unknown} for {self.check}; expected names from {known}"
            )
        # One entry answers for one language. A scope mixing a Python and a
        # TypeScript partition would put one claim in front of two different
        # tools, and the renderer of either record would then publish half of it.
        languages = {lang_of(p) for p in self.partitions}
        if len(languages) > 1:
            raise ValueError(
                f"{self.check} is scoped across languages {sorted(languages)}; "
                "write one entry per language"
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
        owed=(
            "the unpinned and yanked halves: an outdated list answers only whether a "
            "release is behind, and whether a direct dependency is unpinned or a pinned "
            "release yanked is read by the record's lockfile and registry route, which "
            "is also what answers a run without the grant"
        ),
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
        "and the record's argv stops short of the root, which its note gives as `.` "
        "with the target as the working directory",
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
        "this partition exists to produce: this record's own Python routes name none "
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
        "the reach measurement does not survive the withheld grant while the "
        "exclusion axis does: what is excluded from measurement is readable in the "
        "clone, and this fixture configures no [tool.coverage.run] source or omit and "
        "no [tool.coverage.report] exclude_lines. So the expected ungranted answer is "
        "a half-answered check - no-evidence (not-permitted) in status and in the "
        "coverage count, its evidence naming the exclusion axis as answered clean and "
        "the reach axis as unmeasured. A run reporting the check ok on the clean "
        "exclusion reading alone has read one axis as the check, and one recording "
        "no-evidence with no axis named has skipped the half the record says "
        "survives",
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
        "the record's Python route triggers on modules whose functions only forward "
        f"to another module, and the fixture has exactly two: {PACKAGE}.domain.model.load "
        f"forwards to {PACKAGE}.infra.store.read, and {PACKAGE}.infra.store.load_via_domain "
        f"forwards to {PACKAGE}.domain.model.load. The package is {_SRC_FILE_COUNT} files "
        "under src/, which supplies the long tail of one-symbol modules the same "
        "route names. Both are Minor on the record's own band, and neither becomes a "
        "finding without the read the record requires before a count counts - so the "
        "expected observation is the pair, not a verdict on them",
        ("pass-through",),
        owed=(
            "a read confirming each forwarding module is genuinely trivial and that "
            "merging it raises cohesion; a split that maps onto independently changing "
            "responsibilities is correct design rather than a finding"
        ),
    ),
    Expectation(
        "arch/over-abstraction",
        _FULL,
        "exact",
        "three triggers from the record's Python routes, which say one call site is "
        f"the trigger for a single-function module: {PACKAGE}.deadcode.never_referenced "
        f"has zero call sites and {PACKAGE}.invariant.clamp has one. The third is "
        "clamp's low and high parameters, each bound to a single distinct value across "
        "that one call site, which the same routes call an unexercised knob. All "
        "Minor, and as with over-decomposition the record requires a read before a "
        "count becomes a finding",
        ("single-caller",),
        owed=(
            "a read confirming, per trigger, that no second consumer or second value is "
            "imminent in-tree and that collapsing the construct removes indirection "
            "without losing a genuine seam; a documented extension point is a "
            "suppression rather than a finding"
        ),
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
        owed=(
            "a source-to-sink trace in the real code for each reported call, confirming "
            "an attacker-reachable path into the sink; a sink fed only a hardcoded "
            "constant is not an injection, so a scanner hit on the seed is a candidate "
            "until that read"
        ),
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
        "the half a withheld grant costs - so the expected ungranted answer is a "
        "half-answered check, no-evidence (not-permitted) in status and in the "
        "coverage count, its evidence naming the grep axis as answered clean and the "
        "order axis as unmeasured. A run reporting the check ok on the clean grep "
        "reading alone has read one axis as the check",
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
        "configuration. The duration evidence is what the grant buys, so the expected "
        "ungranted answer is a half-answered check, no-evidence (not-permitted) in "
        "status and in the coverage count, its evidence naming the I/O axis as "
        "answered clean and the timing axis as unmeasured. A run reporting the check "
        "ok on the clean I/O reading alone has read one axis as the check",
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
    """Every expectation that applies to one partition, of either language."""
    table = EXPECTATIONS if lang_of(partition) == "python" else TS_EXPECTATIONS
    return tuple(e for e in table if partition in e.partitions)


# ---------------------------------------------------------------------------
# The TypeScript half (#181).
#
# The same single-source rule as the Python half above: one dependency set, one
# seeded source tree, two manifest renderings and one expectations table, all
# from this module, so a seed cannot drift from the expectation that looks for
# it. Every pin below was checked on TS_VERIFIED_ON against OSV
# (`api.osv.dev/v1/query`, ecosystem npm) and the npm registry (`npm view
# <pkg>@<ver> license dependencies`, `npm view <pkg> version` for latest), and
# its `evidence` string says what came back.
# ---------------------------------------------------------------------------

TS_VERIFIED_ON = "2026-09-25"

# The package manager each partition declares in its root `packageManager`
# field, which is what corepack provisions from. A manager the audit
# environment happens to have is not the manager the target declares, so the
# pin is part of the fixture rather than of the host.
NPM_PIN = "npm@11.19.0"
PNPM_PIN = "pnpm@9.15.9"
TS_MANAGER_PINS = {"npm": NPM_PIN, "pnpm": PNPM_PIN}

# The workspace members on pnpm. The npm partition is one package and ignores
# `TsDependency.member`; the pnpm partition is a workspace because the pnpm
# target is one and its corrections in #29 came from workspace behaviour.
TS_ROOT = "."
TS_CORE = "packages/core"
TS_LEAF = "apps/api"
TS_MEMBERS = (TS_ROOT, TS_CORE, TS_LEAF)

TS_PACKAGE_VERSION = "0.1.0"
TS_NPM_PACKAGE = "fixture-app"
TS_WORKSPACE_ROOT_PACKAGE = "fixture-workspace"
TS_CORE_PACKAGE = "@fixture/core"
TS_LEAF_PACKAGE = "@fixture/api"


@dataclass(frozen=True)
class TsDependency:
    """One entry in the TypeScript dependency set.

    `member` is the workspace package that declares it on pnpm: `TS_ROOT`, or
    one of the two members. It decides which manifest a pnpm route has to read
    to see the pin, which is the whole point of the leaf-only stale seed.

    `latest` is the registry's latest release on TS_VERIFIED_ON. Recorded rather
    than looked up, so the freshness expectation's outdated set is computed from
    the module (`pin != latest`) instead of typed, and a re-verification that
    moves one moves the claim with it.
    """

    name: str
    pin: str
    latest: str
    dev: bool
    member: str
    seeds: tuple[str, ...]
    evidence: str

    def __post_init__(self) -> None:
        if self.member not in TS_MEMBERS:
            raise ValueError(
                f"unknown member {self.member!r} for {self.name}; expected one of {TS_MEMBERS}"
            )


TS_DEPENDENCIES = (
    TsDependency(
        "lodash",
        "4.17.20",
        "4.18.1",
        False,
        TS_LEAF,
        ("vulnerable",),
        "OSV: 5 advisories, GHSA-29mw-wpgm-hmr9, GHSA-35jh-r3h4-6jhm, "
        "GHSA-f23m-r3pf-42rh, GHSA-r5fr-rjxr-66jc and GHSA-xxjr-mmjv-4gpg, two pairs of "
        "which alias each other, over CVE-2020-28500, CVE-2021-23337, CVE-2026-4800, "
        "CVE-2025-13465 and CVE-2026-2950. npm view: MIT, no dependencies. Latest is "
        "4.18.1, so it is outdated too",
    ),
    TsDependency(
        "commander",
        "2.20.3",
        "15.0.0",
        False,
        TS_LEAF,
        ("stale", "leaf-only"),
        "OSV: no advisories. npm view: MIT, no dependencies. Latest is 15.0.0, "
        "thirteen majors ahead. Declared in the pnpm leaf only, so a root-only "
        "freshness read cannot reach it",
    ),
    TsDependency(
        "is-odd",
        "3.0.1",
        "3.0.1",
        False,
        TS_ROOT,
        ("transitive-root",),
        "OSV: no advisories. npm view: MIT, the latest release, which makes it the "
        "freshness control. Depends on is-number ^6.0.0, which resolves to is-number "
        "6.0.0 (MIT, no OSV advisories, not declared anywhere in the fixture): the "
        "transitive component the licence and inventory checks have to reach",
    ),
    TsDependency(
        "tinymce",
        "7.9.3",
        "8.9.2",
        False,
        TS_CORE,
        ("copyleft",),
        "npm view: GPL-2.0-or-later, no dependencies. OSV: no advisories. Pinned at "
        "7.9.3 rather than the planned 7.9.1, which carries three XSS advisories "
        "(GHSA-q742-qvgc-gc2f, GHSA-v98h-vmpc-fpqv, GHSA-vg35-5wq7-3x7w) fixed in 7.9.3 "
        "and would have made lodash not the only vulnerable seed. The 8.x line is "
        "unusable for the seed: 8.9.2 declares `SEE LICENSE IN license.md`, which is "
        "not an SPDX id. Latest is 8.9.2, so it is outdated too",
    ),
    TsDependency(
        "vitest",
        "5.0.2",
        "5.0.2",
        True,
        TS_ROOT,
        (),
        "npm view: MIT, the latest release. Declares a non-optional peer dependency "
        "on vite and engines node ^22.12.0 || ^24.0.0 || >=26.0.0. Its option "
        "documentation gives slowTestThreshold a default of 300 and testTimeout a "
        "default of 5000, and says `sequence.shuffle` runs files and tests in random "
        "order",
    ),
    TsDependency(
        "@vitest/coverage-v8",
        "5.0.2",
        "5.0.2",
        True,
        TS_ROOT,
        (),
        "npm view: MIT, the latest release, peer dependency vitest 5.0.2 exactly",
    ),
    TsDependency(
        "typescript",
        "5.9.3",
        "7.0.2",
        True,
        TS_ROOT,
        (),
        "npm view: Apache-2.0. Pinned at 5.9.3, the newest 5.x release, rather than the "
        "latest 7.0.2: 7.x ships as per-platform native binaries, madge 8.0.0 declares "
        "a typescript peer of ^5.4.4 and the dependency-cruiser routes record a "
        "declared range below 7.0.0, so a 7.x in the tree would be an unplanted "
        "confound on every resolved-tree arch route. Outdated by construction",
    ),
)


def _ts_by_name(name: str) -> TsDependency:
    """The one TypeScript dependency with this name, or a failure naming the set."""
    for dependency in TS_DEPENDENCIES:
        if dependency.name == name:
            return dependency
    raise ValueError(
        f"no TypeScript dependency named {name!r}; have {[d.name for d in TS_DEPENDENCIES]}"
    )


# The cycle uses named imports resolved at call time in both directions. ES
# module bindings are live, so neither module reads the other's export during
# evaluation and the cycle is real for the graph tools without breaking a test
# that imports either module. `load` and `loadViaDomain` only forward, which is
# the pass-through pair arch/over-decomposition reads, as in the Python half.
_TS_MODEL = """// Domain model. Imports infra, which is the layering violation.
import { read } from "../infra/store";

export function load(key: string): number | undefined {
  return read(key);
}
"""

_TS_STORE = """// Infrastructure store. Imports the domain model, closing the cycle.
import { load } from "../domain/model";

const data: Record<string, number> = { a: 1 };

export function read(key: string): number | undefined {
  return data[key];
}

export function loadViaDomain(key: string): number | undefined {
  return load(key);
}
"""

_TS_CLAMP = """// A function with two guard branches no test reaches.
export function clamp(value: number, low: number, high: number): number {
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high;
  }
  return value;
}
"""

_TS_TEST_CLAMP = """import { expect, test } from "vitest";
import { clamp } from "../src/clamp";

test("clamp passes a value inside the range through", () => {
  expect(clamp(5, 0, 10)).toBe(5);
});
"""

# Both tests in ONE file, because a shuffle that only reorders files cannot
# reverse them. vitest's `--sequence.shuffle` as a boolean shuffles tests within
# a file as well; the seed that reverses the pair is measured at build time and
# recorded in the build smoke record, never guessed.
_TS_TEST_ORDER = """// An order-dependent pair, green in file order.
import { expect, test } from "vitest";

const seen: number[] = [];

test("appends", () => {
  seen.push(1);
  expect(seen).toEqual([1]);
});

test("reads", () => {
  expect(seen).toEqual([1]);
});
"""

# The sleep and the two vitest defaults it sits between are one fact, so all
# three are named and interpolated. The sleep reuses the Python half's
# constant: the slow seed is the same seed in both languages.
TS_SLOW_TEST_MS = SLOW_TEST_SECONDS * 1000
VITEST_SLOW_TEST_THRESHOLD_MS = 300
VITEST_TEST_TIMEOUT_MS = 5000

_TS_TEST_SLOW = f"""import {{ expect, test }} from "vitest";

test("slow but passing", async () => {{
  await new Promise((resolve) => setTimeout(resolve, {TS_SLOW_TEST_MS}));
  expect(true).toBe(true);
}});
"""

# No `extends`, no `paths` and no `references`: madge's `--ts-config` route
# applies only where the partition's tsconfig does not extend a base living in
# `node_modules`, and this one extends nothing, so the route applies by
# construction rather than by luck of the host.
_TS_CONFIG = """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true
  },
  "include": ["src", "test"]
}
"""

# Paths relative to the seeded package's own root: the repository root on npm,
# `TS_CORE` on pnpm. `ts_source_tree` applies the prefix.
TS_SOURCE_FILES = (
    SourceFile("tsconfig.json", _TS_CONFIG, ()),
    SourceFile("src/domain/model.ts", _TS_MODEL, ("cycle", "pass-through")),
    SourceFile("src/infra/store.ts", _TS_STORE, ("cycle", "pass-through")),
    SourceFile("src/clamp.ts", _TS_CLAMP, ("uncovered-branch",)),
    SourceFile("test/clamp.test.ts", _TS_TEST_CLAMP, ("uncovered-branch",)),
    SourceFile("test/order.test.ts", _TS_TEST_ORDER, ("order-dependence",)),
    SourceFile("test/slow.test.ts", _TS_TEST_SLOW, ("slow-test",)),
)

# The construct each planted seed is, so it cannot leave with its name intact.
# Every TypeScript seed is a construct: none is an absence, which is why there
# is no TypeScript counterpart of ABSENCE_SEEDS.
TS_SEED_MARKERS = {
    "cycle": ('from "../infra/store"', 'from "../domain/model"'),
    "pass-through": ("return read(key)", "return load(key)"),
    # The guards, not the function name: deleting a guard leaves `clamp` intact.
    "uncovered-branch": ("if (value < low)", "if (value > high)"),
    "order-dependence": ("seen.push(",),
    "slow-test": (f"setTimeout(resolve, {TS_SLOW_TEST_MS})",),
}


def _ts_source_prefix(partition: str) -> str:
    if lang_of(partition) != "typescript":
        raise ValueError(f"{partition!r} is not a TypeScript partition")
    return "" if partition == "npm" else f"{TS_CORE}/"


def ts_source_tree(partition: str) -> dict[str, str]:
    """Map every seeded path, as it lands in this partition's tree, to its body."""
    prefix = _ts_source_prefix(partition)
    return {f"{prefix}{f.path}": f.body for f in TS_SOURCE_FILES}


def _json(document: dict) -> str:
    return json.dumps(document, indent=2) + "\n"


def _pins(dependencies, *, dev: bool) -> dict[str, str]:
    """Exact pins, never ranges: a range would let the resolver move a seed."""
    return {d.name: d.pin for d in dependencies if d.dev == dev}


def _package_json(
    name: str,
    dependencies: tuple[TsDependency, ...],
    *,
    package_manager: str = "",
    links: dict[str, str] | None = None,
) -> str:
    """One package.json. `links` are workspace-protocol runtime dependencies."""
    document: dict = {
        "name": name,
        "version": TS_PACKAGE_VERSION,
        "private": True,
        "type": "module",
    }
    if package_manager:
        document["packageManager"] = package_manager
    runtime = _pins(dependencies, dev=False) | (links or {})
    if runtime:
        document["dependencies"] = runtime
    development = _pins(dependencies, dev=True)
    if development:
        document["devDependencies"] = development
    return _json(document)


def ts_render_manifests(partition: str) -> dict[str, str]:
    """Return {relative path: content} for one TypeScript partition's manifests.

    Lockfiles are absent by design, as on the Python side: each manager
    generates its own, which is the difference the two partitions exist to
    exercise. The `packageManager` pin goes on the root manifest only, which is
    where corepack reads it.
    """
    if lang_of(partition) != "typescript":
        raise ValueError(f"{partition!r} is not a TypeScript partition")
    pin = TS_MANAGER_PINS[partition]
    if partition == "npm":
        return {
            "package.json": _package_json(
                TS_NPM_PACKAGE, TS_DEPENDENCIES, package_manager=pin
            )
        }
    if partition == "pnpm":

        def members(member: str):
            return tuple(d for d in TS_DEPENDENCIES if d.member == member)

        return {
            "package.json": _package_json(
                TS_WORKSPACE_ROOT_PACKAGE, members(TS_ROOT), package_manager=pin
            ),
            "pnpm-workspace.yaml": "packages:\n  - packages/*\n  - apps/*\n",
            f"{TS_CORE}/package.json": _package_json(TS_CORE_PACKAGE, members(TS_CORE)),
            f"{TS_LEAF}/package.json": _package_json(
                TS_LEAF_PACKAGE,
                members(TS_LEAF),
                links={TS_CORE_PACKAGE: "workspace:*"},
            ),
        }
    raise ValueError(
        f"partition {partition!r} is named in TS_PARTITIONS but has no manifest rendering"
    )


_TS_ALL = TS_PARTITIONS

_LODASH_CVES = tuple(
    sorted(set(re.findall(r"CVE-\d{4}-\d+", _ts_by_name("lodash").evidence)))
)

# The outdated set and the control, computed from the pins rather than typed.
_TS_OUTDATED = tuple(d for d in TS_DEPENDENCIES if d.pin != d.latest)
_TS_CURRENT = tuple(d for d in TS_DEPENDENCIES if d.pin == d.latest)
_TS_ROOT_OUTDATED = tuple(d for d in _TS_OUTDATED if d.member == TS_ROOT)
# The freshness control is a current pin on a package that has gone quiet, so a
# correct route cannot report it outdated between verification and the run. The
# other current pins are dev tooling on fast release lines and are not controls.
_TS_CONTROLS = tuple(d for d in _TS_CURRENT if d.name == "is-odd")
_TS_CURRENT_NOT_CONTROL = tuple(d for d in _TS_CURRENT if d not in _TS_CONTROLS)


def _names(dependencies) -> str:
    return ", ".join(f"{d.name} {d.pin}" for d in dependencies)


def _behind(dependencies) -> str:
    return ", ".join(f"{d.name} {d.pin} (latest {d.latest})" for d in dependencies)


_TS_SRC_NOTE = (
    f"Paths are relative to the seeded package, which is the tree root on npm and "
    f"{TS_CORE}/ on pnpm"
)

_TS_DEPCRUISE_OWED = (
    "nothing a read of the result adds: the record's field on `dependency-cruiser` "
    "states an invocation requirement, that the spelling is a prefix and answers "
    "only once given `--config` with an audit-owned config (the record prefers one "
    "setting `options.tsConfig`) or `--no-config`, and a run with neither exits 1 "
    "with `Can't open a config file`, which is no-evidence (tool-failed) rather than "
    "an empty graph"
)

TS_EXPECTATIONS = (
    Expectation(
        "deps/vulnerabilities",
        _TS_ALL,
        "floor",
        f"at least {len(_LODASH_CVES)} distinct CVEs against lodash "
        f"{_ts_by_name('lodash').pin}: {', '.join(_LODASH_CVES)}. The record's routes are "
        "`npm audit` on npm and `pnpm audit` on pnpm, both untiered and both reading the "
        f"lockfile, and on pnpm lodash is declared in {TS_LEAF} rather than at the root, "
        "so an audit that reads only the root importer misses it. A floor because "
        "advisories against a frozen pin only accumulate and tools count advisories "
        "rather than CVEs; the run records which unit it counted in. The other seeded "
        "runtime dependencies, is-number included, had no OSV advisory on the verified "
        "date, so an advisory against one of them is a false positive; the "
        "devDependency tree was not queried package by package, so advisories there are "
        "recorded rather than graded",
        ("vulnerable",),
    ),
    Expectation(
        "deps/freshness",
        ("npm",),
        "exact",
        f"`npm outdated` in the installed tree reports exactly {_behind(_TS_OUTDATED)}. "
        f"{_names(_TS_CONTROLS)} has had no release since its pin and is the control: "
        "a route reporting it outdated is producing a false positive. "
        f"{_names(_TS_CURRENT_NOT_CONTROL)} were the latest releases on the verified "
        "date, and a line that ships patches as often as vitest's can move before the "
        "run, so they are re-checked against the registry then rather than graded as "
        "controls. Named rather than counted, because the count moves with the "
        "dependency set while which entry is the control does not",
        ("stale",),
        "the same claim, from the record's registry-comparison route: every pin is "
        "exact and in package.json, so comparing it with the registry's latest release "
        "needs no tree. That route is a procedure rather than a command, so the "
        "harness's ungranted run of the tiered `npm outdated` records no-evidence "
        "(not-permitted) and the claim is what the procedure answers",
        owed=(
            "the unpinned and deprecated-release halves: an outdated list answers only "
            "whether a release is behind. The fixture pins every declaration exactly, "
            "so the unpinned half should read clean, and whether a pinned release is "
            "deprecated is the registry read the record's procedure route carries"
        ),
    ),
    Expectation(
        "deps/freshness",
        ("pnpm",),
        "exact",
        f"across the workspace, {_behind(_TS_OUTDATED)} are outdated. "
        f"{_names(_TS_CONTROLS)} is the control, and {_names(_TS_CURRENT_NOT_CONTROL)} "
        "were current on the verified date and are re-checked before the run, as on "
        "npm. The record's argv is `pnpm outdated -r`, the workspace form its note "
        "names, which reaches both members. Bare `pnpm outdated` reads the root "
        f"manifest only: run bare from the root it can report {_names(_TS_ROOT_OUTDATED)} "
        f"and nothing declared in {TS_CORE} or {TS_LEAF}, so commander, the stale pin "
        f"declared only in {TS_LEAF}, is missing from a run that looks complete. That "
        "is the half-truth #44 names, and a run reporting it is graded as less than "
        "the truth rather than as a clean run",
        ("stale", "leaf-only"),
        "the same claim, from the record's registry-comparison route over all three "
        "manifests. The harness's ungranted run of the tiered `pnpm outdated` records "
        "no-evidence (not-permitted), and the claim is what the procedure answers",
        owed=(
            "the unpinned and deprecated-release halves, as on npm: the fixture pins "
            "every declaration exactly in all three manifests, and the "
            "`workspace:*` link to the core package is a workspace protocol rather than "
            "an unpinned registry dependency"
        ),
    ),
    Expectation(
        "deps/licenses",
        ("npm",),
        "exact",
        f"`npm sbom --package-lock-only --sbom-format cyclonedx` reports tinymce "
        f"{_ts_by_name('tinymce').pin} under GPL-2.0-or-later, read off the lockfile's "
        "per-package `license` with no tree and no network. The one copyleft entry the "
        "check must surface, rather than a count",
        ("copyleft",),
    ),
    Expectation(
        "deps/licenses",
        ("pnpm",),
        "exact",
        f"`pnpm licenses list` in the installed workspace reports tinymce "
        f"{_ts_by_name('tinymce').pin} under GPL-2.0-or-later, declared in {TS_CORE}",
        ("copyleft",),
        "no command route answers. `pnpm licenses list` needs the tree, and `npm sbom`, "
        "the record's untiered command, reads package-lock.json, which this partition "
        "does not carry; what remains is the `@cyclonedx/cdxgen` procedure, which this "
        "round does not execute. So the harness records no-evidence (not-permitted), "
        "and a clean licence list from this partition without the grant is a false "
        "clean",
    ),
    Expectation(
        "deps/transitive-licenses",
        ("npm",),
        "floor",
        "at least is-number 6.0.0 appears as a component with MIT, since it is never "
        "declared and arrives through is-odd; `npm sbom --package-lock-only` reads it "
        "from the lockfile's pinned transitive graph",
        ("transitive-root",),
    ),
    Expectation(
        "deps/transitive-licenses",
        ("pnpm",),
        "floor",
        "at least is-number 6.0.0 appears with MIT in `pnpm licenses list`, which "
        "reports across the whole workspace, arriving through is-odd at the root",
        ("transitive-root",),
        "the same as deps/licenses on this partition: `pnpm licenses list` needs the "
        "tree and `npm sbom` has no package-lock.json to read, so the harness records "
        "no-evidence (not-permitted) and only the cdxgen procedure would answer",
    ),
    Expectation(
        "deps/inventory",
        ("npm",),
        "floor",
        "`npm sbom --package-lock-only --sbom-format cyclonedx` emits a CycloneDX "
        f"document whose components include {_names(TS_DEPENDENCIES)} at their pins, "
        "plus is-number 6.0.0 through is-odd. A floor rather than an exact count, "
        "because the devDependency tree vitest resolves is in the lockfile too and its "
        "size moves with the resolution",
        (),
    ),
    Expectation(
        "deps/inventory",
        ("pnpm",),
        "exact",
        "none of this record's TypeScript command routes reads pnpm-lock.yaml: "
        "`npm sbom`, the only one, is built on package-lock.json, which this partition "
        "does not carry by construction. So no SBOM comes from a command route here, "
        "and the record's remaining route for the partition is the `@cyclonedx/cdxgen` "
        "procedure, which this round does not execute. The harness runs `npm sbom` on "
        "the npm partition only, since it is npm's own subcommand and corepack refuses "
        "npm inside a pnpm-pinned tree, so this partition records no command for the "
        "check. That is the family finding: no command route answers inventory on pnpm",
        (),
    ),
    Expectation(
        "arch/cycles",
        _TS_ALL,
        "exact",
        "one cycle, between src/domain/model.ts and src/infra/store.ts, from "
        "`madge --circular --extensions ts,tsx --ts-config` given the seeded package's "
        "own tsconfig.json. "
        "That tsconfig extends nothing, so the route's applies_when holds by "
        "construction, and madge needs no grant, so the claim holds in both states. "
        f"{_TS_SRC_NOTE}",
        ("cycle",),
        owed=_TS_DEPCRUISE_OWED,
    ),
    Expectation(
        "arch/coupling",
        _TS_ALL,
        "floor",
        "the two modules in the cycle are each other's dependents, so neither is a "
        "leaf, from the dependency map the tiered `dependency-cruiser` route builds",
        ("cycle",),
        "the tiered command route does not run, so the harness records no-evidence "
        "(not-permitted); the same claim is what the record's untiered madge procedure "
        "answers from a read-only clone, which this round does not execute",
        owed=_TS_DEPCRUISE_OWED,
    ),
    Expectation(
        "arch/over-decomposition",
        _TS_ALL,
        "exact",
        "two forwarding functions, one per module in the cycle: load in "
        "src/domain/model.ts forwards to read in src/infra/store.ts, and loadViaDomain "
        "in src/infra/store.ts forwards to load. Minor on the record's band, and "
        "neither becomes a finding without the read the record requires, so the "
        f"expected observation is the pair, not a verdict on it. {_TS_SRC_NOTE}",
        ("pass-through",),
        "the tiered `dependency-cruiser` route does not run, so the harness records "
        "no-evidence (not-permitted); the record's untiered madge procedure answers the "
        "same pair from a read-only clone, which this round does not execute",
        owed=(
            "a read confirming each forwarding module is genuinely trivial and that "
            "merging it raises cohesion, as the record requires once the graph is "
            "complete; and the `dependency-cruiser` invocation requirement, an "
            "audit-owned `--config` or `--no-config`, without which the prefix exits 1"
        ),
    ),
    Expectation(
        "test/coverage-reach",
        _TS_ALL,
        "exact",
        "`vitest run --coverage` with @vitest/coverage-v8 installed reports "
        "src/clamp.ts with its two guard branches uncovered. The fixture sets no "
        "coverage.include, and vitest's documented default includes only files covered "
        "by tests, so model.ts and store.ts, which no test imports, are absent from the "
        "report rather than at zero: an absence the default produces, not a miss. The "
        "suite is green in file order, so the report is written without "
        f"`--coverage.reportOnFailure`. {_TS_SRC_NOTE}",
        ("uncovered-branch",),
        "the measurement does not survive the withheld grant while the configuration "
        "axis does: the fixture carries no vitest config at all, so no coverage "
        "include, exclude or threshold is readable in the clone and the axis answers "
        "clean. The expected ungranted answer is a half-answered check, no-evidence "
        "(not-permitted) in status and in the coverage count, its evidence naming the "
        "configuration axis as answered clean and the measurement axis as unmeasured",
    ),
    Expectation(
        "test/determinism",
        _TS_ALL,
        "exact",
        "test/order.test.ts fails under `vitest run --sequence.shuffle "
        "--sequence.seed=<n>` for a seed that reverses its pair, and passes in file "
        "order. Both tests are in one file, and `--sequence.shuffle` as a boolean "
        "shuffles tests within a file as well as the files, which is what reaches the "
        "pair. The seed is measured when the fixture is first built and recorded in "
        "the build smoke record, never guessed",
        ("order-dependence",),
        "the inputs axis answers without the tree, and finds nothing: the seeded suite "
        "reads no clock, calls no Math.random and touches no network. Order-dependence "
        "goes unmeasured, so the expected ungranted answer is a half-answered check, "
        "no-evidence (not-permitted) in status and in the coverage count, its evidence "
        "naming the inputs axis as answered clean and the order axis as unmeasured",
    ),
    Expectation(
        "test/isolation",
        _TS_ALL,
        "exact",
        f"the test in test/slow.test.ts sleeps {TS_SLOW_TEST_MS}ms: over vitest's "
        f"default slowTestThreshold of {VITEST_SLOW_TEST_THRESHOLD_MS}ms, so "
        "`vitest run` reports its duration and marks it slow, and under the default "
        f"testTimeout of {VITEST_TEST_TIMEOUT_MS}ms, so it passes. All three numbers are "
        "interpolated from the module constants the seeded file is written from",
        ("slow-test",),
        "the I/O axis answers without the tree and finds nothing: the seeded suite "
        "makes no network, filesystem or database call and configures no timeout. The "
        "duration is what the grant buys, so the expected ungranted answer is a "
        "half-answered check, no-evidence (not-permitted) in status and in the "
        "coverage count, its evidence naming the I/O axis as answered clean and the "
        "timing axis as unmeasured",
    ),
)

# Every check with a `lang: typescript` route that gets no expectation, and why.
# Held by a test to partition the family's TypeScript-route checks together
# with TS_EXPECTATIONS, so a new TypeScript route has to be classified here or
# expected rather than defaulting out of the round in silence.
TS_DEFERRED_CHECKS = {
    "arch/complexity": "no TypeScript command route: its routes are ESLint procedures (the core complexity rule and eslint-plugin-sonarjs), which prescribe a configuration to write rather than a command to run",
    "arch/complexity-gate": "no TypeScript command route: its ESLint routes are `kind: subject`, the configuration the check inspects rather than a way of answering it",
    "arch/dead-code": "no TypeScript command route: knip and ts-prune are procedures",
    "arch/hidden-coupling": "no TypeScript command route: its ESLint, knip and tool-less routes are procedures",
    "arch/import-rule-declaration": "no TypeScript command route: its one route is a tool-less reading procedure",
    "arch/layering": "its one TypeScript command route, `dependency-cruiser`, applies only where the project carries its own `.dependency-cruiser` config, and planting one would have the fixture declare the boundary the check tests; the fallback it names is a reading of tsconfig paths and references, which this fixture does not declare",
    "arch/over-abstraction": "no TypeScript command route: knip is a procedure and ts-morph a library",
    "deps/hygiene": "no TypeScript command route: depcheck and knip are procedures",
    "security/crypto": "no TypeScript command route: its ESLint and tool-less routes are procedures",
    "security/dangerous-calls": "no TypeScript command route: its ESLint and tool-less routes are procedures",
    "security/injection": "no TypeScript command route: its ESLint and tool-less routes are procedures",
    "security/unsafe-io": "no TypeScript command route: its ESLint and tool-less routes are procedures",
    "test/coverage-floor-declaration": "no TypeScript command route: its one route is a tool-less reading procedure",
    "test/mutation": "its one TypeScript command route is `disposition: alternative` to the record's procedure route, and its argv carries a `<runner>` placeholder the record leaves the inventory to fill; nothing is planted for it beyond the untested clamp guards, and the plan for this round seeds no mutation survivor",
    "test/property-based-gap": "no TypeScript command route: fast-check is a library",
}
