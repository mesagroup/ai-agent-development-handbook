"""Write the seeded fixture partitions: five Python (#45), two TypeScript (#181).

The definition lives in `python_fixture_spec.py` and touches nothing; this is
the effectful half. It renders one partition's manifests and the shared seeded
source into a directory, makes that directory a git repository with everything
committed, runs the partition's own lock step and commits what it produced.
Which language a partition belongs to is `lang_of`'s answer, and every helper
below that differs by language dispatches on it.

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
    uv run python scripts/build_python_fixtures.py npm pnpm
    uv run python scripts/build_python_fixtures.py --all --output-dir <dir>
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from python_fixture_spec import (
    PACKAGE,
    PARTITIONS,
    TS_MANAGER_PINS,
    TS_PARTITIONS,
    lang_of,
    render_manifests,
    source_tree,
    ts_render_manifests,
    ts_source_tree,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Derived from this file's location rather than written down, and overridable
# with `--output-dir`, so that no personal path reaches a committed file and a
# caller building somewhere else does not have to edit the script to do it.
DEFAULT_OUTPUT_DIR = REPO_ROOT / "fixtures" / "python"
TS_DEFAULT_OUTPUT_DIR = REPO_ROOT / "fixtures" / "typescript"
DEFAULT_OUTPUT_DIRS = {
    "python": DEFAULT_OUTPUT_DIR,
    "typescript": TS_DEFAULT_OUTPUT_DIR,
}

# The managers that are fetched per run rather than taken from the host, pinned
# to an exact version. A fixture built with whatever poetry the machine happens
# to carry records a lock format nobody can reproduce, and the round's whole
# point is that its observations are reproducible. `uv` is deliberately not in
# here: it is the toolchain this repository already runs under, so pinning a
# second copy of it would test a uv no caller of this script uses. Its measured
# version is recorded in each tree it builds instead. The TypeScript managers are pinned by
# the fixture itself, in `TS_MANAGER_PINS`, because each tree declares its own
# `packageManager`; `check_manager_version` holds the host to that pin.
PINNED_MANAGERS = {
    "poetry": "poetry@2.4.1",
    "pipenv": "pipenv@2026.7.1",
}

# What each partition's lock step leaves behind, and therefore what the second
# commit carries. `pip` has none: its `requirements.txt` pins the declared set
# with `==` and there is no separate lock format to generate, so that partition's
# transitive graph stays unpinned.
LOCK_ARTIFACTS = {
    "uv": ("uv.lock",),
    "pip": (),
    "poetry": ("poetry.lock",),
    "pipenv": ("Pipfile.lock",),
    "pylock": ("pylock.toml",),
    "npm": ("package-lock.json",),
    "pnpm": ("pnpm-lock.yaml",),
}

# The one registry every TypeScript lock is resolved against. A lockfile records
# each package's `resolved` URL, so a lock taken through a mirror names a host
# another machine may not reach and differs byte for byte from one taken
# without it; the public registry is the one every reader can resolve.
PUBLIC_NPM_REGISTRY = "https://registry.npmjs.org/"

# The record every built tree carries, written by the generator rather than
# planned by the definition, and the marker `_clear` recognizes a previous build
# by. Named once because three places have to agree on it.
FIXTURE_README = "FIXTURE.md"

# The identity the fixture commits are made under. A fake domain, because a real
# one in a generated tree is an environment-specific value in everything the
# fixture is later copied into - and because the host's own identity is not
# always set, which would make `git commit` fail for a reason that has nothing
# to do with the fixture.
COMMIT_NAME = "Fixture Builder"
COMMIT_EMAIL = "fixture@example.invalid"


def _known(partition: str) -> str:
    """Return the partition, or fail naming it and what is available."""
    lang_of(partition)
    return partition


def _known_python(partition: str) -> str:
    """Return a Python partition, or fail naming it.

    For the helpers whose question only a Python partition has an answer to,
    such as which single file declares the set: a TypeScript partition is refused
    by name rather than answered with a guess.
    """
    if lang_of(partition) != "python":
        raise ValueError(
            f"{partition!r} is a {lang_of(partition)} partition; this helper answers "
            f"for the Python partitions {PARTITIONS} only"
        )
    return partition


def plan_tree(partition: str) -> dict[str, str]:
    """The files one partition's tree holds whose content this module renders.

    Not the whole tree: `build` also writes `FIXTURE.md`, which is rendered from
    the plan rather than part of it, and the lock step adds this partition's lock
    artifact afterwards. `committed_files` is the union of the three and is what
    a built tree is checked against.

    On Python the manifests differ per partition and the seeded source does not,
    which is what makes one expectations table serve all five. On TypeScript the
    source is the same files under a different prefix: the tree root on npm, the
    core workspace member on pnpm.
    """
    if lang_of(partition) == "typescript":
        return ts_render_manifests(partition) | ts_source_tree(partition)
    return render_manifests(partition) | source_tree()


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

    Empty for `pip`: the definition writes `requirements.txt` with every declared
    dependency pinned by `==`, and that partition has no separate lock format to
    generate, so there is no resolution step and no transitive pin set.
    """
    match _known(partition):
        case "npm":
            return (
                "npm",
                "install",
                "--package-lock-only",
                "--ignore-scripts",
                "--no-audit",
                "--no-fund",
            )
        case "pnpm":
            # Through corepack, which provisions pnpm from the tree's own
            # `packageManager` pin: pnpm is not a host tool here, and a pnpm that
            # happened to be on PATH would be a manager the fixture never named.
            return (
                "corepack",
                "pnpm",
                "install",
                "--lockfile-only",
                "--ignore-scripts",
            )
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
    # Unreachable while the partition tuples and the arms above agree. A name
    # added to either tuple with no lock route lands here rather than falling through to a
    # return of `()`, which would read as "this partition needs no lock" and
    # commit a tree with no resolution in it.
    raise ValueError(f"partition {partition!r} is a known partition but has no lock")


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


