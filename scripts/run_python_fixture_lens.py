"""Run every `python:` tooling entry against the seeded fixtures (#45).

The table below holds **each check record's prescribed invocation verbatim**,
keyed by the (check, tool) pair, with the record's own sentence quoted beside
it. That is the mechanism rather than the decoration: somebody running these by
hand repairs a broken command as they go and the repair never reaches the
record, whereas here the deviation needed to make a tool work is a diff against
the transcription. So `argv` is what the record says, `completion` is what had
to be added for the command to run at all, and `note` says why - and the set of
entries carrying a completion is a finding list before any tool has spoken.

Three fields are derived from the records rather than transcribed, because a
second copy of a fact the records already state is a copy free to drift:

* the grant tier, read per (check, tool) out of the record's own `needs`;
* which checks a partition runs, read out of `expectations_for`, so the harness
  cannot run a set the published record does not grade;
* which tools exist at all, read out of every record's `tooling.python`, which
  is what the exact-set guard in the tests compares the table against.

`classify` maps one observation into the engine's vocabulary and never leaves
it. **A non-zero exit is not a tool failure by itself**: bandit, ruff, deptry,
pip-audit and a shuffled pytest all exit non-zero precisely when they find what
this fixture planted, so the failure signal is a non-zero exit with nothing on
stdout - a tool that ran and produced no report.

Nothing here writes into a fixture tree. Every run happens in a copy made in a
scratch directory that does not resolve under the fixture root, because a tool
that writes only a cache still writes: ruff leaves `.ruff_cache`, pytest leaves
`.pytest_cache` and `__pycache__`, coverage leaves `.coverage`, and each of
those dirties a tree whose `git status --porcelain` being empty is how a run
proves it read without writing. The results file goes beside the partitions
rather than inside one, for the same reason.

Usage:
    uv run python scripts/run_python_fixture_lens.py uv --grant target-execution
    uv run python scripts/run_python_fixture_lens.py pip --grant none
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_checks import SKILLS_DIR, load_checks
from build_python_fixtures import DEFAULT_OUTPUT_DIR
from python_fixture_spec import (
    ISOLATION_TIMEOUT_SECONDS,
    PACKAGE,
    PARTITIONS,
    expectations_for,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Where `build_python_fixtures.py` writes the partitions, and where the results
# go - beside them, never inside one. Taken from the generator rather than
# spelled again here, so a caller moving the fixtures moves both.
FIXTURE_ROOT = DEFAULT_OUTPUT_DIR
RESULTS_DIRNAME = "results"

# The engine's scale, from `audit-core`. It does not grow: a fourth status would
# collapse a distinction the engine draws on purpose, and the round exists to
# test the family against this vocabulary rather than to extend it.
STATUSES = ("ok", "no-evidence", "not-applicable")
REASONS = ("not-permitted", "tool-unavailable", "tool-failed")

# The two grant states every entry is run under. `target-execution` implies
# `resolved-tree`, so the granted run holds both and the ungranted run holds
# neither; the middle state is not a third run, it is what the tiers distinguish
# inside these two.
GRANTS = ("none", "target-execution")

# What has to be installed for a tool whose own name is not enough. Harness
# plumbing rather than a claim from any record, and a tool absent from here is
# fetched under its own name.
#
# Two things put an entry here. `coverage.py` is the project's own name for a
# distribution published as `coverage`. And **the fixture declares no pytest**,
# so a route whose transcribed command runs the target's suite has to bring one:
# `coverage run -m pytest` and `mutmut run` both die on `No module named pytest`
# otherwise, which reads as a tool that failed rather than as a package nobody
# installed - a failure this harness would have invented, on an entry the record
# had right. The pytest plugins need no entry because each depends on pytest
# already, so naming the plugin brings the runner with it.
TOOL_PACKAGES = {
    "coverage.py": ("coverage", "pytest"),
    "mutmut": ("mutmut", "pytest"),
}

# How each partition's tree is materialized, verified end to end when the
# partitions were built. The seeded package is src-layout, so every route
# installs the project and not only its dependencies: a dependency-only install
# leaves `import fixture_app` raising `ModuleNotFoundError`, which reads as a
# broken fixture rather than as an incomplete install.
MATERIALIZE: dict[str, tuple[tuple[str, ...], ...]] = {
    "uv": (("uv", "sync"),),
    "pip": (
        ("python", "-m", "venv", ".venv"),
        (".venv/bin/pip", "install", "-r", "requirements.txt"),
        (".venv/bin/pip", "install", "-e", ".", "--no-deps"),
    ),
    "poetry": (("poetry", "install"),),
    "pipenv": (
        ("pipenv", "install"),
        ("pipenv", "run", "pip", "install", "-e", ".", "--no-deps"),
    ),
    "pylock": (
        # The environment is named rather than defaulted, so that the directory
        # the launcher puts on `PATH` is the one this command wrote instead of
        # whichever one uv would have picked.
        ("uv", "venv", ".venv"),
        ("uv", "pip", "install", "-r", "pylock.toml"),
        ("uv", "pip", "install", "-e", ".", "--no-deps"),
    ),
}


@dataclass(frozen=True)
class Invocation:
    """One check record's prescribed way of running one tool.

    Args:
        check: The record's id, `<domain>/<slug>`.
        tool: A name from that record's `tooling.python`.
        argv: The command **as the record writes it**. Empty where the record
            names the tool without prescribing a command - a library, a reading
            pass, or a route conditional on a config file the fixture does not
            carry. An empty `argv` is a fact about the record, not a gap here.
        argv_by_partition: Where the record prescribes a different command per
            partition - `cyclonedx-py`'s subcommand "matching the partition's
            own dependency file", `pip-audit`'s mode - the command for each,
            still verbatim, as `(partition, argv)` pairs. A partition paired
            with `()` is one the record prescribes no route for at all. Pairs
            rather than a mapping so that the whole entry is hashable, which is
            what freezing it is otherwise promising.
        completion: What had to be added to `argv` for the command to run.
            Recorded separately rather than folded in, because this is the
            round's output: a record whose command needs completing is a record
            to correct, and folding the completion into `argv` would report a
            repaired command as a clean run.
        then: A second command the record prescribes in sequence, where it does -
            `coverage run -m pytest` followed by `coverage report --show-missing`
            is one route, not two, and dropping the half that prints the report
            would leave the route looking like a tool that produced nothing.
        note: Why the completion was needed, or what the transcription found
            missing. Required whenever `completion` is non-empty.
        in_env: Whether the tool has to run from inside the materialized
            environment rather than through a one-shot runner.
        record_quote: A sentence occurring **exactly once** in the record, taken
            by reading it. This is what the verbatim guard compares, so it is
            the half that fails when a record's prescription changes under the
            table.
    """

    check: str
    tool: str
    record_quote: str
    argv: tuple[str, ...] = ()
    argv_by_partition: tuple[tuple[str, tuple[str, ...]], ...] = ()
    completion: tuple[str, ...] = ()
    then: tuple[str, ...] = ()
    note: str = ""
    in_env: bool = False

    def __post_init__(self) -> None:
        if self.completion and not self.note:
            raise ValueError(
                f"{self.check}/{self.tool}: a completion needs a note saying why it "
                "was needed; an unexplained completion reports a repaired command "
                "as a clean run"
            )
        if self.argv and self.argv_by_partition:
            raise ValueError(
                f"{self.check}/{self.tool}: has both a shared argv and a per-partition "
                "one, so which the run used would depend on reading this file"
            )
        named = [p for p, _ in self.argv_by_partition]
        if len(named) != len(set(named)):
            raise ValueError(
                f"{self.check}/{self.tool}: names a partition twice in "
                f"argv_by_partition ({named}), so one of the two never runs"
            )

    def prescribed(self, partition: str) -> tuple[str, ...]:
        """The record's own command for this partition, before any completion."""
        if not self.argv_by_partition:
            return self.argv
        return dict(self.argv_by_partition).get(partition, ())


