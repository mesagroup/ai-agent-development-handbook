"""Definition of the seeded Python fixtures (#45).

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
    """

    name: str
    pin: str
    imported: bool
    seeds: tuple[str, ...]
    evidence: str


DEPENDENCIES = (
    Dependency(
        "jinja2",
        "2.11.3",
        True,
        ("vulnerable", "transitive-root"),
        "OSV: 8 advisories over CVE-2024-22195, CVE-2024-34064, CVE-2024-56326, CVE-2025-27516; pulls markupsafe",
    ),
    Dependency(
        "packaging", "20.9", True, ("stale",), "latest is 26.3, six majors ahead"
    ),
    Dependency(
        "Unidecode",
        "1.4.0",
        True,
        ("copyleft",),
        "classifier: GNU General Public License v2 or later (GPLv2+)",
    ),
    Dependency(
        "six",
        "1.10.0",
        False,
        ("declared-unused",),
        "declared and never imported: deptry DEP002",
    ),
    Dependency(
        "markupsafe",
        "",
        True,
        ("undeclared-import",),
        "arrives through jinja2 and is imported directly: deptry DEP003",
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

_UNSAFE = """import hashlib
import subprocess


def run_expression(expr):
    return eval(expr)


def run_shell(name):
    return subprocess.run("ls " + name, shell=True, check=False)


def digest(value):
    return hashlib.md5(value.encode()).hexdigest()


def query(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = '%s'" % user_id)
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

_TEST_SLOW = """import time


def test_slow_but_passing():
    time.sleep(2)
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