def committed_files(partition: str) -> tuple[str, ...]:
    """Every path a finished build of this partition has committed, sorted.

    The planned tree, plus the `FIXTURE.md` the generator writes, plus the lock
    artifacts the lock step produces, minus whatever that step produced and this
    partition throws away again. `build` compares the tree's own `git ls-files`
    against this, which is what makes the pylock partition's missing `uv.lock` an
    asserted property of the build rather than a step that could stop running
    without anything noticing - and what makes the whole expected set assertable
    here, without a package manager.
    """
    kept = (
        set(plan_tree(partition)) | {FIXTURE_README} | set(LOCK_ARTIFACTS[partition])
    ) - set(discard_after_lock(partition))
    return tuple(sorted(kept))


def _manager_line(partition: str, uv_version: str) -> str:
    """How the partition's lock step was provisioned, for the tree's own record."""
    if partition in PINNED_MANAGERS:
        return f"`uvx {PINNED_MANAGERS[partition]}`, pinned by the generator"
    if partition == "pip":
        return (
            "none; `requirements.txt` pins each declared dependency with `==`, this "
            "partition has no separate lock format, and its transitive graph is unpinned"
        )
    return f"`{uv_version}`, taken from the host that ran the generator"


BUILD_METADATA = "setup.py"


def declaring_manifest(partition: str) -> str:
    """The one file in this partition's tree that declares the dependency set.

    Every partition declares the set in exactly one file, and this partition may
    render a second manifest that declares nothing: `setup.py` is build metadata
    with no `install_requires`, there so the src-layout package installs without
    competing with the partition's own declaration format. Listing both as
    declarations in the tree's own record would say the opposite of what that
    file was written to do, so the build-metadata name is excluded by name and
    the result is required to be unique.
    """
    declaring = [
        p for p in render_manifests(_known_python(partition)) if p != BUILD_METADATA
    ]
    if len(declaring) != 1:
        raise ValueError(
            f"partition {partition!r} renders {len(declaring)} declaring manifests "
            f"({sorted(declaring)}); one partition declares the set once, so a second "
            "would let each tool read whichever format it prefers"
        )
    return declaring[0]


def fixture_readme(partition: str, uv_version: str) -> str:
    """The `FIXTURE.md` written into one tree.

    Pure, and it takes the measured version rather than reading it, so the
    document a build produces can be asserted without running a build. On a
    Python partition that is the host uv; on a TypeScript one it is the version
    the partition's own manager reported, which `check_manager_version` has
    already held equal to the pin.
    """
    if lang_of(partition) == "typescript":
        return _ts_fixture_readme(partition, uv_version)
    lock = lock_command(partition)
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