def argv_for(invocation: Invocation, partition: str) -> tuple[str, ...]:
    """The command this entry runs on one partition, completion included.

    Returns `()` where the record prescribes no command, which is a reading pass
    rather than a failure - the caller records it as such instead of running
    nothing and blaming a tool.
    """
    if partition not in PARTITIONS:
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {PARTITIONS}"
        )
    base = invocation.prescribed(partition)
    if not base:
        return ()
    return base + invocation.completion


# The transcription. One entry per (check, tool) pair, because a tool answering
# several checks needs a different invocation for each: ruff selects `C901` for
# `arch/complexity`, the `S` ruleset for the four `security` checks and the `D`
# ruleset for `docs/docstring-coverage`, and collapsing those into one entry
# would test one rule selection and report it as six.
INVOCATIONS: tuple[Invocation, ...] = (
    # --- arch ---------------------------------------------------------------
    Invocation(
        check="arch/complexity-gate",
        tool="ruff",
        record_quote=(
            "`C901` needs `mccabe` max-complexity set in `pyproject.toml`; if it is "
            "unset, passing a threshold on the command line yields clean numbers and "
            "silently hides the gap."
        ),
        note=(
            "the record prescribes reading the project's configured threshold rather "
            "than running a tool, so there is no command to transcribe: running one "
            "measures code against a threshold, which is arch/complexity's question"
        ),
    ),
    Invocation(
        check="arch/complexity-gate",
        tool="radon",
        record_quote=(
            "Whichever tool you run, record what the project itself enforces - a "
            "number it never configured is a number nothing holds it to."
        ),
        note="the record prescribes no radon command for the gate question",
    ),
    Invocation(
        check="arch/complexity-gate",
        tool="xenon",
        record_quote=(
            "**Read the project's configured threshold before measuring, and treat "
            "its absence as a finding in its own right.**"
        ),
        note="the record prescribes no xenon command for the gate question",
    ),
    Invocation(
        check="arch/complexity",
        tool="ruff",
        argv=("ruff", "check", "--select", "C901"),
        record_quote=(
            "`ruff check --select C901` or `radon cc` / `xenon`. Capture the metric "
            "per function."
        ),
    ),
    Invocation(
        check="arch/complexity",
        tool="radon",
        argv=("radon", "cc"),
        completion=("src",),
        note=(
            "`radon cc` takes a path and the record names none; ruff defaults to the "
            "working directory and radon does not, so the same sentence is runnable "
            "for one tool and not the other"
        ),
        record_quote=(
            "`ruff check --select C901` or `radon cc` / `xenon`. Capture the metric "
            "per function."
        ),
    ),
    Invocation(
        check="arch/complexity",
        tool="xenon",
        argv=("xenon",),
        completion=("--max-absolute", "B", "src"),
        note=(
            "the record names the tool and no arguments; xenon needs both a threshold "
            "and a path, and the expectation is written against `--max-absolute B`"
        ),
        record_quote=(
            "`ruff check --select C901` or `radon cc` / `xenon`. Capture the metric "
            "per function."
        ),
    ),
    Invocation(
        check="arch/coupling",
        tool="grimp",
        record_quote=(
            "compute afferent/efferent counts per module from the same edge set; flag "
            "the top hubs."
        ),
        note=(
            "grimp is a library the record asks to be computed with rather than a "
            "command, so the answer comes from a scripted pass over the built graph"
        ),
    ),
    Invocation(
        check="arch/coupling",
        tool="pydeps",
        record_quote="`pydeps` gives a visual; the counts are the evidence.",
        note=(
            "the record offers pydeps for a picture and says the counts are the "
            "evidence, so it prescribes no pydeps command for this check"
        ),
    ),
    Invocation(
        check="arch/cycles",
        tool="import-linter",
        record_quote=(
            "`import-linter`'s cycle contract, `pydeps --show-cycles`, or `grimp`'s "
            "cycle detection on the built graph."
        ),
        note=(
            "the contract is the input and the fixture carries none; writing one to "
            "make the tool run would manufacture the configuration whose absence is "
            "what the run is meant to observe"
        ),
    ),
    Invocation(
        check="arch/cycles",
        tool="pydeps",
        argv=("pydeps", "--show-cycles"),
        completion=(f"src/{PACKAGE}",),
        note="pydeps takes the package to graph and the record names none",
        record_quote=(
            "`import-linter`'s cycle contract, `pydeps --show-cycles`, or `grimp`'s "
            "cycle detection on the built graph."
        ),
    ),
    Invocation(
        check="arch/cycles",
        tool="grimp",
        record_quote=(
            "`pydeps` doesn't execute the target - it reads import opcodes from "
            "compiled bytecode - but it only sees modules the import machinery can "
            "find, so an uninstalled dependency drops out of the graph and a cycle "
            "running through it goes silently unreported rather than erroring."
        ),
        note="grimp's cycle detection runs on a graph a scripted pass builds",
    ),
    Invocation(
        check="arch/dead-code",
        tool="vulture",
        argv=("vulture",),
        completion=("src", "tests"),
        note=(
            "vulture takes the paths to scan and the record names none; both trees are "
            "passed because a symbol referenced only by a test is not dead, and "
            "scanning src alone would report the suite's own callees as unused"
        ),
        record_quote=(
            "`vulture` (note its confidence score - it has false positives on "
            "framework hooks, dynamic dispatch, and re-exports; verify before "
            "deleting)."
        ),
    ),
    Invocation(
        check="arch/hidden-coupling",
        tool="grimp",
        record_quote=(
            "the import graph won't show this, so grep the AST for the tells and read "
            "each hit."
        ),
        note=(
            "the record names grimp in its tooling and then says the import graph "
            "cannot answer this check, so the prescription is a grep-and-read pass "
            "rather than a grimp command"
        ),
    ),
    Invocation(
        check="arch/layering",
        tool="import-linter",
        record_quote="`import-linter` if a `.importlinter` contract exists, or `tach`.",
        note=(
            "conditional on a contract the fixture does not carry, so the record "
            "prescribes no command here"
        ),
    ),
    Invocation(
        check="arch/layering",
        tool="tach",
        record_quote=(
            "If neither, build the ground-truth edge set yourself - parse each "
            "module's `import` / `from ... import` statements (`grimp`, or an "
            "AST/`ast`-based walk, or a scoped grep) and check every cross-tier edge "
            "against the declared rules."
        ),
        note=(
            "tach is offered as the alternative to a contract and the record names no "
            "tach command; its own configuration is absent from the fixture too"
        ),
    ),
    Invocation(
        check="arch/layering",
        tool="grimp",
        record_quote="Record the offending `file:line` for each violation.",
        note="grimp builds the edge set the record asks to be walked",
    ),
    Invocation(
        check="arch/martin-metrics",
        tool="grimp",
        record_quote=(
            "Record `Ca`, `Ce`, `I`, `A` and `D` per package; `D` is the evidence."
        ),
        note="the metrics are computed from the graph rather than reported by a command",
    ),
    Invocation(
        check="arch/over-abstraction",
        tool="grimp",
        record_quote=(
            "For each single-function module or one-method wrapper class, count call "
            "sites (`grimp` refs or a scoped grep); **one** is the trigger."
        ),
        note="grimp refs are counted from the built graph rather than from a command",
    ),
    Invocation(
        check="arch/over-abstraction",
        tool="ruff",
        record_quote=(
            "the signal is *fan-in to an abstraction*, computed from the same edge/AST "
            "set built for layering."
        ),
        note=(
            "this record lists ruff in `tooling.python` and its fallback never names "
            "it, so there is no prescribed invocation to transcribe - which is a "
            "finding about the record rather than about the tool"
        ),
    ),
    Invocation(
        check="arch/over-decomposition",
        tool="grimp",
        record_quote=(
            "Record the ratio / the count of trivial nodes / the offending chain as "
            "the evidence."
        ),
        note="the shape is computed from the same edge set rather than by a command",
    ),
    # --- deps ---------------------------------------------------------------
    Invocation(
        check="deps/freshness",
        tool="uv",
        argv=("uv", "pip", "list", "--outdated"),
        in_env=True,
        record_quote=(
            "`uv pip list --outdated` / `pip list --outdated`, both of which read the "
            "installed environment rather than the lockfile, so they need the tree "
            "resolved."
        ),
    ),
    Invocation(
        check="deps/freshness",
        tool="pip",
        argv=("pip", "list", "--outdated"),
        in_env=True,
        record_quote=(
            "Two things survive without one: the lockfile scan for floating direct "
            "pins, and the per-package registry comparison this record's "
            "`ungranted_note` sets out, which answers outdated-ness and yanked-ness "
            "from the pins already in the clone."
        ),
    ),
    Invocation(
        check="deps/hygiene",
        tool="deptry",
        argv=("deptry",),
        completion=(".",),
        in_env=True,
        note=(
            "deptry takes a scan root and the record prescribes none; the answer moves "
            "with it - `deptry src` makes the package local and the self-import rows "
            "vanish - so the expectation is written against `deptry .` and the missing "
            "root is a gap in the record"
        ),
        record_quote=(
            "`deptry` reads installed distribution metadata, so it must run inside the "
            "project's own environment."
        ),
    ),
    Invocation(
        check="deps/inventory",
        tool="cyclonedx-py",
        argv_by_partition=(
            ("uv", ("uv", "export", "--format", "cyclonedx1.5", "--frozen")),
            ("pip", ("cyclonedx-py", "requirements")),
            ("poetry", ("cyclonedx-py", "poetry")),
            ("pipenv", ("cyclonedx-py", "pipenv")),
            ("pylock", ("cyclonedx-py", "requirements", "pylock.toml")),
        ),
        note=(
            "the record prescribes the subcommand 'matching the partition's own "
            "dependency file', so the command is per partition rather than shared. The "
            "`uv` row is the record's other route, the tool's native SBOM export, "
            "which is what a partition cyclonedx-py has no subcommand for is left "
            "with; the `pylock` row points the requirements subcommand at a PEP 751 "
            "file because the record names no route that reads one"
        ),
        record_quote=(
            "`cyclonedx-py`'s `requirements`, `poetry` or `pipenv` subcommand, "
            "matching the partition's own dependency file, or the tool's native SBOM "
            "export."
        ),
    ),
    Invocation(
        check="deps/licenses",
        tool="pip-licenses",
        argv=("pip-licenses",),
        in_env=True,
        record_quote=(
            "`pip-licenses` (with `--format` for SPDX-ish output), or read each "
            "installed dist's `*.dist-info/METADATA` (`License` + `Classifier: "
            "License ::`)."
        ),
    ),
    Invocation(
        check="deps/transitive-licenses",
        tool="pip-licenses",
        argv=("pip-licenses",),
        in_env=True,
        record_quote=(
            "Same tools and same precedence as `deps/licenses`, which its own fallback "
            "section states; this check differs in how far down the graph the answer "
            "has to hold, not in what produces it."
        ),
    ),
    Invocation(
        check="deps/vulnerabilities",
        tool="pip-audit",
        argv_by_partition=(
            ("uv", ()),
            ("pip", ("pip-audit", "-r", "requirements.txt")),
            ("poetry", ()),
            ("pipenv", ()),
            ("pylock", ("pip-audit", "--locked", ".")),
        ),
        note=(
            "the record makes the mode a function of what the partition locks with, "
            "and names no mode at all for a uv, poetry or pipenv tree: `--locked` "
            "reads PEP 751 and nothing else, `-r` needs a requirements file, and a "
            "bare `pip-audit` audits the environment it was launched from, which the "
            "record says not to do. `<requirements>` is a placeholder resolved to this "
            "fixture's own file"
        ),
        record_quote=(
            "Run `pip-audit` with no arguments and it audits whatever environment it "
            "was launched from, which on a foreign target is the audit environment "
            "rather than the subject - not evidence about the target at all, so don't."
        ),
    ),
    Invocation(
        check="deps/vulnerabilities",
        tool="safety",
        record_quote=(
            "It also requires authentication and is unusable in an unauthenticated "
            "audit whatever else is true, which is a separate reason from its tier."
        ),
        note=(
            "the record names safety as the alternative and prescribes no command, "
            "and says it cannot run unauthenticated whatever else is true"
        ),
    ),
    # --- docs ---------------------------------------------------------------
    Invocation(
        check="docs/docstring-coverage",
        tool="ruff",
        argv=("ruff",),
        completion=("check", "--select", "D"),
        note=(
            "the record names ruff's `D` rules rather than a command line; "
            "`ruff check --select D` is what selects them"
        ),
        record_quote=(
            "`ruff` `D` rules / `pydocstyle` / `interrogate` if present, else an "
            "AST/grep sweep."
        ),
    ),
    Invocation(
        check="docs/docstring-coverage",
        tool="pydocstyle",
        argv=("pydocstyle",),
        record_quote=(
            "Which public modules/classes/functions lack docstrings. Report per "
            "package."
        ),
    ),
    Invocation(
        check="docs/docstring-coverage",
        tool="interrogate",
        argv=("interrogate",),
        record_quote=(
            "docstring fixes **touch code**, so they are **not** docs-only - they need "
            "the normal lint/typecheck/test gate and may need the code-review gate."
        ),
        note=(
            "the record's fallback is one line naming three tools and no arguments; "
            "pydocstyle and interrogate both default to the working directory, so the "
            "bare name is runnable for them"
        ),
    ),
    # --- security -----------------------------------------------------------
    *tuple(
        entry
        for check in (
            "security/crypto",
            "security/dangerous-calls",
            "security/injection",
            "security/unsafe-io",
        )
        for entry in (
            Invocation(
                check=check,
                tool="bandit",
                argv=("bandit", "-r"),
                completion=(f"src/{PACKAGE}",),
                note=(
                    "`<pkg>` is a placeholder the record leaves to the caller; the "
                    "seeded package is at src/" + PACKAGE
                ),
                record_quote=(
                    "`bandit -r <pkg>` (captures test id like `B602`, severity, "
                    "confidence, `file:line`), or `ruff check --select S` if the "
                    "project standardizes on ruff, or `semgrep --config p/python` for "
                    "dataflow-aware rules."
                ),
            ),
            Invocation(
                check=check,
                tool="ruff",
                argv=("ruff", "check", "--select", "S"),
                record_quote=(
                    "`bandit -r <pkg>` (captures test id like `B602`, severity, "
                    "confidence, `file:line`), or `ruff check --select S` if the "
                    "project standardizes on ruff, or `semgrep --config p/python` for "
                    "dataflow-aware rules."
                ),
            ),
            Invocation(
                check=check,
                tool="semgrep",
                argv=("semgrep", "--config", "p/python"),
                record_quote=(
                    "Semgrep is a Python-registry package, so fetch it with `uvx "
                    "semgrep` or `pipx run semgrep` whatever the partition's language "
                    "is"
                ),
            ),
        )
    ),
    # --- test ---------------------------------------------------------------
    Invocation(
        check="test/coverage-reach",
        tool="pytest-cov",
        argv=("pytest", "--cov-branch", "--cov-report=term-missing"),
        completion=(f"--cov={PACKAGE}",),
        in_env=True,
        note=(
            "`<pkg>` is a placeholder the record leaves to the caller; the seeded "
            "package is " + PACKAGE
        ),
        record_quote=(
            "`pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage "
            "run -m pytest` + `coverage report --show-missing`)."
        ),
    ),
    Invocation(
        check="test/coverage-reach",
        tool="coverage.py",
        argv=("coverage", "run", "-m", "pytest"),
        then=("coverage", "report", "--show-missing"),
        in_env=True,
        record_quote=(
            "Branch coverage is the signal; capture the missing line/branch ranges per "
            "module as the evidence pointer."
        ),
        note=(
            "the record prescribes two commands in sequence for this route, so the "
            "second is held in `then` rather than dropped"
        ),
    ),
    Invocation(
        check="test/determinism",
        tool="pytest-randomly",
        argv=("pytest",),
        in_env=True,
        record_quote=(
            "run the suite in randomized order (`pytest-randomly` randomizes "
            "automatically once installed; use `--randomly-seed=<n>` to reproduce a "
            "failing order)"
        ),
    ),
    Invocation(
        check="test/determinism",
        tool="pytest-rerunfailures",
        record_quote=(
            "and, for suspected flakies, repeat runs; flag order-dependence and "
            "non-determinism."
        ),
        note=(
            "the record asks for repeat runs and names no flag, so this plugin's own "
            "`--reruns` is nowhere in the prescription"
        ),
    ),
    Invocation(
        check="test/isolation",
        tool="pytest-timeout",
        argv=("pytest", "--durations=25"),
        completion=(f"--timeout={ISOLATION_TIMEOUT_SECONDS}",),
        in_env=True,
        note=(
            "the record prescribes `--durations=25`, which is core pytest and never "
            "exercises pytest-timeout, the tool the record names; the timeout comes "
            "from the fixture's own ISOLATION_TIMEOUT_SECONDS, which the expectation "
            "is written against"
        ),
        record_quote="`pytest --durations=25` for the slowest tests; check unit tests for real I/O.",
    ),
    Invocation(
        check="test/mutation",
        tool="mutmut",
        argv=("mutmut", "run"),
        in_env=True,
        record_quote="**Python** - `mutmut run` or `cosmic-ray`.",
    ),
    Invocation(
        check="test/mutation",
        tool="cosmic-ray",
        argv=("cosmic-ray",),
        in_env=True,
        record_quote=(
            "every one of these re-runs the target's own suite once per injected "
            "mutant, so this check needs the `target-execution` grant, and it is the "
            "most expensive tool in this family to run"
        ),
        note=(
            "the record names the tool and no subcommand; cosmic-ray drives a session "
            "from a TOML config, and writing one would manufacture the input rather "
            "than transcribe the record"
        ),
    ),
    Invocation(
        check="test/property-based-gap",
        tool="hypothesis",
        record_quote=(
            "the gap is found by reading the pure functions and the tests covering "
            "them, and judging where a property would say more than a handful of "
            "examples."
        ),
        note=(
            "a library imported inside the partition's own tests rather than a runner, "
            "so the record prescribes a reading pass and no command"
        ),
    ),
)


