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


def test_source_tree_maps_paths_to_bodies():
    tree = source_tree()
    assert "src/fixture_app/domain/model.py" in tree
    assert tree["src/fixture_app/domain/model.py"].startswith('"""')
