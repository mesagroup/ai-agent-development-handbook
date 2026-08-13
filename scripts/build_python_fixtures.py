"""Write the five seeded Python fixture partitions (#45).

The definition lives in `python_fixture_spec.py` and touches nothing; this is
the effectful half. It renders one partition's manifests and the shared seeded
source into a directory, makes that directory a git repository with everything
committed, runs the partition's own lock step and commits what it produced.

**Each fixture is a git repository with everything committed**, for two reasons
that both bite otherwise. Semgrep limits its scan to git-tracked files and says
so only in a note, so an untracked tree would make every `security` check pass
vacuously - a clean result from a scanner that read nothing. And the read-only
invariant every audit run checks is `git status --porcelain` empty before and
after, which is not a comparison that means anything outside a repository.

**The trees are generated, never committed, and never installed into.** Nothing
here materializes a partition: resolving a tree writes a lock, a cache or a
virtual environment into it, which is the write the invariant above forbids and
which would leave the committed tree dirty. Materializing a partition to run a
check against it is the caller's job and belongs in a copy outside the tree,
which is what `audit-core` prescribes for a real target as well.

Usage:
    uv run python scripts/build_python_fixtures.py --all
    uv run python scripts/build_python_fixtures.py uv poetry
    uv run python scripts/build_python_fixtures.py --all --output-dir <dir>
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from python_fixture_spec import PACKAGE, PARTITIONS, render_manifests, source_tree

REPO_ROOT = Path(__file__).resolve().parent.parent

# Derived from this file's location rather than written down, and overridable
# with `--output-dir`, so that no personal path reaches a committed file and a
# caller building somewhere else does not have to edit the script to do it.
DEFAULT_OUTPUT_DIR = REPO_ROOT / "fixtures" / "python"

# The managers that are fetched per run rather than taken from the host, pinned
# to an exact version. A fixture built with whatever poetry the machine happens
# to carry records a lock format nobody can reproduce, and the round's whole
# point is that its observations are reproducible. `uv` is deliberately not in
# here: it is the toolchain this repository already runs under, so pinning a
# second copy of it would test a uv no caller of this script uses. Its measured
# version is recorded in each tree it builds instead.
PINNED_MANAGERS = {
    "poetry": "poetry@2.4.1",
    "pipenv": "pipenv@2026.7.1",
}

# What each partition's lock step leaves behind, and therefore what the second
# commit carries. `pip` has none because its `requirements.txt` is already a
# fully pinned list: there is no resolution step to record.
LOCK_ARTIFACTS = {
    "uv": ("uv.lock",),
    "pip": (),
    "poetry": ("poetry.lock",),
    "pipenv": ("Pipfile.lock",),
    "pylock": ("pylock.toml",),
}

# The identity the fixture commits are made under. A fake domain, because a real
# one in a generated tree is an environment-specific value in everything the
# fixture is later copied into - and because the host's own identity is not
# always set, which would make `git commit` fail for a reason that has nothing
# to do with the fixture.
COMMIT_NAME = "Fixture Builder"
COMMIT_EMAIL = "fixture@example.invalid"


def _known(partition: str) -> str:
    """Return the partition, or fail naming it and what is available."""
    if partition not in PARTITIONS:
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {PARTITIONS}"
        )
    return partition


def plan_tree(partition: str) -> dict[str, str]:
    """Every file one partition's tree holds before its lock step runs.

    The manifests differ per partition and the seeded source does not, which is
    what makes one expectations table serve all five.
    """
    return render_manifests(_known(partition)) | source_tree()


def prelock_commands(partition: str) -> tuple[tuple[str, ...], ...]:
    """Commands that must run before `lock_command`, and whose output is not kept.

    Only `pylock` has one. `uv export --format pylock.toml` reads an existing
    `uv.lock`, so that partition resolves with uv first and then throws the
    resolution away again - see `discard_after_lock` for why keeping it would
    quietly retire the partition.
    """
    if _known(partition) == "pylock":
        return (("uv", "lock"),)
    return ()


def lock_command(partition: str) -> tuple[str, ...]:
    """The one invocation that produces this partition's committed lock artifact.

    Empty for `pip`, whose `requirements.txt` is written fully pinned by the
    definition and so is its own lock.
    """
    match _known(partition):
        case "uv":
            return ("uv", "lock")
        case "pip":
            return ()
        case "poetry":
            return ("uvx", PINNED_MANAGERS["poetry"], "lock")
        case "pipenv":
            return ("uvx", PINNED_MANAGERS["pipenv"], "lock")
        case "pylock":
            return (
                "uv",
                "export",
                "--format",
                "pylock.toml",
                "--frozen",
                "-o",
                "pylock.toml",
            )
    # Unreachable while PARTITIONS and the arms above agree. A name added to
    # PARTITIONS with no lock route lands here rather than falling through to a
    # return of `()`, which would read as "this partition needs no lock" and
    # commit a tree with no resolution in it.
    raise ValueError(f"partition {partition!r} is named in PARTITIONS but has no lock")


def discard_after_lock(partition: str) -> tuple[str, ...]:
    """Files the lock step produced that must not reach the commit.

    The `pylock` partition's `pyproject.toml` is byte-identical to the `uv`
    partition's, so a tree carrying both `pylock.toml` and the `uv.lock` it was
    exported from is read by every lock-reading tool as a second `uv` run. The
    one format `pip-audit --locked` actually reads then goes untested while the
    results look complete, which is the failure this whole round exists to
    catch, arriving from the fixture rather than from the tool.
    """
    if _known(partition) == "pylock":
        return ("uv.lock",)
    return ()


def _manager_line(partition: str, uv_version: str) -> str:
    """How the partition's lock step was provisioned, for the tree's own record."""
    if partition in PINNED_MANAGERS:
        return f"`uvx {PINNED_MANAGERS[partition]}`, pinned by the generator"
    if partition == "pip":
        return "none; `requirements.txt` is written fully pinned and is this partition's lock"
    return f"`{uv_version}`, taken from the host that ran the generator"


BUILD_METADATA = "setup.py"


def declaring_manifest(partition: str) -> str:
    """The one file in this partition's tree that declares the dependency set.

    Every partition declares the set in exactly one file, and the `pip` and
    `pipenv` trees carry a second manifest that declares nothing: `setup.py` is
    build metadata with no `install_requires`, there so the src-layout package
    installs without competing with the partition's own declaration format.
    Listing both as declarations in the tree's own record would say the opposite
    of what that file was written to do.
    """
    declaring = [p for p in render_manifests(_known(partition)) if p != BUILD_METADATA]
    if len(declaring) != 1:
        raise ValueError(
            f"partition {partition!r} renders {len(declaring)} declaring manifests "
            f"({sorted(declaring)}); one partition declares the set once, so a second "
            "would let each tool read whichever format it prefers"
        )
    return declaring[0]


def fixture_readme(partition: str, uv_version: str) -> str:
    """The `FIXTURE.md` written into one tree.

    Pure, and it takes the measured uv version rather than reading it, so the
    document a build produces can be asserted without running a build.
    """
    lock = lock_command(_known(partition))
    prelock = prelock_commands(partition)
    artifacts = LOCK_ARTIFACTS[partition]
    steps = [" ".join(c) for c in (*prelock, lock) if c]
    lines = [
        f"# Seeded audit fixture - `{partition}` partition",
        "",
        "Generated by `scripts/build_python_fixtures.py` from `scripts/python_fixture_spec.py`, in the handbook repository this tree was built from. Everything here is planted, including the defects. What each check must observe when it runs against this tree is written down in advance, in that same repository at `docs/audit/python-fixture-expectations.md`; a tool that runs cleanly and reports half of it fails rather than passes.",
        "",
        f"The package is `{PACKAGE}`, src-layout, so materializing this partition has to install the project and not only its dependencies - a dependency-only install leaves `import {PACKAGE}` raising `ModuleNotFoundError`, which reads as a broken fixture rather than as an incomplete install.",
        "",
        "| | |",
        "|---|---|",
        f"| Partition | `{partition}` |",
        f"| Declares the dependency set in | `{declaring_manifest(partition)}` |",
        f"| Lock artifact | {', '.join(f'`{a}`' for a in artifacts) if artifacts else 'none'} |",
        f"| Built by | {'; '.join(f'`{s}`' for s in steps) if steps else 'no lock step'} |",
        f"| Manager | {_manager_line(partition, uv_version)} |",
        "",
        "This tree is a git repository with everything committed, and both halves of that matter. Semgrep scans git-tracked files only, so an untracked tree would make every security check pass having read nothing; and `git status --porcelain` empty before and after a run, which is how an audit proves it wrote nothing, means nothing outside a repository.",
        "",
        "So do not resolve or install inside this directory. Copy it somewhere else and materialize the copy, which is what an audit run is required to do against a real target too.",
    ]
    if BUILD_METADATA in render_manifests(partition):
        lines += [
            "",
            f"`{BUILD_METADATA}` here is build metadata and nothing else: it carries no `install_requires`, so the package installs without declaring a second copy of the dependency set. A `[project]` table would not have that property - an absent `dependencies` key in one is an affirmative claim of zero, which deptry reads in preference to this partition's own manifest.",
        ]
    if partition == "pylock":
        lines += [
            "",
            "This partition carries no `uv.lock`. The export that produces `pylock.toml` reads one, and it is deleted again before the commit: this partition's `pyproject.toml` is byte-identical to the `uv` partition's, so a tree holding both files is read by every lock-reading tool as a second `uv` run, leaving PEP 751 untested while the results look complete.",
        ]
    return "\n".join(lines) + "\n"


def _fixture_env() -> dict[str, str]:
    """The environment the fixture subprocesses run under.

    The generator itself runs under `uv run`, which exports `VIRTUAL_ENV`
    pointing at this repository's environment. A package manager invoked in a
    fixture tree with that set resolves against the handbook's environment
    instead of the fixture's, so it comes out of the environment here rather
    than being worked around per command.
    """
    env = dict(os.environ)
    for name in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH"):
        env.pop(name, None)
    # Pipenv otherwise adopts an already-active environment rather than
    # resolving the Pipfile in front of it.
    env["PIPENV_IGNORE_VIRTUALENVS"] = "1"
    return env


def _run(command: Sequence[str], cwd: Path) -> str:
    """Run one command in a fixture tree, or raise naming it and its stderr.

    Nothing here swallows a failure: a lock step that errored and was ignored
    produces a tree that looks built and carries no resolution, which is
    indistinguishable at review from a partition whose manager has no lock.
    """
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=_fixture_env(),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"{command[0]!r} is not on PATH, needed to build {cwd.name!r}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    if completed.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} failed in {cwd.name!r} with exit code "
            f"{completed.returncode}\nstderr:\n{completed.stderr.strip()}"
        )
    return completed.stdout


def _git(root: Path, *args: str) -> str:
    """Run git in a fixture tree under the fixture's own identity.

    The identity and the signing flag are passed per invocation rather than
    written into the tree's config: a host that signs commits by default, or one
    with no `user.email` set at all, would otherwise decide whether a fixture
    builds.
    """
    return _run(
        (
            "git",
            "-c",
            f"user.name={COMMIT_NAME}",
            "-c",
            f"user.email={COMMIT_EMAIL}",
            "-c",
            "commit.gpgsign=false",
            *args,
        ),
        root,
    )


def _measure_uv_version() -> str:
    """The host uv, as it identifies itself. Recorded in the trees uv locks."""
    if shutil.which("uv") is None:
        raise RuntimeError("uv is not on PATH; every partition's build needs it")
    completed = subprocess.run(
        ["uv", "--version"], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"uv --version failed with exit code {completed.returncode}\n"
            f"stderr:\n{completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _clear(root: Path, partition: str) -> None:
    """Remove a previous build of this partition, and nothing else.

    A generator that overwrites is what a caller wants from gitignored output,
    and a recursive delete of a path handed in on the command line is not. So
    the refusal is narrow and explicit: only a directory this generator wrote -
    named for its partition and carrying the `FIXTURE.md` only a build produces
    - is replaced, and anything else is reported rather than removed.
    """
    if not root.exists():
        return
    if root.name != partition or not (root / "FIXTURE.md").exists():
        raise RuntimeError(
            f"{root} exists and was not written by this generator "
            f"(expected a directory named {partition!r} carrying FIXTURE.md); "
            "remove it yourself or build somewhere else"
        )
    shutil.rmtree(root)


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for relative, body in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)


def _stage(root: Path, paths: Iterable[str]) -> None:
    """Stage exactly the named paths.

    Explicit paths rather than `git add -A`: the second commit must carry the
    lock artifact and nothing the lock step happened to leave beside it, and a
    cache directory swept in here would be a file the expectations do not
    describe sitting in every tree a check reads.
    """
    _git(root, "add", "--", *paths)


def build(partition: str, root: Path, uv_version: str | None = None) -> dict[str, str]:
    """Write, commit and lock one partition. Returns a summary of what it did.

    Args:
        partition: One of `PARTITIONS`.
        root: The directory to build in. Replaced if a previous build of this
            same partition is there, refused if anything else is.
        uv_version: The host uv version to record; measured when omitted.

    Returns:
        A mapping of partition, root, tracked file count and dirty file count,
        each as a string, for the caller to print or assert on.
    """
    _known(partition)
    uv_version = uv_version if uv_version is not None else _measure_uv_version()
    _clear(root, partition)
    root.mkdir(parents=True)

    files = plan_tree(partition)
    _write_tree(root, files)
    (root / "FIXTURE.md").write_text(fixture_readme(partition, uv_version))

    _git(root, "init", "--quiet", "--initial-branch", "main")
    _stage(root, [*sorted(files), "FIXTURE.md"])
    _git(
        root, "commit", "--quiet", "-m", f"Seeded fixture source, {partition} manifests"
    )

    for command in prelock_commands(partition):
        _run(command, root)
    if lock_command(partition):
        _run(lock_command(partition), root)
    for name in discard_after_lock(partition):
        discarded = root / name
        if not discarded.exists():
            raise RuntimeError(
                f"{name} was to be discarded from the {partition!r} tree and is not "
                "there; the lock step did not produce what this partition expects"
            )
        discarded.unlink()

    for name in LOCK_ARTIFACTS[partition]:
        if not (root / name).exists():
            raise RuntimeError(
                f"the {partition!r} lock step produced no {name}; "
                f"ran: {' '.join(lock_command(partition))}"
            )
    if LOCK_ARTIFACTS[partition]:
        _stage(root, LOCK_ARTIFACTS[partition])
        _git(
            root, "commit", "--quiet", "-m", f"Lock the dependency set for {partition}"
        )

    dirty = _git(root, "status", "--porcelain").splitlines()
    if dirty:
        raise RuntimeError(
            f"the {partition!r} tree is dirty after its build, which no run can "
            "start from:\n" + "\n".join(dirty)
        )
    tracked = _git(root, "ls-files").splitlines()
    for name in discard_after_lock(partition):
        if name in tracked:
            raise RuntimeError(
                f"{name} was discarded from the {partition!r} tree and is tracked "
                "anyway; a previous build committed it"
            )
    return {
        "partition": partition,
        "root": str(root),
        "tracked": str(len(tracked)),
        "dirty": str(len(dirty)),
    }


def main(argv: list[str] | None = None) -> int:
    """Build the requested partitions.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `0` when every requested partition built.
    """
    parser = argparse.ArgumentParser(
        description="Write the seeded Python fixture partitions."
    )
    parser.add_argument(
        "partitions",
        nargs="*",
        choices=list(PARTITIONS),
        help="partitions to build; omit and pass --all for every one",
    )
    parser.add_argument("--all", action="store_true", help="build every partition")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"where the trees go (default: {DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)} under the repository)",
    )
    args = parser.parse_args(argv)

    requested = tuple(PARTITIONS) if args.all else tuple(args.partitions)
    if not requested:
        parser.error("name at least one partition, or pass --all")

    uv_version = _measure_uv_version()
    for partition in requested:
        summary = build(partition, args.output_dir / partition, uv_version)
        print(
            f"{summary['partition']}: {summary['tracked']} tracked, "
            f"{summary['dirty']} dirty, in {summary['root']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