@lru_cache(maxsize=1)
def _records() -> dict[str, object]:
    """Every check record, parsed once.

    Cached because the derivations below are called per (check, tool) pair and
    re-walking the skill tree fifty-one times is fifty-one chances for the run
    to be reading a different tree than the one it started on.
    """
    checks, errors = load_checks(SKILLS_DIR)
    if errors:
        raise RuntimeError("the check records do not load:\n" + "\n".join(errors))
    return checks


def tools_named_in_records() -> set[str]:
    """Every tool any record offers for Python.

    Read from the records rather than listed here, so a tool added to a record
    and forgotten in `INVOCATIONS` fails the exact-set guard instead of going
    unexercised behind a full-looking run.
    """
    return {
        tool
        for check in _records().values()
        for tool in check.tooling.get("python", ())
    }


def grant_tier(check: str, tool: str) -> str:
    """What this tool needs present in the target before it answers.

    Derived from the record's own `needs` rather than transcribed beside the
    invocation: a copy of a tier the record already states is a copy free to
    drift, and the drift would be invisible - a tool run under the wrong grant
    still produces output.

    Returns:
        `resolved-tree`, `target-execution`, or the empty string where the tool
        answers from a read-only clone.
    """
    checks = _records()
    if check not in checks:
        raise ValueError(f"no check record {check!r}")
    record = checks[check]
    if tool not in record.tooling.get("python", ()):
        raise ValueError(f"{check} does not offer {tool!r} for Python")
    for tier, tools in record.needs.items():
        if tool in tools:
            return tier
    return ""