def ts_declaring_manifests(partition: str) -> tuple[str, ...]:
    """Every `package.json` in a TypeScript partition's tree, sorted.

    The npm partition declares its set in one manifest; the pnpm workspace
    splits it across the root and its two members, which is the property the
    leaf-only stale seed rests on, so the record names all three.
    """
    if lang_of(partition) != "typescript":
        raise ValueError(f"{partition!r} is not a TypeScript partition")
    return tuple(
        sorted(
            p
            for p in ts_render_manifests(partition)
            if p.rsplit("/", 1)[-1] == "package.json"
        )
    )


def pinned_manager_version(partition: str) -> str:
    """The version a TypeScript partition's `packageManager` pin names."""
    if lang_of(partition) != "typescript":
        raise ValueError(f"{partition!r} is not a TypeScript partition")
    return TS_MANAGER_PINS[partition].split("@", 1)[1]


def manager_version_command(partition: str) -> tuple[str, ...]:
    """The command whose output is the manager version this partition locks with.

    npm is the host's: nothing provisions it from the pin, so the host has to be
    the pinned one. pnpm comes from corepack, and only answers for the pin when
    corepack can see it, so `measure_manager_version` runs this in a directory
    carrying the partition's root manifest.
    """
    match lang_of(partition), partition:
        case "typescript", "npm":
            return ("npm", "--version")
        case "typescript", "pnpm":
            return ("corepack", "pnpm", "--version")
    raise ValueError(f"{partition!r} has no manager version probe")


def check_manager_version(partition: str, reported: str) -> str:
    """Return the reported version, or refuse the build naming both versions.

    A lockfile's format and its resolution both depend on the manager version,
    so a lock taken by a manager other than the pinned one is a tree nobody can
    reproduce from the pin it declares.
    """
    pinned = pinned_manager_version(partition)
    version = reported.strip()
    if version != pinned:
        raise RuntimeError(
            f"refusing to build {partition!r}: "
            f"`{' '.join(manager_version_command(partition))}` reports {version!r}, "
            f"and the partition's packageManager pin is {TS_MANAGER_PINS[partition]!r}"
        )
    return version


def _probe(command: Sequence[str], cwd: Path, env: Mapping[str, str]) -> str:
    """Run a version probe and return its stdout, or raise naming its output."""
    return _run(command, cwd, env=dict(env))


def measure_manager_version(
    partition: str,
    probe: Callable[[Sequence[str], Path, Mapping[str, str]], str] = _probe,
) -> str:
    """Probe this partition's manager and hold it equal to the pin.

    Run before anything is written or cleared, in a scratch directory carrying
    only the partition's root `package.json`: that is the file corepack reads
    the pin from, and a refused build then leaves no half-written tree behind.
    """
    command = manager_version_command(partition)
    with tempfile.TemporaryDirectory(prefix=f"fixture-probe-{partition}-") as scratch:
        where = Path(scratch)
        (where / "package.json").write_text(
            ts_render_manifests(partition)["package.json"]
        )
        reported = probe(command, where, ts_fixture_env())
    return check_manager_version(partition, reported)


def _ts_fixture_readme(partition: str, manager_version: str) -> str:
    """The `FIXTURE.md` written into one TypeScript tree."""
    artifacts = LOCK_ARTIFACTS[partition]
    pin = TS_MANAGER_PINS[partition]
    if partition == "pnpm":
        manager = (
            f"`pnpm {manager_version}`, provisioned by corepack from the "
            f"`packageManager` pin `{pin}`"
        )
    else:
        manager = (
            f"`npm {manager_version}`, taken from the host and held equal to the "
            f"`packageManager` pin `{pin}`"
        )
    lines = [
        f"# Seeded audit fixture - `{partition}` partition",
        "",
        "Generated by `scripts/build_python_fixtures.py` from `scripts/python_fixture_spec.py`, in the handbook repository this tree was built from. Everything here is planted, including the defects. What each check must observe when it runs against this tree is written down in advance, in that same repository at `docs/audit/typescript-fixture-expectations.md`; a tool that runs cleanly and reports half of it fails rather than passes.",
        "",
        "| | |",
        "|---|---|",
        f"| Partition | `{partition}` |",
        f"| Declares the dependency set in | {', '.join(f'`{m}`' for m in ts_declaring_manifests(partition))} |",
        f"| Lock artifact | {', '.join(f'`{a}`' for a in artifacts)} |",
        f"| Built by | `{' '.join(lock_command(partition))}` |",
        f"| Registry | `{PUBLIC_NPM_REGISTRY}`, set by the generator |",
        f"| Manager | {manager} |",
        "",
        "The lockfile was generated without installing: no `node_modules` was written and no install script ran.",
        "",
        "This tree is a git repository with everything committed, and both halves of that matter. Semgrep scans git-tracked files only, so an untracked tree would make every security check pass having read nothing; and `git status --porcelain` empty before and after a run, which is how an audit proves it wrote nothing, means nothing outside a repository.",
        "",
        "So do not resolve or install inside this directory. Copy it somewhere else and materialize the copy, which is what an audit run is required to do against a real target too.",
    ]
    return "\n".join(lines) + "\n"


