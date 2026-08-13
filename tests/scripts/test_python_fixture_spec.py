"""Tests for scripts/python_fixture_spec.py (#45)."""

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