def invocations_for(partition: str) -> tuple[Invocation, ...]:
    """Every invocation one partition runs.

    Scoped by the expectations rather than by a second list, so the harness
    cannot run a set the published record does not grade.
    """
    if partition not in PARTITIONS:
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {PARTITIONS}"
        )
    carried = {e.check for e in expectations_for(partition)}
    return tuple(i for i in INVOCATIONS if i.check in carried)


def packages_for(tool: str) -> tuple[str, ...]:
    """Everything that has to be installed for this tool's route to run.

    The first is the tool itself; anything after it is what the route needs
    present and the fixture does not declare.
    """
    return TOOL_PACKAGES.get(tool, (tool,))


# The partitions whose materialization route builds a `.venv` in the copy, read
# out of `MATERIALIZE` rather than listed again: a route rewritten to install
# somewhere else would otherwise leave this claiming a directory nobody wrote.
VENV_PARTITIONS = tuple(
    partition
    for partition, commands in MATERIALIZE.items()
    if any(any(".venv" in word for word in command) for command in commands)
)
VENV_BIN = ".venv/bin"


def provision_command(partition: str, package: str) -> tuple[str, ...]:
    """How one audit-owned package gets into a partition's materialized copy.

    `audit-core` bars installing into the target and prescribes a copy the check
    owns; this is that install, and it happens in the copy rather than in the
    fixture. Every tool here is one the fixture does not declare, so it is never
    evidence about the target - only the lens the target is read through.

    Returns `()` for a partition whose launcher fetches the tool per run instead.
    """
    if partition not in PARTITIONS:
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {PARTITIONS}"
        )
    match partition:
        case "poetry":
            return ("poetry", "run", "pip", "install", package)
        case "pipenv":
            return ("pipenv", "run", "pip", "install", package)
        case partition if partition in VENV_PARTITIONS:
            return (f"{VENV_BIN}/pip", "install", package)
        case _:
            # `uv run --with` provisions and runs in one step, so a separate
            # install would put the package in the project environment the
            # `deps` checks are reading.
            return ()


