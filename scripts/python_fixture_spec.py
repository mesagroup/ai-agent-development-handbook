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