def _fixture_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """The environment the fixture subprocesses run under.

    Two kinds of host setting decide what a lock step produces, and both are
    removed here rather than worked around per command.

    An environment pointer, first. The generator itself runs under `uv run`,
    which exports `VIRTUAL_ENV` pointing at this repository's environment; a
    package manager invoked in a fixture tree with that set resolves against the
    handbook's environment instead of the fixture's. The in-project variants are
    the same failure in the other direction - each one puts a `.venv` inside the
    tree the build is about to commit, which is the write the tree's own
    read-only invariant forbids.

    An index override, second. A lock resolved against a private index records
    versions and hashes another host cannot obtain, which contradicts the one
    property the pinned managers above exist to give the fixture. Both the
    current and the deprecated uv spellings are removed, since uv still reads
    the deprecated pair.
    """
    env = dict(os.environ if base is None else base)
    for name in (
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "PYTHONPATH",
        "PIPENV_VENV_IN_PROJECT",
        "POETRY_VIRTUALENVS_IN_PROJECT",
        "UV_INDEX",
        "UV_DEFAULT_INDEX",
        "UV_INDEX_URL",
        "UV_EXTRA_INDEX_URL",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
    ):
        env.pop(name, None)
    # Pipenv otherwise adopts an already-active environment rather than
    # resolving the Pipfile in front of it.
    env["PIPENV_IGNORE_VIRTUALENVS"] = "1"
    return env


def _is_registry_setting(name: str) -> bool:
    """Whether an environment variable sets an npm or pnpm registry.

    Both managers read `npm_config_*` in either case, and a scoped registry is
    spelled `npm_config_@scope:registry`, so the test is on the lowercased name.
    """
    lowered = name.lower()
    return lowered.startswith("npm_config_") and lowered.endswith("registry")


def ts_fixture_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """The environment a TypeScript lock step and its version probe run under.

    `_fixture_env`'s removals first, since the generator still runs under
    `uv run`. Then every registry override is removed and the public registry
    set, so each lockfile's `resolved` URLs name a host every reader can reach.
    Corepack is told neither to prompt before fetching the pinned pnpm, which
    would hang a build with no terminal, nor to write a `packageManager` pin of
    its own into a manifest, which would dirty the tree it is locking.
    """
    env = _fixture_env(base)
    for name in [n for n in env if _is_registry_setting(n)]:
        del env[name]
    env["npm_config_registry"] = PUBLIC_NPM_REGISTRY
    env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] = "0"
    env["COREPACK_ENABLE_AUTO_PIN"] = "0"
    return env


def lock_env(partition: str, base: Mapping[str, str] | None = None) -> dict[str, str]:
    """The environment this partition's lock step runs under."""
    if lang_of(partition) == "typescript":
        return ts_fixture_env(base)
    return _fixture_env(base)


def _output_block(label: str, stream: str) -> str:
    """One labelled stream for a failure message, or nothing when it is empty.

    A bare `stderr:` header over nothing reads as a tool that failed silently,
    which is a different diagnosis from the tool that reported on the other
    stream - so an empty stream contributes no header at all.
    """
    stripped = stream.strip()
    return f"\n{label}:\n{stripped}" if stripped else ""