def launcher(
    invocation: Invocation, partition: str, *, granted: bool
) -> tuple[str, ...]:
    """The words that go in front of the command, and how the tool is obtained.

    An `in_env` tool runs from inside the materialized environment under a
    grant, because the one-shot runner's sandbox cannot see what the target
    resolved: measured on one tree, `uvx deptry` reported markupsafe as DEP001
    where deptry inside the environment reported it as DEP003, which is the
    answer the expectation claims. Grading a correct run against the other one
    would send a later pass off to "fix" a record that was right.

    Without the grant there is no environment to run inside, so the same tool
    falls back to the one-shot runner and the run records which it used.

    A `.venv` partition gets no prefix at all: its command name is not always
    its module name - `pip-licenses` imports as `piplicenses` - so `python -m`
    has nothing to hand, and the environment's own `bin` goes on `PATH` for the
    subprocess instead.
    """
    packages = packages_for(invocation.tool)
    extra = tuple(word for name in packages[1:] for word in ("--with", name))
    if not (invocation.in_env and granted):
        if packages == (invocation.tool,):
            return ("uvx",)
        return ("uvx", "--from", packages[0], *extra)
    match partition:
        case "poetry":
            return ("poetry", "run")
        case "pipenv":
            return ("pipenv", "run")
        case partition if partition in VENV_PARTITIONS:
            return ()
        case _:
            return ("uv", "run", "--with", packages[0], *extra)


