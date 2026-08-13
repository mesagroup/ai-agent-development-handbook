"""Tests for scripts/python_fixture_spec.py (#45)."""

import re
import tomllib

import pytest
import python_fixture_spec
from python_fixture_spec import (
    DEPENDENCIES,
    PARTITIONS,
    SOURCE_FILES,
    declared,
    render_manifests,
    source_tree,
)


def test_every_dependency_name_is_a_bare_toml_key():
    """A dotted distribution name silently becomes a nested TOML table.

    The poetry and Pipfile renderers write `name = "pin"`, so a name such as
    `ruamel.yaml` parses as a table `ruamel` containing `yaml` rather than as
    one dependency. `tomllib` accepts it, every substring assertion here accepts
    it, and the manager reads a dependency that does not exist. The set is meant
    to be edited whenever a pin is re-verified, so this guards the next edit
    rather than the current contents.
    """
    for dependency in DEPENDENCIES:
        assert re.fullmatch(r"[A-Za-z0-9_-]+", dependency.name), dependency.name


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


def test_every_imported_dependency_is_imported_somewhere_in_the_tree():
    """The positive direction of the import claim.

    The unused seed's direction is guarded above by the absence of a string.
    This one guards the rest: deleting `import markupsafe` from the seeded
    source would otherwise retire the DEP003 seed while the dataclass and the
    expectation both went on claiming it. The module name is checked rather
    than the distribution name because they differ - `Unidecode` imports as
    `unidecode`.
    """
    body = "\n".join(f.body for f in SOURCE_FILES)
    for dependency in DEPENDENCIES:
        if dependency.imported:
            assert f"import {dependency.module}" in body, dependency.name


def test_source_tree_maps_paths_to_bodies():
    tree = source_tree()
    assert "src/fixture_app/domain/model.py" in tree
    assert tree["src/fixture_app/domain/model.py"].startswith('"""')


def test_source_tree_loses_no_file_to_a_duplicate_path():
    """Two SourceFile entries sharing a path would collapse into one.

    The body and the seeds of whichever came first would vanish with no error,
    and Task 5 merges this dict with the manifests, where a collision is
    equally silent.
    """
    assert len(source_tree()) == len(SOURCE_FILES)


def test_every_partition_renders_a_manifest():
    for partition in PARTITIONS:
        files = render_manifests(partition)
        assert files, partition
        assert all(body.strip() for body in files.values()), partition


def test_the_undeclared_dependency_reaches_no_manifest():
    """Derived from the definition rather than naming the package.

    Written against the literal string, this test goes on passing after the
    undeclared seed is swapped for another package - it would then assert that a
    name nothing renders is absent, which nothing can fail.
    """
    undeclared = [d.name.lower() for d in DEPENDENCIES if not d.pin]
    assert undeclared, "the undeclared-import seed has gone missing"
    for partition in PARTITIONS:
        for body in render_manifests(partition).values():
            for name in undeclared:
                assert name not in body.lower(), (partition, name)


def test_each_partition_uses_its_own_manifest_format():
    assert "pyproject.toml" in render_manifests("uv")
    assert "requirements.txt" in render_manifests("pip")
    assert "tool.poetry" in render_manifests("poetry")["pyproject.toml"]
    assert "Pipfile" in render_manifests("pipenv")


def test_the_requirements_partitions_declare_nothing_in_a_project_table():
    """The silencing declaration, which the competing-declaration guard misses.

    A `[project]` table carrying build metadata and no `dependencies` key is not
    silent about dependencies: it is an affirmative claim of zero. deptry reads
    it in preference to `requirements.txt` and then reports the real
    dependencies as DEP001 while the DEP002 seed disappears entirely, so the
    partition produces a full result from the wrong file.

    The guard against two files *declaring* the set cannot see this, because the
    offending table declares nothing - which is exactly what makes it wrong. So
    `pip` and `pipenv` are held to rendering no `pyproject.toml` at all.
    """
    for partition in ("pip", "pipenv"):
        files = render_manifests(partition)
        assert "pyproject.toml" not in files, partition
        assert not any("[project]" in body for body in files.values()), partition


def test_an_unknown_partition_is_rejected_by_name():
    with pytest.raises(ValueError, match="conda"):
        render_manifests("conda")


