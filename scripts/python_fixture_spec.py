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