def classify(
    returncode: int,
    stdout: str,
    stderr: str,
    tool_present: bool,
    *,
    permitted: bool = True,
) -> tuple[str, str]:
    """Map one observation into the engine's vocabulary.

    Pure, and it never returns a status outside `STATUSES`: the point of the
    round is that the family is tested against the engine's scale rather than
    that the scale grows to fit what came back.

    **A non-zero exit is not a failure by itself.** bandit, ruff, deptry,
    pip-audit and a shuffled pytest all exit non-zero exactly when they find
    what this fixture planted, so reading the exit code alone would grade every
    correct run as a tool defect. What distinguishes a failure is a non-zero
    exit with nothing on stdout - a tool that ran and produced no report.

    Args:
        returncode: The command's exit status.
        stdout: What it wrote to stdout.
        stderr: What it wrote to stderr, kept for the caller's record.
        tool_present: Whether the tool could be obtained at all.
        permitted: Whether the run holds the grant this tool needs.

    Returns:
        The status and its reason; the reason is empty for `ok`.
    """
    if not permitted:
        return ("no-evidence", "not-permitted")
    if not tool_present:
        return ("no-evidence", "tool-unavailable")
    if returncode == 0 or stdout.strip():
        return ("ok", "")
    del stderr  # recorded by the caller; the classification does not read it
    return ("no-evidence", "tool-failed")


