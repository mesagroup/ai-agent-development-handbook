"""The generator's planning helpers, plus the one partition that builds offline (#45).

Most of what is tested here is decided before a subprocess runs: what each
partition's tree contains, which manager locks it, what that lock leaves behind,
what has to be thrown away again and what the finished commit therefore holds.

`build` is exercised too, on the `pip` partition. Its lock command is empty, so
that whole build is git and the filesystem and nothing else, and the tree it
produces can be compared to the tree it planned. The honest boundary is the
other four partitions rather than the effectful half as such: each of them
fetches or runs a package manager, so what they add over `pip` is a network
round trip rather than another route through this module. They are covered by
the recorded smoke run instead - a unit test that mocked the five managers would
assert the mock rather than the route.
"""

from __future__ import annotations

import sys

import build_python_fixtures
import pytest
from build_python_fixtures import (
    BUILD_METADATA,
    FIXTURE_README,
    LOCK_ARTIFACTS,
    PINNED_MANAGERS,
    _git,
    _run,
    _stage,
    build,
    committed_files,
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

# What each partition's lock step is named to leave behind, written out for the
# same reason: read out of `LOCK_ARTIFACTS`, the assertion would hold whatever
# that mapping said, and the name is the half that matters. A tree committing
# `locked.txt` where uv writes `uv.lock` carries no lock any tool can read while
# every count still comes out right.
LOCK_ARTIFACT = {
    "uv": ("uv.lock",),
    "pip": (),
    "poetry": ("poetry.lock",),
    "pipenv": ("Pipfile.lock",),
    "pylock": ("pylock.toml",),
}

# What each partition's lock step produces and the build then deletes again.
DISCARDED = {
    "uv": (),
    "pip": (),
    "poetry": (),
    "pipenv": (),
    "pylock": ("uv.lock",),
}


def _row(readme: str, label: str) -> str:
    """The one table row of a rendered `FIXTURE.md` carrying this label.

    Rows rather than substrings, because every claim these tests make about the
    document is a claim about one cell: `poetry` occurring somewhere in a readme
    is satisfied by the partition name alone, while the `Built by` row is the
    only place the route that produced the tree is written down.
    """
    rows = [line for line in readme.splitlines() if line.startswith(f"| {label} |")]
    assert len(rows) == 1, f"expected one {label!r} row, found {rows}"
    return rows[0]


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
        assert artifacts == LOCK_ARTIFACT[partition], partition
        assert bool(artifacts) == bool(lock_command(partition)), partition
        for artifact in artifacts:
            assert artifact not in plan_tree(partition), partition


def test_a_lock_command_writing_to_a_named_path_writes_to_its_own_artifact():
    # The one partition whose lock step is an export rather than a manager's own
    # `lock`: the artifact is not a convention, it is the argument, so here the
    # name and the command can be tied together rather than written out.
    command = lock_command("pylock")
    assert "-o" in command
    assert (command[command.index("-o") + 1],) == LOCK_ARTIFACTS["pylock"]


def test_no_partition_keeps_an_artifact_it_also_discards():
    for partition in PARTITIONS:
        overlap = set(LOCK_ARTIFACTS[partition]) & set(discard_after_lock(partition))
        assert overlap == set(), partition


def test_the_committed_set_is_the_plan_the_readme_and_the_kept_artifacts():
    for partition in PARTITIONS:
        expected = set(plan_tree(partition)) | {FIXTURE_README}
        expected |= set(LOCK_ARTIFACT[partition])
        expected -= set(DISCARDED[partition])
        assert committed_files(partition) == tuple(sorted(expected)), partition


def test_the_pylock_partition_commits_no_uv_lock():
    # The invariant the partition exists for, asserted without a lock step: a
    # tree carrying both files is read by every lock-reading tool as a second
    # `uv` partition, and PEP 751 then goes untested while results look complete.
    assert "uv.lock" not in committed_files("pylock")
    assert "pylock.toml" in committed_files("pylock")
    assert "uv.lock" in committed_files("uv")


def test_each_partition_declares_the_set_in_exactly_one_file():
    for partition in PARTITIONS:
        declaring = declaring_manifest(partition)
        assert declaring == DECLARING_MANIFEST[partition], partition
        assert declaring != BUILD_METADATA, partition


def test_the_build_metadata_file_is_not_reported_as_a_declaration():
    for partition in ("pip", "pipenv"):
        readme = fixture_readme(partition, "uv 0.0.0")
        declaration_row = _row(readme, "Declares the dependency set in")
        assert DECLARING_MANIFEST[partition] in declaration_row, partition
        assert BUILD_METADATA not in declaration_row, partition
        # It is still named, as what it is: a reader who does not know why it is
        # there is a reader who would add `install_requires` to it.
        assert BUILD_METADATA in readme, partition


def test_the_readme_records_the_route_that_built_the_tree():
    poetry = fixture_readme("poetry", "uv 0.0.0")
    assert _row(poetry, "Built by") == (
        f"| Built by | `uvx {PINNED_MANAGERS['poetry']} lock` |"
    )
    assert _row(poetry, "Lock artifact") == "| Lock artifact | `poetry.lock` |"
    # The uv version is measured on the host, so it belongs only to the
    # partitions uv actually locks. Naming it under poetry would report a
    # version of a tool that did not build this tree.
    assert "uv 0.0.0" not in poetry
    assert _row(fixture_readme("uv", "uv 0.0.0"), "Manager") == (
        "| Manager | `uv 0.0.0`, taken from the host that ran the generator |"
    )


def test_the_readme_records_both_steps_of_the_pylock_route():
    # The one partition built by two commands. A row naming only the export
    # would describe a tree nobody could reproduce: the export reads a uv.lock
    # that has to be made first and thrown away after.
    assert _row(fixture_readme("pylock", "uv 0.0.0"), "Built by") == (
        "| Built by | `uv lock`; "
        "`uv export --format pylock.toml --frozen -o pylock.toml` |"
    )


def test_the_readme_says_the_pip_partition_has_no_lock_step():
    readme = fixture_readme("pip", "uv 0.0.0")
    assert _row(readme, "Built by") == "| Built by | no lock step |"
    assert _row(readme, "Lock artifact") == "| Lock artifact | none |"
    assert "uv 0.0.0" not in readme


def test_the_readme_says_what_the_pip_partition_pins_and_what_it_leaves_unpinned():
    # `requirements.txt` pins the declared set and nothing under it, and the
    # expectations record says so: calling the file this partition's lock would
    # promise a transitive pin set no check can find there.
    assert _row(fixture_readme("pip", "uv 0.0.0"), "Manager") == (
        "| Manager | none; `requirements.txt` pins each declared dependency with "
        "`==`, this partition has no separate lock format, and its transitive "
        "graph is unpinned |"
    )


def test_every_partition_renders_a_readme_naming_itself():
    for partition in PARTITIONS:
        readme = fixture_readme(partition, "uv 0.0.0")
        assert partition in readme, partition
        assert PACKAGE in readme, partition


def test_every_readme_states_the_constraints_a_reader_would_otherwise_break():
    # Each of these is a paragraph a reader acts on rather than prose: a tree
    # left untracked makes every semgrep check pass having read nothing, and a
    # resolve inside the directory is the write the read-only invariant forbids.
    for partition in PARTITIONS:
        readme = fixture_readme(partition, "uv 0.0.0")
        assert "Semgrep scans git-tracked files only" in readme, partition
        assert "`git status --porcelain` empty before and after" in readme, partition
        assert "do not resolve or install inside this directory" in readme, partition


def test_only_the_pylock_readme_explains_the_missing_uv_lock():
    assert "This partition carries no `uv.lock`" in fixture_readme("pylock", "uv 0.0.0")
    for partition in PARTITIONS:
        if partition != "pylock":
            readme = fixture_readme(partition, "uv 0.0.0")
            assert "carries no `uv.lock`" not in readme, partition


def test_an_unknown_partition_is_rejected_by_name():
    with pytest.raises(ValueError, match="conda"):
        plan_tree("conda")


def test_every_pure_helper_rejects_an_unknown_partition():
    for helper in (
        plan_tree,
        lock_command,
        prelock_commands,
        discard_after_lock,
        committed_files,
        declaring_manifest,
    ):
        with pytest.raises(ValueError, match="conda"):
            helper("conda")
    with pytest.raises(ValueError, match="conda"):
        fixture_readme("conda", "uv 0.0.0")


def test_a_failed_command_reports_the_stream_the_tool_wrote_on(tmp_path):
    # Poetry and pipenv report much of a failed resolution on stdout, so a
    # message carrying stderr alone reads as a tool that failed silently.
    with pytest.raises(RuntimeError) as on_stdout:
        _run(
            [sys.executable, "-c", "print('resolution detail'); raise SystemExit(3)"],
            tmp_path,
        )
    assert "exit code 3" in str(on_stdout.value)
    assert "stdout:\nresolution detail" in str(on_stdout.value)
    assert "stderr:" not in str(on_stdout.value)

    with pytest.raises(RuntimeError) as on_stderr:
        _run(
            [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('boom\\n'); raise SystemExit(4)",
            ],
            tmp_path,
        )
    assert "stderr:\nboom" in str(on_stderr.value)
    assert "stdout:" not in str(on_stderr.value)


def test_a_missing_command_is_reported_as_a_missing_command(tmp_path):
    with pytest.raises(RuntimeError, match="not on PATH"):
        _run(["no-such-tool-fbe0a1"], tmp_path)


def test_staging_takes_the_named_paths_and_leaves_everything_else(tmp_path):
    # `git add -A` here would sweep whatever the lock step left beside the
    # artifact into the commit, and the expectations describe none of it.
    _git(tmp_path, "init", "--quiet", "--initial-branch", "main")
    (tmp_path / "planned.txt").write_text("planned\n")
    (tmp_path / "stray.txt").write_text("stray\n")
    _stage(tmp_path, ["planned.txt"])
    staged = _git(tmp_path, "diff", "--cached", "--name-only").splitlines()
    assert staged == ["planned.txt"]


def test_the_pip_partition_builds_offline_into_exactly_the_files_it_planned(tmp_path):
    # The one partition whose whole build is git and the filesystem: its lock
    # command is empty, so this runs the effectful half end to end with no
    # package manager and no network.
    root = tmp_path / "pip"
    summary = build("pip", root, uv_version="uv 0.0.0")

    tracked = sorted(_git(root, "ls-files").splitlines())
    assert tracked == list(committed_files("pip"))
    assert summary == {
        "partition": "pip",
        "root": str(root),
        "tracked": str(len(tracked)),
    }
    assert _git(root, "status", "--porcelain") == ""
    assert (root / FIXTURE_README).read_text() == fixture_readme("pip", "uv 0.0.0")


def test_a_second_build_replaces_its_own_tree_and_refuses_any_other(tmp_path):
    root = tmp_path / "pip"
    build("pip", root, uv_version="uv 0.0.0")
    (root / "leftover.txt").write_text("from the previous build\n")
    build("pip", root, uv_version="uv 0.0.0")
    assert not (root / "leftover.txt").exists()

    foreign = tmp_path / "pip-elsewhere"
    foreign.mkdir()
    (foreign / "notes.txt").write_text("somebody's directory\n")
    with pytest.raises(RuntimeError, match="not written by this generator"):
        build("pip", foreign, uv_version="uv 0.0.0")
    assert (foreign / "notes.txt").exists()


def test_a_build_that_leaves_the_tree_dirty_is_refused(tmp_path, monkeypatch):
    # A tree with an uncommitted file in it is one no audit run can start from:
    # the read-only invariant is `git status --porcelain` unchanged, which says
    # nothing when it was already non-empty.
    monkeypatch.setattr(
        build_python_fixtures,
        "prelock_commands",
        lambda partition: ((sys.executable, "-c", "open('stray.txt', 'w').write('')"),),
    )
    with pytest.raises(RuntimeError, match="dirty after its build"):
        build("pip", tmp_path / "pip", uv_version="uv 0.0.0")


def test_a_lock_step_that_produced_no_artifact_is_reported_as_such(
    tmp_path, monkeypatch
):
    # Named after the artifact rather than after `git add`'s pathspec error,
    # because those are different diagnoses: one says the lock step did not run,
    # the other says the staging list is wrong.
    monkeypatch.setitem(LOCK_ARTIFACTS, "pip", ("ghost.lock",))
    with pytest.raises(RuntimeError, match=r"lock step produced no ghost\.lock"):
        build("pip", tmp_path / "pip", uv_version="uv 0.0.0")
