"""Keep the `deptry` gate configured, wired and capable of failing (#14).

`deps/hygiene` prescribes `deptry` and nothing in this repository ran it until
this gate existed, which is why this repository shipped its own undeclared
`markdown` import: the check was right, the tooling was right, and the tool
only ran when a human invoked the skill.

Three things can rot, and none of them is visible by reading the config:

- **The first-party list falls behind `scripts/`.** Every module there is
  first-party by construction and they import each other as top-level names,
  so a new script that a sibling imports fails CI as a missing dependency.
  Held against the directory rather than against the four names that tripped
  the rule when the list was written.
- **The workflow stops invoking it.** A configuration nothing runs is the
  state #14 exists to end, and it looks identical to a working one.
- **The gate is configured into silence.** `known_first_party` widened until
  it swallows a real third-party name leaves `deptry` green on a project with
  a genuine missing dependency, which is how a gate like this dies. The
  equality check above is what catches that, not the non-vacuity check below:
  an exempted name is one that matches no module in `scripts/`. The
  non-vacuity check only sees it for the one dependency it removes.

The last is #14's third acceptance criterion - "undeclare a dependency, watch
CI fail, restore" - as a test rather than as a thing done once on one commit.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SCRIPTS = REPO_ROOT / "scripts"

# The dependency the non-vacuity check removes. `markdown` is the one this
# repository actually shipped undeclared, and `render_handbook_artifact.py`
# imports it lazily inside a function - so it also holds the finding that a
# function-level import is not a blind spot for this tool.
UNDECLARED_UNDER_TEST = "markdown"


@pytest.fixture(scope="module", autouse=True)
def _deptry_is_installed() -> None:
    """Fail once, clearly, when the tool itself is missing.

    Four of the tests below shell out to `deptry`, and without it they fail
    with messages about a shipping check record or about this branch's own
    invariants - sending a maintainer to edit prose when the cause is an
    uninstalled tool. Module-scoped so that says itself once rather than
    once per test. Not `importorskip`: skipping would leave the gate
    unenforced and green, which is the state #14 exists to end.
    """
    if importlib.util.find_spec("deptry") is None:
        pytest.fail(
            "deptry is not importable, so none of the checks in this module "
            "mean anything. It is declared in the dev dependency group; run "
            "`uv sync --group dev`"
        )


def _config() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _known_first_party() -> set[str]:
    return set(_config()["tool"]["deptry"]["known_first_party"])


def _script_modules() -> set[str]:
    return {path.stem for path in SCRIPTS.glob("*.py")}


def test_the_first_party_list_is_the_scripts_directory() -> None:
    """Equality, not containment, in both directions for different reasons.

    A module in `scripts/` missing from the list is a sibling import away from
    failing CI as a missing dependency. A name in the list matching no module
    is either a script that was renamed - leaving the real one uncovered - or
    a third-party package quietly exempted from the gate, which is the way
    this check gets configured into silence.
    """
    listed, actual = _known_first_party(), _script_modules()
    assert listed == actual, (
        f"[tool.deptry] known_first_party lists {sorted(listed)} and scripts/ "
        f"holds {sorted(actual)}. Missing from the list: "
        f"{sorted(actual - listed)}; listed but not a script: "
        f"{sorted(listed - actual)}. Every module in scripts/ is first-party "
        "by construction, so the list is the directory"
    )


def test_the_scripts_directory_is_not_empty() -> None:
    """The comparison above passes on two empty sets."""
    assert len(_script_modules()) > 1, (
        f"found {len(_script_modules())} module(s) in {SCRIPTS}; the "
        "first-party check compares two sets and agreeing on nothing is not "
        "agreement"
    )


def test_deptry_is_declared_rather_than_fetched_at_run_time() -> None:
    """The gate's version comes from the lockfile, not from the index.

    `uv run --with deptry` also works and resolves the tool afresh on every
    run, so the gate would drift with whatever the index serves - the same
    objection the runner rule makes to fetching a tool a project could
    declare.
    """
    dev = _config()["dependency-groups"]["dev"]
    assert any(
        entry.split(">")[0].split("=")[0].strip() == "deptry" for entry in dev
    ), f"deptry is not in the dev dependency group: {dev}"


def test_the_workflow_runs_deptry() -> None:
    """A configuration nothing invokes is the state #14 exists to end.

    Matched on the command rather than on the step's name, because renaming a
    step is cosmetic and deleting the `run` line is the defect.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "deptry" in text, f"{WORKFLOW.name} does not mention deptry at all"
    assert re.search(r"run:\s*uv run deptry \.", text), (
        f"{WORKFLOW.name} does not run `uv run deptry .`. The config can be "
        "perfect and the gate still never fire; that is the shape this test "
        "exists to catch"
    )