def _fixture_env() -> dict[str, str]:
    """The environment a fixture subprocess runs under.

    The harness runs under `uv run`, which exports `VIRTUAL_ENV` pointing at
    this repository's environment. A package manager invoked in a fixture copy
    with that set resolves against the handbook's environment instead of the
    fixture's, and every `deps` answer would then be about this repository.
    """
    env = dict(os.environ)
    for name in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH"):
        env.pop(name, None)
    env["PIPENV_IGNORE_VIRTUALENVS"] = "1"
    return env


def _run(
    command: Sequence[str], cwd: Path, timeout: int, bin_dir: Path | None = None
) -> dict[str, object]:
    """Run one command and report what happened, distinguishing the failures.

    A tool that is missing and a tool that ran and failed are different facts -
    the engine's `tool-unavailable` and `tool-failed` depend on telling them
    apart - so `FileNotFoundError` is caught by name and reported as absence
    rather than collapsing into a non-zero exit. Nothing is swallowed: every
    other exception is reported with its type and message.

    Args:
        command: The argv to run.
        cwd: The materialized copy to run it in.
        timeout: Seconds before the command is abandoned as hung.
        bin_dir: A directory to put in front of `PATH`, for a partition whose
            environment is a plain `.venv` and whose tools are found by name.
    """
    env = _fixture_env()
    if bin_dir is not None:
        env["PATH"] = os.pathsep.join([str(bin_dir), env.get("PATH", "")])
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "tool_present": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "tool_present": True,
        }
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "tool_present": True,
    }


def reconstruct(partition: str, source: Path, work_root: Path) -> Path:
    """Copy one fixture partition somewhere it can be written to.

    The copy carries `.git`, because some tools read only tracked files and a
    copy without it would make them pass having scanned nothing.
    """
    if (
        work_root.resolve() == source.resolve()
        or source.resolve() in work_root.resolve().parents
    ):
        raise ValueError(
            f"the work directory {work_root} resolves under the fixture {source}; "
            "reconstructing inside the target is the write the read-only invariant "
            "forbids"
        )
    destination = work_root / partition
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return destination