def _run(
    command: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None
) -> str:
    """Run one command in a fixture tree, or raise naming it and its output.

    Nothing here swallows a failure: a lock step that errored and was ignored
    produces a tree that looks built and carries no resolution, which is
    indistinguishable at review from a partition whose manager has no lock.

    Both streams reach the message. Poetry and pipenv report much of a failed
    resolution on stdout, so a message carrying stderr alone drops the part that
    says what went wrong.
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
            f"{completed.returncode}"
            + _output_block("stdout", completed.stdout)
            + _output_block("stderr", completed.stderr)
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
        raise RuntimeError("uv is not on PATH; every Python partition's build needs it")
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
    if root.name != partition or not (root / FIXTURE_README).exists():
        raise RuntimeError(
            f"{root} exists and was not written by this generator "
            f"(expected a directory named {partition!r} carrying {FIXTURE_README}); "
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


def build(
    partition: str,
    root: Path,
    uv_version: str | None = None,
    *,
    probe: Callable[[Sequence[str], Path, Mapping[str, str]], str] | None = None,
) -> dict[str, str]:
    """Write, commit and lock one partition. Returns a summary of what it did.

    Args:
        partition: One of `PARTITIONS` or `TS_PARTITIONS`.
        root: The directory to build in. Replaced if a previous build of this
            same partition is there, refused if anything else is.
        uv_version: The host uv version to record on a Python partition;
            measured when omitted, and unused on a TypeScript one.
        probe: How a TypeScript partition's manager version is read, before
            anything is written; `_probe` when omitted. The build is refused
            when the version it returns differs from the partition's pin.

    Returns:
        A mapping of partition, root and tracked file count, each as a string,
        for the caller to print or assert on. No dirty count: the build refuses
        to return at all from a dirty tree, so a number here could only ever be
        zero and would read as a property somebody checked.
    """
    if lang_of(partition) == "typescript":
        version = measure_manager_version(partition, probe or _probe)
    else:
        version = uv_version if uv_version is not None else _measure_uv_version()
    _clear(root, partition)
    root.mkdir(parents=True)

    files = plan_tree(partition)
    _write_tree(root, files)
    (root / FIXTURE_README).write_text(fixture_readme(partition, version))

    _git(root, "init", "--quiet", "--initial-branch", "main")
    _stage(root, [*sorted(files), FIXTURE_README])
    _git(
        root, "commit", "--quiet", "-m", f"Seeded fixture source, {partition} manifests"
    )

    for command in prelock_commands(partition):
        _run(command, root, env=lock_env(partition))
    if lock_command(partition):
        _run(lock_command(partition), root, env=lock_env(partition))
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
    tracked = sorted(_git(root, "ls-files").splitlines())
    for name in discard_after_lock(partition):
        if name in tracked:
            raise RuntimeError(
                f"{name} was discarded from the {partition!r} tree and is tracked "
                "anyway; the staging list this build committed from grew to include "
                "an artifact this partition exists to leave out"
            )
    expected = list(committed_files(partition))
    if tracked != expected:
        raise RuntimeError(
            f"the {partition!r} tree committed a different set of files than planned"
            f"\nunplanned: {sorted(set(tracked) - set(expected))}"
            f"\nmissing: {sorted(set(expected) - set(tracked))}"
        )
    return {
        "partition": partition,
        "root": str(root),
        "tracked": str(len(tracked)),
    }


def main(argv: list[str] | None = None) -> int:
    """Build the requested partitions.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `0` when every requested partition built.
    """
    parser = argparse.ArgumentParser(
        description="Write the seeded Python and TypeScript fixture partitions."
    )
    parser.add_argument(
        "partitions",
        nargs="*",
        choices=[*PARTITIONS, *TS_PARTITIONS],
        help="partitions to build; omit and pass --all for every one",
    )
    parser.add_argument(
        "--all", action="store_true", help="build every partition of both languages"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "where the trees go, for every requested partition (default: "
            f"{DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)} for Python and "
            f"{TS_DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)} for TypeScript, "
            "under the repository)"
        ),
    )
    args = parser.parse_args(argv)

    requested = (*PARTITIONS, *TS_PARTITIONS) if args.all else tuple(args.partitions)
    if not requested:
        parser.error("name at least one partition, or pass --all")

    # uv is measured only where a Python partition will record it, so a
    # TypeScript-only build does not fail on a host uv it never uses.
    wants_python = any(lang_of(p) == "python" for p in requested)
    uv_version = _measure_uv_version() if wants_python else None
    for partition in requested:
        base = args.output_dir or DEFAULT_OUTPUT_DIRS[lang_of(partition)]
        summary = build(partition, base / partition, uv_version)
        print(
            f"{summary['partition']}: {summary['tracked']} tracked files "
            f"in {summary['root']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