def _deptry(root: str, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run `deptry` over `root` with `cwd` as the working directory.

    Both arguments matter, and in two different ways that the tests below pin
    separately. `ROOT` chooses the files to scan while the dependency
    definitions come from the configuration discovered at `cwd`, so pointing
    the two at different projects reports a clean target. And `ROOT` is
    matched against deptry's exclude patterns as written, so an absolute path
    fails to match the default `tests` pattern and pulls the test suite into
    the scan.

    `root` is a string rather than a `Path` so a caller can pass `"."` - which
    is what the CI step runs, and what keeps both traps shut.
    """
    return subprocess.run(
        [sys.executable, "-m", "deptry", "--no-ansi", root],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


@pytest.fixture
def project_with_an_undeclared_import(tmp_path: Path) -> Path:
    """A copy of this project with one declared dependency removed.

    A copy rather than an edit in place: the alternative is mutating this
    repository's own `pyproject.toml` while the suite runs, which a failure
    partway through would leave behind.
    """
    shutil.copytree(SCRIPTS, tmp_path / "scripts")
    original = PYPROJECT.read_text(encoding="utf-8")
    stripped = re.sub(rf'"{UNDECLARED_UNDER_TEST}[^"]*",?\s*', "", original, count=1)
    assert stripped != original, (
        f"{UNDECLARED_UNDER_TEST!r} is no longer a declared dependency of this "
        "project, so removing it proves nothing. Point "
        "UNDECLARED_UNDER_TEST at a dependency the code imports"
    )
    (tmp_path / "pyproject.toml").write_text(stripped, encoding="utf-8")
    return tmp_path


def test_the_gate_fails_on_an_undeclared_import(
    project_with_an_undeclared_import: Path,
) -> None:
    """#14's third criterion, run on every push instead of once.

    Undeclare a dependency the code imports and `deptry` must both exit
    non-zero and name the module. Exit code alone would pass on a tool that
    crashed, and the module name alone would pass on a tool that reported it
    as something harmless.

    Which code it reports is deliberately not asserted. Removing the
    declaration from a copy leaves the dependency installed in the
    environment running this suite, so the finding comes back as
    `DEP003 ... transitive dependency` rather than the `DEP001 ... missing`
    that the same edit produces where it is not installed. Both are the gate
    firing; pinning either would make this test a claim about the caller's
    environment.
    """
    copy = project_with_an_undeclared_import
    result = _deptry(".", cwd=copy)
    output = result.stdout + result.stderr
    assert result.returncode != 0, (
        f"deptry exited 0 on a project missing {UNDECLARED_UNDER_TEST!r}, so "
        f"the CI gate would be green on it. Output:\n{output}"
    )
    assert UNDECLARED_UNDER_TEST in output, (
        f"deptry failed but never named {UNDECLARED_UNDER_TEST!r}, so the "
        f"failure is not the one this gate is for. Output:\n{output}"
    )


def test_the_gate_is_clean_on_this_project() -> None:
    """The other half: it fails on a defect and passes on this tree.

    Without this, the test above is satisfied by a tool that fails on
    everything, and the CI step would be red on `main`.
    """
    result = _deptry(".", cwd=REPO_ROOT)
    assert result.returncode == 0, (
        "deptry reports issues in this project, so the CI gate added by #14 "
        f"is red on this branch:\n{result.stdout + result.stderr}"
    )


def test_a_scan_root_without_its_own_config_reports_a_false_clean(
    project_with_an_undeclared_import: Path,
) -> None:
    """The trap `deps/hygiene` now records, held as a test so it stays true.

    `ROOT` selects the files; the dependency definitions come from the config
    discovered at the working directory. So `deptry <target>` run from
    somewhere else scans the target's source against the *caller's*
    dependencies - and on a target with a genuine missing dependency it prints
    "Success! No dependency issues found." and exits 0.

    That is worse than a tool that cannot run: an audit reports a pass. This
    test pins the behaviour rather than the wording, so if a later `deptry`
    resolves the config from `ROOT` instead, it fails here and the record's
    clause gets re-read rather than silently outliving the trap.
    """
    misdirected = _deptry(str(project_with_an_undeclared_import), cwd=REPO_ROOT)
    assert misdirected.returncode == 0, (
        "deptry no longer reports a false clean when ROOT and the working "
        "directory name different projects. Re-read deps/hygiene's note: the "
        "clause about passing --config, and alone_insufficient, both rest on "
        f"this.\n{misdirected.stdout + misdirected.stderr}"
    )
    pointed = subprocess.run(
        [
            sys.executable,
            "-m",
            "deptry",
            "--no-ansi",
            str(project_with_an_undeclared_import),
            "--config",
            str(project_with_an_undeclared_import / "pyproject.toml"),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert pointed.returncode != 0, (
        "pointing --config at the target's own pyproject.toml did not surface "
        f"the missing dependency:\n{pointed.stdout + pointed.stderr}"
    )
    assert UNDECLARED_UNDER_TEST in pointed.stdout + pointed.stderr


def test_any_scan_root_but_dot_loses_the_default_excludes(tmp_path: Path) -> None:
    """The other half of the same trap, and it points the opposite way.

    deptry matches its exclude patterns against the path as it appears,
    anchored at the start, and the default patterns are relative (`tests`,
    `venv`, `\\.venv`). So `deptry .` excludes `tests/` and any other spelling
    of the same root does not - same project, same config, a different set of
    files scanned.

    **Absoluteness is not the trigger**, which is worth pinning because it is
    the obvious wrong reading: a plain relative sibling path loses the
    excludes too, since it also puts a prefix in front of every path. Both
    spellings are checked here so the record's claim cannot decay into the
    narrower one.

    Here that surfaces as `pytest` reported as a misplaced dev dependency once
    per test module: deptry is reading the suite as production code, which is
    exactly what the default exclude prevents. So an auditor who points the
    tool at an absolute target path gets findings about the target's tests
    that are artifacts of the invocation, on top of the false clean the test
    above describes.

    Pinned because it is invisible: both invocations look like "run deptry on
    this project", one of them is green, and neither says which files it
    chose without `-v`.
    """
    relative = _deptry(".", cwd=REPO_ROOT)
    absolute = _deptry(str(REPO_ROOT), cwd=REPO_ROOT)
    assert relative.returncode == 0, (
        "the `.` invocation is not clean, so this test cannot show a "
        f"difference:\n{relative.stdout + relative.stderr}"
    )
    assert absolute.returncode != 0, (
        "an absolute scan root no longer pulls tests/ into the scan, so "
        "deptry's exclude matching has changed. Re-read deps/hygiene's note "
        "and the CI step's comment, which both rest on this"
    )
    output = absolute.stdout + absolute.stderr
    assert "DEP004" in output and "pytest" in output, (
        "the absolute invocation failed for some other reason than the test "
        f"suite being scanned:\n{output}"
    )

    # The same root written as a relative sibling, to show the mechanism is
    # the prefix rather than the leading slash.
    parent = tmp_path / "parent"
    (parent / REPO_ROOT.name).mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "scripts", parent / REPO_ROOT.name / "scripts")
    shutil.copytree(REPO_ROOT / "tests", parent / REPO_ROOT.name / "tests")
    shutil.copy(PYPROJECT, parent / REPO_ROOT.name / "pyproject.toml")
    shutil.copy(PYPROJECT, parent / "pyproject.toml")
    sibling = _deptry(REPO_ROOT.name, cwd=parent)
    assert sibling.returncode != 0, (
        "a relative sibling root kept the default excludes, so the trap is "
        "about absolute paths after all and both the record's wording and "
        f"this test's name are wrong:\n{sibling.stdout + sibling.stderr}"
    )