def run_partition(
    partition: str,
    source: Path,
    work_root: Path,
    grant: str,
    timeout: int,
) -> dict[str, object]:
    """Run one partition's invocations under one grant state.

    Returns the whole observation rather than a verdict: the raw exit code,
    stdout and stderr are kept so that a later pass can re-classify without
    re-running, and so that a completion the transcription had to make is
    visible beside what it produced.
    """
    if grant not in GRANTS:
        raise ValueError(f"unknown grant {grant!r}; expected one of {GRANTS}")
    granted = grant != "none"
    copy = reconstruct(partition, source, work_root)
    materialization = []
    if granted:
        for command in MATERIALIZE[partition]:
            outcome = _run(command, copy, timeout)
            materialization.append({"command": list(command), **outcome})
            if outcome["returncode"] != 0:
                break

    rows = []
    for invocation in invocations_for(partition):
        tier = grant_tier(invocation.check, invocation.tool)
        permitted = granted or not tier
        argv = argv_for(invocation, partition)
        row: dict[str, object] = {
            "check": invocation.check,
            "tool": invocation.tool,
            "record_argv": list(invocation.prescribed(partition)),
            "completion": list(invocation.completion),
            "note": invocation.note,
            "needs": tier,
            "in_env": invocation.in_env,
        }
        if not argv:
            row |= {
                "ran": False,
                "status": "",
                "reason": "",
                "why": "the record prescribes no command for this tool",
            }
            rows.append(row)
            continue
        if not permitted:
            status, reason = classify(0, "", "", tool_present=True, permitted=False)
            row |= {"ran": False, "status": status, "reason": reason}
            rows.append(row)
            continue
        prefix = launcher(invocation, partition, granted=granted)
        bin_dir = copy / VENV_BIN if not prefix and invocation.in_env else None
        # A tool the fixture does not declare goes into the copy this run owns,
        # never into the fixture and never into the shared tree: `audit-core`
        # bars both, and a package the audit added is never evidence about the
        # target whichever tree it landed in.
        if invocation.in_env and granted:
            installs = []
            for package in packages_for(invocation.tool):
                provision = provision_command(partition, package)
                if provision:
                    installs.append(
                        {
                            "command": list(provision),
                            **_run(provision, copy, timeout, bin_dir),
                        }
                    )
            if installs:
                row["provision"] = installs
        command = (*prefix, *argv)
        outcome = _run(command, copy, timeout, bin_dir)
        status, reason = classify(
            outcome["returncode"] if outcome["returncode"] is not None else 1,
            str(outcome["stdout"]),
            str(outcome["stderr"]),
            tool_present=bool(outcome["tool_present"]),
        )
        row |= {
            "ran": True,
            "command": list(command),
            "status": status,
            "reason": reason,
            **outcome,
        }
        # A route the record writes as two commands is one route: dropping the
        # half that prints the report would record the half that produces the
        # data as a tool that answered nothing.
        if invocation.then:
            follow_up = (*prefix, *invocation.then)
            row["then"] = {
                "command": list(follow_up),
                **_run(follow_up, copy, timeout, bin_dir),
            }
        rows.append(row)

    return {
        "partition": partition,
        "grant": grant,
        "source": str(source),
        "materialization": materialization,
        "results": rows,
    }


def main(argv: list[str] | None = None) -> int:
    """Run one partition under one grant state and write the observations.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `0` once the run is written. A tool that failed is an observation rather
        than an error here: the round exists to record what came back.
    """
    parser = argparse.ArgumentParser(
        description="Run the transcribed python: invocations against one fixture."
    )
    parser.add_argument("partition", choices=list(PARTITIONS))
    parser.add_argument("--grant", choices=list(GRANTS), default="target-execution")
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=FIXTURE_ROOT,
        help="where the generated partitions are",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="scratch root for the copy; a temporary directory by default",
    )
    parser.add_argument(
        "--timeout", type=int, default=900, help="seconds per command (default: 900)"
    )
    args = parser.parse_args(argv)

    source = args.fixture_root / args.partition
    if not source.is_dir():
        parser.error(
            f"{source} is not there; build it first with build_python_fixtures"
        )

    work_root = args.work_dir or Path(tempfile.mkdtemp(prefix="python-fixture-lens-"))
    work_root.mkdir(parents=True, exist_ok=True)
    observed = run_partition(
        args.partition, source, work_root, args.grant, args.timeout
    )

    results_dir = args.fixture_root / RESULTS_DIRNAME
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / f"{args.partition}-{args.grant}.json"
    out_path.write_text(json.dumps(observed, indent=2, sort_keys=True) + "\n")
    ran = sum(1 for r in observed["results"] if r.get("ran"))
    print(f"{args.partition} ({args.grant}): {ran} commands run, written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