def test_a_partition_with_no_rendering_is_rejected_rather_than_given_anothers():
    """The branch that catches a name added to PARTITIONS and nowhere else.

    Without it the final branch would answer for any unrecognised name, so a new
    partition would be built from another partition's manifest and the run would
    report that format as exercised.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(python_fixture_spec, "PARTITIONS", (*PARTITIONS, "pdm"))
        with pytest.raises(ValueError, match="no manifest rendering"):
            render_manifests("pdm")


def test_every_toml_manifest_parses_as_toml():
    """A manifest is TOML before it is anything else.

    The renderers build these by string concatenation, so an unquoted value or a
    lost newline produces a file that reads correctly and that no manager can
    load. Parsing here is what stops that reaching a fixture tree, where it would
    surface as the manager failing and be read as a missing tool.

    Selected by shape rather than by a list of filenames, so a renderer that
    later emits `uv.toml` or `poetry.toml` is parsed too instead of silently
    escaping the check, and counted so that the whole test cannot pass by
    parsing nothing.
    """
    parsed = 0
    for partition in PARTITIONS:
        for name, body in render_manifests(partition).items():
            if name.endswith(".toml") or name == "Pipfile":
                tomllib.loads(body)
                parsed += 1
    assert parsed >= len(PARTITIONS) - 1, parsed


def test_every_declared_dependency_reaches_every_partition_at_its_pin():
    """Name and pin have to meet on one line, not merely both be present.

    Searching the concatenated bodies cannot tell a correct rendering from one
    with two pins swapped between packages: both names and both pins are still
    somewhere in the text. The round rests on the exact pins - jinja2 3.1.2 is
    what makes the vulnerability seed real - so the pairing is the property.
    """
    for partition in PARTITIONS:
        lines = "".join(render_manifests(partition).values()).splitlines()
        for dependency in declared():
            assert any(
                dependency.name in line and dependency.pin in line for line in lines
            ), (partition, dependency.name, dependency.pin)


def test_each_partition_declares_the_set_in_exactly_one_file():
    """Two files declaring the same set is how a partition stops being one.

    Each tool reads whichever manifest it prefers, so a partition whose format
    is never the one read still produces a full result and the run records the
    lens as exercised. The build manifest the `pip` and `pipenv` partitions need
    for their src-layout install therefore has to declare nothing.

    The carrier is found by dependency *name*, not by pin: an unpinned
    `install_requires=["jinja2"]` added to the build manifest declares the set a
    second time while carrying no pin at all, so a pin-based search would report
    one carrier and miss it.
    """
    for partition in PARTITIONS:
        files = render_manifests(partition)
        for dependency in declared():
            pattern = rf"(?i)(?<![\w.-]){re.escape(dependency.name)}(?![\w.-])"
            carriers = [n for n, body in files.items() if re.search(pattern, body)]
            assert len(carriers) == 1, (partition, dependency.name, carriers)


def test_every_partition_renders_exactly_one_build_manifest():
    """The src-layout package has to be installable in every partition.

    Running the seeded suite against a tree where only the dependencies were
    installed fails at collection with `ModuleNotFoundError: No module named
    'fixture_app'`, which is indistinguishable from a broken fixture. So every
    partition renders exactly one build manifest: a `pyproject.toml` carrying a
    build backend where the format allows it, and a `setup.py` where declaring
    the dependency set in `pyproject.toml` would take the partition's own format
    out of play.
    """
    for partition in PARTITIONS:
        files = render_manifests(partition)
        build_manifests = [n for n in files if n in ("pyproject.toml", "setup.py")]
        assert len(build_manifests) == 1, (partition, build_manifests)
        body = files[build_manifests[0]]
        assert "build-system" in body or "setuptools" in body, partition


def test_every_partition_states_the_interpreter_floor():
    """Each format spells the floor its own way, so the constant is the anchor.

    Interpolating `PYTHON_FLOOR` is what keeps the spellings from disagreeing;
    this fails if a renderer is written with the number typed in instead and the
    constant is later moved.
    """
    for partition in PARTITIONS:
        bodies = "".join(render_manifests(partition).values())
        assert python_fixture_spec.PYTHON_FLOOR in bodies, partition
