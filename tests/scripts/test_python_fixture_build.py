"""The generator's pure planning helpers (#45).

Everything tested here is decided before a subprocess runs: what each partition's
tree contains, which manager locks it, what that lock leaves behind and what has
to be thrown away again. `build()` itself is exercised by running it, which
Task 5 does and Task 7 makes a recorded smoke - a unit test that mocked the five
package managers would assert the mock rather than the route.
"""

from __future__ import annotations

import pytest
from build_python_fixtures import (
    BUILD_METADATA,
    LOCK_ARTIFACTS,
    PINNED_MANAGERS,
    declaring_manifest,
    discard_after_lock,
    fixture_readme,
    lock_command,
    plan_tree,
    prelock_commands,
)
from python_fixture_spec import PACKAGE, PARTITIONS, render_manifests, source_tree

# The manifest each partition declares its dependency set in. Written out rather
# than derived from `render_manifests`, because deriving it from the function
# under test would make the assertion true whatever that function returned - and
# the `pip` and `pipenv` partitions carrying a `setup.py` beside a non-pyproject
# manifest is exactly the arrangement worth pinning down.
DECLARING_MANIFEST = {
    "uv": "pyproject.toml",
    "pylock": "pyproject.toml",
    "poetry": "pyproject.toml",
    "pip": "requirements.txt",
    "pipenv": "Pipfile",
}


def test_every_partition_plans_manifests_and_the_seeded_source():
    for partition in PARTITIONS:
        tree = plan_tree(partition)
        assert f"src/{PACKAGE}/unsafe.py" in tree, partition
        assert "tests/test_order.py" in tree, partition
        assert DECLARING_MANIFEST[partition] in tree, partition


def test_the_planned_tree_is_the_manifests_and_nothing_but_the_seeded_source():
    for partition in PARTITIONS:
        expected = render_manifests(partition) | source_tree()
        assert plan_tree(partition) == expected, partition


def test_each_partition_locks_with_its_own_manager():
    assert lock_command("uv")[0] == "uv"
    assert "poetry" in " ".join(lock_command("poetry"))
    assert "pipenv" in " ".join(lock_command("pipenv"))
    assert lock_command("pip") == ()


def test_the_two_one_shot_managers_are_pinned_to_a_version():
    for manager, spec in PINNED_MANAGERS.items():
        assert spec.startswith(f"{manager}@"), spec
        assert spec != f"{manager}@", spec
    for partition in ("poetry", "pipenv"):
        assert PINNED_MANAGERS[partition] in lock_command(partition), partition


def test_the_pylock_partition_exports_rather_than_locks():
    command = " ".join(lock_command("pylock"))
    assert "--format pylock.toml" in command
    assert "--frozen" in command


def test_only_the_pylock_partition_needs_a_command_before_its_lock():
    assert prelock_commands("pylock") == (("uv", "lock"),)
    for partition in PARTITIONS:
        if partition != "pylock":
            assert prelock_commands(partition) == (), partition


def test_the_pylock_partition_discards_the_uv_lock_it_was_exported_from():
    assert discard_after_lock("pylock") == ("uv.lock",)
    for partition in PARTITIONS:
        if partition != "pylock":
            assert discard_after_lock(partition) == (), partition


def test_every_partition_names_the_artifact_its_lock_command_produces():
    for partition in PARTITIONS:
        artifacts = LOCK_ARTIFACTS[partition]
        assert bool(artifacts) == bool(lock_command(partition)), partition
        for artifact in artifacts:
            assert artifact not in plan_tree(partition), partition


def test_no_partition_keeps_an_artifact_it_also_discards():
    for partition in PARTITIONS:
        overlap = set(LOCK_ARTIFACTS[partition]) & set(discard_after_lock(partition))
        assert overlap == set(), partition


def test_each_partition_declares_the_set_in_exactly_one_file():
    for partition in PARTITIONS:
        declaring = declaring_manifest(partition)
        assert declaring == DECLARING_MANIFEST[partition], partition
        assert declaring != BUILD_METADATA, partition


def test_the_build_metadata_file_is_not_reported_as_a_declaration():
    for partition in ("pip", "pipenv"):
        readme = fixture_readme(partition, "uv 0.0.0")
        declaration_row = next(
            line for line in readme.splitlines() if line.startswith("| Declares")
        )
        assert DECLARING_MANIFEST[partition] in declaration_row, partition
        assert BUILD_METADATA not in declaration_row, partition
        # It is still named, as what it is: a reader who does not know why it is
        # there is a reader who would add `install_requires` to it.
        assert BUILD_METADATA in readme, partition


def test_the_readme_records_the_route_that_built_the_tree():
    readme = fixture_readme("poetry", "uv 0.0.0")
    assert "poetry" in readme
    assert PINNED_MANAGERS["poetry"] in readme
    assert "poetry.lock" in readme
    # The uv version is measured on the host, so it belongs only to the
    # partitions uv actually locks. Naming it under poetry would report a
    # version of a tool that did not build this tree.
    assert "uv 0.0.0" not in readme
    assert "uv 0.0.0" in fixture_readme("uv", "uv 0.0.0")


def test_the_readme_says_the_pip_partition_has_no_lock_step():
    readme = fixture_readme("pip", "uv 0.0.0")
    assert "requirements.txt" in readme
    assert "uv 0.0.0" not in readme


def test_every_partition_renders_a_readme_naming_itself():
    for partition in PARTITIONS:
        readme = fixture_readme(partition, "uv 0.0.0")
        assert partition in readme, partition
        assert PACKAGE in readme, partition


def test_an_unknown_partition_is_rejected_by_name():
    with pytest.raises(ValueError, match="conda"):
        plan_tree("conda")


def test_every_pure_helper_rejects_an_unknown_partition():
    for helper in (
        plan_tree,
        lock_command,
        prelock_commands,
        discard_after_lock,
        declaring_manifest,
    ):
        with pytest.raises(ValueError, match="conda"):
            helper("conda")
    with pytest.raises(ValueError, match="conda"):
        fixture_readme("conda", "uv 0.0.0")
