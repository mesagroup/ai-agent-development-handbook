"""Run every `python:` tooling entry against the seeded fixtures (#45).

The table below holds **each check record's prescribed invocation verbatim**,
keyed by the (check, tool) pair, with the record's own sentence quoted beside
it. That is the mechanism rather than the decoration: somebody running these by
hand repairs a broken command as they go and the repair never reaches the
record, whereas here the deviation needed to make a tool work is a diff against
the transcription. So `argv` is what the record says, `completion` is what had
to be added for the command to run at all, and `note` says why - and the set of
entries carrying a completion is a finding list before any tool has spoken.

A route the record does not prescribe at all is a third thing, and it is held
apart from both: `supplied_by_partition` carries a command **this round
contributed** rather than transcribed, and it never renders as `record_argv` in
the results. They are SBOM and vulnerability routes for dependency files the
record names no subcommand or mode for, so each is a candidate answer to a named
hole rather than a correction to the record - and keeping it out of `record_argv`
is what stops a later pass reading "the harness ran this" as "the record said
this".

Three fields are derived from the records rather than transcribed, because a
second copy of a fact the records already state is a copy free to drift:

* the grant tier, read per (check, tool) out of the record's own `needs`;
* which checks a partition runs, read out of `expectations_for`, so the harness
  cannot run a set the published record does not grade;
* which tools exist at all, read out of every record's `tooling.python`, which
  is what the exact-set guard in the tests compares the table against.

`classify` maps one observation into the engine's vocabulary and never leaves
it. **A non-zero exit is not a tool failure by itself - for a tool proven
capable of a designed one**: bandit, ruff, deptry, pip-audit and a shuffled
pytest all exit non-zero precisely when they find what this fixture planted,
so for these the failure signal is a non-zero exit with nothing on the stream
that tool reports its findings on. Which stream that is varies - deptry writes
its whole report to stderr and leaves stdout empty - so it is a per-entry fact
in `findings_stream` rather than an assumption that every tool reports on
stdout. What each tool's non-zero exit *means* is itself a per-tool fact,
`NONZERO_EXIT_MEANING`, rather than a rule every tool shares: `mutmut` writes
status text to stdout on every run, failure or not, so content on a stream is
not evidence there for the reason it is for a linter - proven from `mutmut`'s
own source, not assumed, and named beside the table.

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
from build_python_fixtures import DEFAULT_OUTPUT_DIR, PINNED_MANAGERS
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

# Where a supplied route parks an intermediate it has to hand to the next step.
# Named rather than defaulted so that the file is recognisable as the harness's
# in the copy afterwards, and distinct from any manifest a partition declares -
# a step writing `requirements.txt` would overwrite the pip partition's own.
SUPPLIED_REQUIREMENTS = "audit-export-requirements.txt"

# Where every materialization route below puts the partition's own environment,
# and so what `<path-to-venv-python>` resolves to in the one command a record
# writes that placeholder into. Named here rather than beside `launcher`,
# because the transcription reads it too.
VENV_BIN = ".venv/bin"

# The engine's scale, from `audit-core`. Neither tuple grows: a fourth status
# would collapse a distinction the engine draws on purpose, and `audit-core`
# introduces the reasons as "the three ways a check can fail to run", so a
# fourth reason is a value the pass that grades this file has no row for. The
# round exists to test the family against this vocabulary rather than to extend
# it, which is why both are pinned by literal equality in the tests.
#
# Two things in this file are outside the scale on purpose. `not-applicable` is
# a status `classify` can never return: it means the check has no lens in the
# partition's language, which is settled by the record before the harness runs
# rather than by an observation. And a row for a record that prescribes no
# command carries `status: ""` - not a fourth status but the absence of one,
# because nothing ran to have a status.
STATUSES = ("ok", "no-evidence", "not-applicable")
REASONS = ("not-permitted", "tool-unavailable", "tool-failed")

# Harness-local, and deliberately a separate field from `reason` rather than
# more reasons. Both name a way a row failed to produce evidence that the
# engine's three reasons cannot tell apart on their own: a hung command reads
# exactly like a tool that ran and printed nothing, and a route whose
# environment was never built reads exactly like a tool nobody could fetch. The
# engine's reason still governs what the row *is*; the detail says which of them
# it was, so that a later pass reading this file can separate a genuine tool
# defect from the harness's own environment giving out.
DETAILS = ("timed-out", "environment-unmaterialized")

# The two grant states every entry is run under. `target-execution` implies
# `resolved-tree`, so the granted run holds both and the ungranted run holds
# neither; the middle state is not a third run, it is what the tiers distinguish
# inside these two.
GRANTS = ("none", "target-execution")

# What has to be installed for a tool whose own name is not enough. Harness
# plumbing rather than a claim from any record, and a tool absent from here is
# fetched under its own name.
#
# Three things put an entry here. `coverage.py` is the project's own name for a
# distribution published as `coverage`, and `cyclonedx-py` is the command name
# of a distribution published as `cyclonedx-bom` - naming the distribution makes
# the resolution direct instead of leaving the runner to guess from an alias.
# And **the fixture declares no pytest**,
# so a route whose transcribed command runs the target's suite has to bring one:
# `coverage run -m pytest` and `mutmut run` both die on `No module named pytest`
# otherwise, which reads as a tool that failed rather than as a package nobody
# installed - a failure this harness would have invented, on an entry the record
# had right. The pytest plugins need no entry because each depends on pytest
# already, so naming the plugin brings the runner with it.
TOOL_PACKAGES = {
    "coverage.py": ("coverage", "pytest"),
    "cyclonedx-py": ("cyclonedx-bom",),
    "mutmut": ("mutmut", "pytest"),
}

# How each partition's tree is materialized, verified end to end when the
# partitions were built. The seeded package is src-layout, so every route
# installs the project and not only its dependencies: a dependency-only install
# leaves `import fixture_app` raising `ModuleNotFoundError`, which reads as a
# broken fixture rather than as an incomplete install.
# Every route installs from the committed lock and never refreshes it. The
# distinction is not cosmetic: `uv sync` and `pipenv install` both re-resolve
# when they judge the lock stale, so without the frozen form the tools would
# observe a resolution the fixture never committed - and the build smoke that
# established the ground truth materialized with `uv sync --frozen`, so the two
# would be measuring different trees with nothing to say so. The refresh does
# not reach a fixture (materialization runs in a copy), which is why this is a
# correctness question about the observation rather than about the invariant.
# FROZEN_FORM below names what makes each route read rather than resolve.
#
# None of `python`, `poetry` or `pipenv` is a bare name this host resolves:
# only `uv` is guaranteed present, since the harness itself runs under it. So
# `poetry` and `pipenv` go through `uvx` pinned to the exact version
# `build_python_fixtures.PINNED_MANAGERS` names - the same manager that
# produced each partition's lock, materializing it, which is the property a
# drifted pin would silently lose. And the `pip` partition's venv is created
# with `uv venv --seed` rather than a bare `python -m venv`: `--seed` is chosen
# over the otherwise-equivalent system `python3 -m venv` because uv is already
# required for the harness to run at all, whereas a system `python3` varies by
# machine - a reproducibility argument, not a fidelity one. Venv creation is
# instrument scaffolding; the commands actually being measured remain the
# record's own (`.venv/bin/pip install -r requirements.txt`, `pip list
# --outdated`, and so on), and those are unchanged. What `--seed` buys here is
# a real `pip` binary at `.venv/bin/pip`, which the next two steps invoke
# directly rather than through `uv pip install` - unlike `pylock` below, whose
# steps never touch the binary and so never needed seeding.
MATERIALIZE: dict[str, tuple[tuple[str, ...], ...]] = {
    "uv": (("uv", "sync", "--frozen"),),
    "pip": (
        ("uv", "venv", "--seed", ".venv"),
        (".venv/bin/pip", "install", "-r", "requirements.txt"),
        (".venv/bin/pip", "install", "-e", ".", "--no-deps"),
    ),
    "poetry": (("uvx", PINNED_MANAGERS["poetry"], "install"),),
    "pipenv": (
        ("uvx", PINNED_MANAGERS["pipenv"], "sync"),
        (
            "uvx",
            PINNED_MANAGERS["pipenv"],
            "run",
            "pip",
            "install",
            "-e",
            ".",
            "--no-deps",
        ),
    ),
    "pylock": (
        # The environment is named rather than defaulted, so that the
        # interpreter the launcher points `--python` at is the one this
        # command wrote instead of whichever one uv would have picked. Not
        # seeded: nothing here calls `.venv/bin/pip` directly, every step is
        # `uv pip install`, which needs no pip binary inside the venv it
        # targets.
        ("uv", "venv", ".venv"),
        ("uv", "pip", "install", "-r", "pylock.toml"),
        ("uv", "pip", "install", "-e", ".", "--no-deps"),
    ),
}

# What makes each partition's route read the committed lock instead of
# resolving a new one. `pip` and `pylock` need nothing: a `requirements.txt` of
# exact pins and a `pylock.toml` are both already the resolution, so there is no
# lock for the installer to refresh. Named per partition rather than asserted as
# a blanket rule, because a route that genuinely needs no flag and one that lost
# its flag look identical in a list of commands.
FROZEN_FORM = {
    "uv": "--frozen",
    "pipenv": "sync",
    "poetry": "install",
    "pip": "",
    "pylock": "",
}

# What reports each tool's own version, appended after `launcher`'s prefix the
# same way `argv` is - so a `uvx`-fetched tool answers with the version `uvx`
# actually resolved, not a version transcribed once and left to drift. Every
# tool `INVOCATIONS` names has an entry, `None` where it does not, and `None` is
# only legal beside a reason in `NO_VERSION_ROUTE`: the same shape as
# `ungranted_note`'s `none` sentinel, and for the same reason - an omitted entry
# must never read as a silent default.
#
# `grimp` and `hypothesis` carry no `argv` anywhere in `INVOCATIONS`: the record
# asks for each as a library rather than a command, so neither's own console
# entry point (`hypothesis` needs `click`, which nothing here installs; `grimp`
# has no console entry point at all) is what the family actually runs. Their
# probes read the installed distribution's own metadata instead, and the
# `--with <pkg>` is safe to bake into the probe itself only because both tools
# are `in_env=False` everywhere they occur: `launcher` then returns bare
# `("uvx",)` on every partition and every grant, so there is no in-environment
# branch this hard-coded flag could collide with.
#
# The four pytest plugins are the same shape without the safety condition: each
# is `in_env=True`, so under a grant the tool is already present in the
# materialized environment (or added via the same `--with` `launcher` computes
# for the real check) and the bare `python -c` finds it with no flag of the
# probe's own; under no grant it resolves to a bare interpreter with nothing
# installed and the probe fails with `PackageNotFoundError`, which is recorded
# as failure text rather than dropped - an honest answer, since there is no
# environment to read the plugin's version from.
_METADATA_VERSION = "from importlib.metadata import version; print(version({0!r}))"

VERSION_PROBE: dict[str, tuple[str, ...] | None] = {
    "ruff": ("ruff", "--version"),
    "radon": ("radon", "--version"),
    "xenon": ("xenon", "--version"),
    "grimp": ("--with", "grimp", "python", "-c", _METADATA_VERSION.format("grimp")),
    "pydeps": ("pydeps", "--version"),
    "import-linter": ("import-linter", "--version"),
    "tach": ("tach", "--version"),
    "vulture": ("vulture", "--version"),
    "uv": ("uv", "--version"),
    "pip": ("pip", "--version"),
    "deptry": ("deptry", "--version"),
    "cyclonedx-py": ("cyclonedx-py", "--version"),
    "pip-licenses": ("pip-licenses", "--version"),
    "pip-audit": ("pip-audit", "--version"),
    "safety": ("safety", "--version"),
    "pydocstyle": ("pydocstyle", "--version"),
    "interrogate": ("interrogate", "--version"),
    "bandit": ("bandit", "--version"),
    "semgrep": ("semgrep", "--version"),
    "pytest-cov": ("python", "-c", _METADATA_VERSION.format("pytest-cov")),
    "coverage.py": ("coverage", "--version"),
    "pytest-randomly": ("python", "-c", _METADATA_VERSION.format("pytest-randomly")),
    "pytest-rerunfailures": (
        "python",
        "-c",
        _METADATA_VERSION.format("pytest-rerunfailures"),
    ),
    "pytest-timeout": ("python", "-c", _METADATA_VERSION.format("pytest-timeout")),
    "mutmut": ("mutmut", "--version"),
    "cosmic-ray": ("cosmic-ray", "--version"),
    "hypothesis": (
        "--with",
        "hypothesis",
        "python",
        "-c",
        _METADATA_VERSION.format("hypothesis"),
    ),
}

# Empty on purpose rather than absent: every tool `INVOCATIONS` names turned out
# to have a working route, verified by hand against the installed package and
# against the actual command `launcher` resolves for it (not just that some
# `--version` or `importlib.metadata` form exists in isolation) - so there is
# nothing here to explain. The dict stays because `probe_versions` reads it, and
# a future tool with no route at all names itself here rather than silently
# taking `None`.
NO_VERSION_ROUTE: dict[str, str] = {}

# What a declared command form is for. A disposition says what the *record* names
# a form for, and `runs` is the only value the harness acts on. Each of the other
# two says a different thing about a form the transcription did not take:
#
# * `superseded` - the record names the form and then narrows the same command,
#   the way the `--no-deps --disable-pip` pair narrows `pip-audit -r
#   <requirements>`, and the narrower form is the one it goes on to prescribe.
# * `alternative` - a second route the record keeps valid without making it the
#   default here: `cyclonedx-py environment`, more accurate where a tree is
#   available and useless on a read-only clone; `pip-licenses --format json`, the
#   same list presented machine-readably; `mutmut results`, the other of two ways
#   the record offers to read the tally; `pytest --randomly-seed=<n>`, the seeded
#   re-run the record keeps for reproducing a failing order, where the command it
#   prescribes first is `pytest` bare. Nothing narrows these and nothing warns
#   against them - the record simply prescribes something else first. Read as
#   "a route for a partition shape the fixtures lack" it fits none of them, and
#   it would make the value a claim about the fixture set rather than about the
#   record, which is the one thing a disposition never is.
#
# There is no value for a form a record names in order to warn against, and the
# reason is disposition precedence rather than anything structural. Records do
# warn against multi-token forms, and the extractor reads those spans as forms:
# `arch/cycles` names `pydeps --show-cycles` and then says that form alone has no
# textual output channel at all, and `deps/inventory` says it has no route
# through `cyclonedx-py poetry` for a PEP 621 manifest. Each still carries the
# disposition describing what the record does with it - the first is `superseded`,
# because the record narrows the same command; the second is `runs`, because the
# harness runs it on the partition whose manifest it does read. A warning is a
# reason a record gives, and every form here has some other disposition that
# already answers what the record names it for, so nothing reaches `forbidden`
# today. A record writing "never run `foo --bar`", where the harness neither runs
# that form nor narrows it, would give the value a user immediately. A value with
# no user is ceremony that reads as coverage, so this tuple holds exactly the
# values some declared form carries, and a test in the suite fails when it stops
# doing so.
#
# Naming them is the point: without a disposition, a form the harness does not
# run is indistinguishable from a form nobody noticed, which is how `--show-dot`
# sat unprescribed in `arch/cycles` through three green guards.
DISPOSITIONS: tuple[str, ...] = ("runs", "alternative", "superseded")


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
            with `()` is one this entry has no prescribed command for; where the
            round contributed a route for it anyway, that route is in
            `supplied_by_partition` rather than here. Pairs rather than a mapping
            so that the whole entry is hashable, which is what freezing it is
            otherwise promising.
        supplied_by_partition: A route **this round contributed** for a
            partition the record prescribes none for, as `(partition, steps)`
            pairs where `steps` is the sequence of commands that route runs. It
            never reaches `record_argv`, so the difference between what the
            record said and what the audit supplied stays visible in the output
            rather than depending on somebody reading this file. Each step is
            written in full, **including how it obtains its own tool**, because
            a supplied route is authored here rather than transcribed: there is
            no record naming a tool for the launcher to go and fetch, and one of
            these routes runs the target's own package manager while the next
            runs a fetched one. A partition may carry a prescribed route or a
            supplied one, never both.
        supplied_note: What the supplied route is for and why the record has
            none. Required whenever `supplied_by_partition` is non-empty, for
            the reason `note` is required beside a completion: an unexplained
            supplied route reads as a command the record prescribed.
        own_runner: The partitions whose prescribed argv is complete as written,
            so `launcher` puts nothing in front of it. A record may prescribe a
            command whose first word is a runner, or a tool other than the one
            this entry is keyed on, while `launcher` obtains the tool by the
            check's tool name rather than by the command - so without this field
            such a route has only two shapes available, and both misreport it:
            fronted by a fetch for a package the command never calls, whose
            version the row then reports as the one that answered, or demoted to
            a supplied route, which says the record prescribed nothing where it
            prescribed this. A partition named here must carry a prescribed argv
            and must not also carry a supplied route.
        completion: What had to be added to `argv` for the command to run.
            Recorded separately rather than folded in, because this is the
            round's output: a record whose command needs completing is a record
            to correct, and folding the completion into `argv` would report a
            repaired command as a clean run.
        then: A second command the record prescribes in sequence, where it does -
            `coverage run -m pytest` followed by `coverage report --show-missing`
            is one route, not two, and dropping the half that prints the report
            would leave the route looking like a tool that produced nothing.
            The order is the record's and is held against it rather than against
            a literal in the suite: the two commands concatenated trace through
            the quote in the order the record writes them, so swapping them
            fails as a reversed route rather than as a tuple somebody needs to
            update.
        note: Why the completion was needed, or what the transcription found
            missing. Required whenever `completion` is non-empty.
        in_env: Whether the tool has to run from inside the materialized
            environment rather than through a one-shot runner.
        findings_stream: Which stream this tool writes its report to, and so
            which one `classify` reads to tell a tool that answered from one
            that failed. `stdout` for all but deptry, which writes its whole
            report to stderr and leaves stdout empty - measured, and the reason
            this is a field rather than an assumption: read on stdout, a deptry
            run that finds every planted seed grades as a tool failure and one
            that finds nothing grades clean, which is the classification exactly
            inverted on the entry the fixture was seeded for.
        record_quote: The record's own **prescribing sentence** for this route,
            occurring exactly once in the record, taken by reading it. This is
            what the verbatim guard compares, so it is the half that fails when
            a record's prescription changes under the table - and it only fails
            there if it is anchored off the sentence that names the command,
            which is why the guard also holds the transcribed tokens against it.

            Where the record prescribes no command the quote is instead the
            sentence that says what it prescribes instead, and `note` says so.
            Two shapes read as oversights and are not. A quote spanning two
            adjacent sentences is one whose entry runs a command the record
            splits across both, so quoting either alone would leave half the
            prescription unwatched. And a quote naming no command at all is one
            whose record prescribes by delegating to another check's fallback
            section, which makes the delegation the prescription.
        forms: Every command form this record's prescribing paragraph names for
            this route, as `(form, disposition)` pairs, taken by reading it. The
            declaration is what the record-to-harness guards compare: the three
            older guards all run the other way, holding the transcription
            against the record, so a record that *grows* a prescription leaves
            them green while the harness quietly stops running what it says it
            runs.

            A form is not always led by this entry's tool, so the declaration is
            keyed on the route rather than on the name: the record prescribes
            `pytest --randomly-seed=<n>` for `pytest-randomly` and `uv export
            --format=cyclonedx1.5 --frozen` where `cyclonedx-py` has no uv
            subcommand, and a declaration keyed on the tool's name would hold
            nothing for either while the record went on prescribing it.

            A disposition is a claim about the record and not about this table:
            it says what the record names the form for, never whether anything
            here runs it.
            The two can still diverge, inside bounds two properties now set. A
            form declared `runs` that no argv carries fails the coverage
            property. A form the harness runs *as written* while declaring it
            `superseded` or `alternative` fails a second one, and flipping the
            last `runs` form off an entry fails a third before any argv is
            touched, which is what keeps the disposition from working as a
            per-form off-switch for the coverage property. What is left is
            narrower and stated where it is held: a non-`runs` form run as a
            strict prefix plus an unrelated token, and a disposition simply
            wrong about its record, which no extraction can read out of prose.
            `deps/vulnerabilities` is the live instance rather than the
            hypothetical one: its `pip-audit -r <requirements>` is `superseded`,
            truthfully - the record narrows it with the `--no-deps --disable-pip`
            pair - and the uv partition's supplied route runs exactly that form
            without the pair. A supplied route is authored here rather than
            transcribed, so by construction it answers to no declaration, which
            is why the two can disagree without either being wrong.
    """

    check: str
    tool: str
    record_quote: str
    argv: tuple[str, ...] = ()
    argv_by_partition: tuple[tuple[str, tuple[str, ...]], ...] = ()
    supplied_by_partition: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = ()
    supplied_note: str = ""
    own_runner: tuple[str, ...] = ()
    completion: tuple[str, ...] = ()
    then: tuple[str, ...] = ()
    note: str = ""
    in_env: bool = False
    findings_stream: str = "stdout"
    forms: tuple[tuple[str, str], ...] = ()

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
        if self.findings_stream not in ("stdout", "stderr"):
            raise ValueError(
                f"{self.check}/{self.tool}: findings_stream is "
                f"{self.findings_stream!r}; a tool reports on stdout or on stderr, "
                "and classifying on a third thing would grade every run of it"
            )
        self._check_supplied()
        self._check_own_runner()
        self._check_forms()

    def _check_supplied(self) -> None:
        """The three ways a supplied route would stop being distinguishable."""
        if self.supplied_by_partition and not self.supplied_note:
            raise ValueError(
                f"{self.check}/{self.tool}: a supplied route needs a note saying what "
                "it is for; an unexplained one reads as a command the record "
                "prescribed"
            )
        supplied = [p for p, _ in self.supplied_by_partition]
        if len(supplied) != len(set(supplied)):
            raise ValueError(
                f"{self.check}/{self.tool}: names a partition twice in "
                f"supplied_by_partition ({supplied}), so one of the two never runs"
            )
        for partition in supplied:
            if self.argv or self.prescribed(partition):
                raise ValueError(
                    f"{self.check}/{self.tool}: {partition} carries both a prescribed "
                    "route and a supplied one, so the results row could not say which "
                    "of the two it ran"
                )
        if supplied and self.in_env:
            raise ValueError(
                f"{self.check}/{self.tool}: a supplied route writes each step in full "
                "and so takes no launcher prefix, which is what an in_env entry needs "
                "to reach the materialized environment"
            )

    def _check_own_runner(self) -> None:
        """The two ways naming a partition here would say nothing.

        A partition with no prescribed argv is a claim about a route that does
        not exist, so the suppression applies to nothing and the field reads as
        covering a route somebody has since removed. And an `in_env` entry needs
        the launcher's prefix to reach the materialized environment, so
        suppressing it there is not a command that runs as written - it is one
        that never arrives.

        The third shape, a partition carrying a supplied route as well, is
        already unreachable here rather than unguarded: passing the first check
        takes a prescribed argv, and `_check_supplied` rejects a partition
        carrying a prescribed route and a supplied one from the other side.
        """
        for partition in self.own_runner:
            if not self.prescribed(partition):
                raise ValueError(
                    f"{self.check}/{self.tool}: {partition} is named in own_runner "
                    "and has no prescribed command, so the suppressed prefix applies "
                    "to nothing"
                )
        if self.own_runner and self.in_env:
            raise ValueError(
                f"{self.check}/{self.tool}: an own_runner partition takes no launcher "
                "prefix, which is what an in_env entry needs to reach the materialized "
                "environment"
            )

    def _check_forms(self) -> None:
        """The three ways a declared form would stop meaning anything."""
        seen: set[str] = set()
        for form, disposition in self.forms:
            if not form.strip():
                raise ValueError(
                    f"{self.check}/{self.tool}: declares an empty command form, "
                    "which no extraction can ever match"
                )
            if disposition not in DISPOSITIONS:
                raise ValueError(
                    f"{self.check}/{self.tool}: {form!r} carries disposition "
                    f"{disposition!r}, which is not one of {DISPOSITIONS}"
                )
            if form in seen:
                raise ValueError(
                    f"{self.check}/{self.tool}: declares {form!r} twice, so which "
                    "disposition applies would depend on reading this file"
                )
            seen.add(form)

    def prescribed(self, partition: str) -> tuple[str, ...]:
        """The record's own command for this partition, before any completion."""
        if not self.argv_by_partition:
            return self.argv
        return dict(self.argv_by_partition).get(partition, ())

    def supplied(self, partition: str) -> tuple[tuple[str, ...], ...]:
        """The route this round contributed for this partition, if any.

        Returns `()` where the round supplied nothing, which is every entry
        except the two named holes this round exists to test a candidate for.
        """
        return dict(self.supplied_by_partition).get(partition, ())


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
# would test one rule selection and report it as evidence about every check that
# names the tool.
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
        forms=(),
    ),
    Invocation(
        check="arch/complexity-gate",
        tool="radon",
        record_quote=(
            "Whichever tool you run, record what the project itself enforces - a "
            "number it never configured is a number nothing holds it to."
        ),
        note="the record prescribes no radon command for the gate question",
        forms=(),
    ),
    Invocation(
        check="arch/complexity-gate",
        tool="xenon",
        record_quote=(
            "**Read the project's configured threshold before measuring, and treat "
            "its absence as a finding in its own right.**"
        ),
        note="the record prescribes no xenon command for the gate question",
        forms=(),
    ),
    Invocation(
        check="arch/complexity",
        tool="ruff",
        argv=("ruff", "check", "--select", "C901"),
        record_quote=(
            "`ruff check --select C901` or `radon cc` / `xenon`. Capture the metric "
            "per function."
        ),
        forms=(("ruff check --select C901", "runs"),),
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
        forms=(("radon cc", "runs"),),
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
        # Measured: `uvx xenon --max-absolute B src` on the seeded partition exits 1
        # with stdout empty and the whole finding on stderr -
        # `ERROR:xenon:block "src/fixture_app/complexity.py:4 classify" has a rank of
        # C`. Left at the stdout default, that finding was invisible to `classify`,
        # which read an empty stdout and graded the row `tool-failed` - a real hit
        # converted into no-evidence, the same shape `deptry` would be in without its
        # own `findings_stream="stderr"` below.
        findings_stream="stderr",
        record_quote=(
            "`ruff check --select C901` or `radon cc` / `xenon`. Capture the metric "
            "per function."
        ),
        forms=(),
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
        forms=(),
    ),
    Invocation(
        check="arch/coupling",
        tool="pydeps",
        record_quote="`pydeps` gives a visual; the counts are the evidence.",
        note=(
            "the record offers pydeps for a picture and says the counts are the "
            "evidence, so it prescribes no pydeps command for this check"
        ),
        forms=(),
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
        forms=(),
    ),
    Invocation(
        check="arch/cycles",
        tool="pydeps",
        argv=("pydeps", "--show-cycles", "--show-dot"),
        completion=(f"src/{PACKAGE}",),
        note="pydeps takes the package to graph and the record names none",
        record_quote=(
            "**Run `pydeps --show-cycles --show-dot`: `--show-cycles` alone has "
            "no textual output channel at all.**"
        ),
        forms=(
            ("pydeps --show-cycles", "superseded"),
            ("pydeps --show-cycles --show-dot", "runs"),
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
        forms=(),
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
        forms=(),
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
        forms=(),
    ),
    Invocation(
        check="arch/layering",
        tool="import-linter",
        record_quote="`import-linter` if a `.importlinter` contract exists, or `tach`.",
        note=(
            "conditional on a contract the fixture does not carry, so the record "
            "prescribes no command here"
        ),
        forms=(),
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
        forms=(),
    ),
    Invocation(
        check="arch/layering",
        tool="grimp",
        record_quote="Record the offending `file:line` for each violation.",
        note="grimp builds the edge set the record asks to be walked",
        forms=(),
    ),
    Invocation(
        check="arch/martin-metrics",
        tool="grimp",
        record_quote=(
            "Record `Ca`, `Ce`, `I`, `A` and `D` per package; `D` is the evidence."
        ),
        note="the metrics are computed from the graph rather than reported by a command",
        forms=(),
    ),
    Invocation(
        check="arch/over-abstraction",
        tool="grimp",
        record_quote=(
            "For each single-function module or one-method wrapper class, count call "
            "sites (`grimp` refs or a scoped grep); **one** is the trigger."
        ),
        note="grimp refs are counted from the built graph rather than from a command",
        forms=(),
    ),
    Invocation(
        check="arch/over-decomposition",
        tool="grimp",
        record_quote=(
            "Record the ratio / the count of trivial nodes / the offending chain as "
            "the evidence."
        ),
        note="the shape is computed from the same edge set rather than by a command",
        forms=(),
    ),
    # --- deps ---------------------------------------------------------------
    Invocation(
        check="deps/freshness",
        tool="uv",
        argv=("uv", "pip", "list", "--outdated", "--python"),
        completion=(f"{VENV_BIN}/python",),
        in_env=True,
        # The flag is the record's, not this table's: measured, `uv pip list
        # --outdated` with the interpreter unnamed prints nothing at exit 0 on a
        # partition whose environment has three outdated packages, because an
        # inner `uv` - the command rather than the thing running it - does its
        # own environment resolution and does not inherit the `--python` the
        # overlay already named. The record names the interpreter explicitly for
        # that reason, so the only thing left to supply here is the path.
        note=(
            "`<path-to-venv-python>` is a placeholder the record leaves to the caller; "
            "it resolves to the interpreter the partition's own materialization built "
            "inside the copy this run owns"
        ),
        record_quote=(
            "Name the interpreter explicitly on the `uv` route, as `uv pip list "
            "--outdated --python <path-to-venv-python>`: without `--python <path>`, "
            "`uv pip list --outdated` can return empty output at exit 0 against a tree "
            "with stale packages in it, rather than erroring or falling back to a "
            "discovered venv, so a clean run of the unqualified command is not evidence "
            "that nothing is outdated - it can equally be evidence the command never "
            "found the environment."
        ),
        forms=(
            ("uv pip list --outdated", "superseded"),
            ("uv pip list --outdated --python <path-to-venv-python>", "runs"),
        ),
    ),
    Invocation(
        check="deps/freshness",
        tool="pip",
        argv=("pip", "list", "--outdated"),
        in_env=True,
        record_quote=(
            "`uv pip list --outdated` / `pip list --outdated`, both of which read the "
            "installed environment rather than the lockfile, so they need the tree "
            "resolved."
        ),
        forms=(("pip list --outdated", "runs"),),
    ),
    Invocation(
        check="deps/hygiene",
        tool="deptry",
        argv=("deptry",),
        completion=(".",),
        in_env=True,
        # Measured: on a seeded partition `deptry .` exits 1 with an empty
        # stdout and its whole DEP002/DEP001 report on stderr.
        findings_stream="stderr",
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
        forms=(),
    ),
    Invocation(
        check="deps/inventory",
        tool="cyclonedx-py",
        argv_by_partition=(
            ("uv", ("uv", "export", "--format=cyclonedx1.5", "--frozen")),
            ("pip", ("cyclonedx-py", "requirements")),
            ("poetry", ("cyclonedx-py", "poetry")),
            ("pipenv", ("cyclonedx-py", "pipenv")),
            ("pylock", ()),
        ),
        own_runner=("uv",),
        supplied_by_partition=(
            ("pylock", (("uvx", "cyclonedx-py", "requirements", "pylock.toml"),)),
        ),
        note=(
            "the record prescribes the subcommand 'matching the partition's own "
            "dependency file', so the command is per partition rather than shared - "
            "and on a uv-locked tree what it names is the native export instead, a "
            "command of another tool entirely, which is why that row names its own "
            "runner. It names no route for a PEP 751 file, which is why that row "
            "carries no prescribed command"
        ),
        supplied_note=(
            "the record's first named hole: it names no route at all for a PEP 751 "
            "file, and this step points the requirements subcommand at one, so it is "
            "a candidate this round tests rather than a correction it has made. It "
            "never reaches record_argv, which stays the record's own command per "
            "partition, and the record prescribes none on this one"
        ),
        record_quote=(
            "`cyclonedx-py`'s `requirements`, `poetry` or `pipenv` subcommand, "
            "matching the partition's own dependency file, or the tool's native SBOM "
            "export. `cyclonedx-py` has no uv subcommand, so on a uv-locked partition "
            "the native export is `uv export --format=cyclonedx1.5 --frozen`: it "
            "produces a well-formed CycloneDX 1.5 document (6 components, "
            "`specVersion` 1.5, no `licenses` field)."
        ),
        forms=(
            ("cyclonedx-py environment", "alternative"),
            ("cyclonedx-py poetry", "runs"),
            ("uv export --format=cyclonedx1.5 --frozen", "runs"),
        ),
    ),
    Invocation(
        check="deps/licenses",
        tool="pip-licenses",
        argv=("pip-licenses",),
        in_env=True,
        record_quote=(
            "`pip-licenses`, or read each installed dist's `*.dist-info/METADATA` "
            "(`License` + `Classifier: License ::`)."
        ),
        forms=(("pip-licenses --format json", "alternative"),),
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
        forms=(),
    ),
    Invocation(
        check="deps/vulnerabilities",
        tool="pip-audit",
        argv_by_partition=(
            ("uv", ()),
            (
                "pip",
                ("pip-audit", "-r", "requirements.txt", "--no-deps", "--disable-pip"),
            ),
            ("poetry", ()),
            ("pipenv", ()),
            ("pylock", ("pip-audit", "--locked", ".")),
        ),
        supplied_by_partition=(
            (
                "uv",
                (
                    (
                        "uv",
                        "export",
                        "--frozen",
                        "--format",
                        "requirements.txt",
                        "-o",
                        SUPPLIED_REQUIREMENTS,
                    ),
                    ("uvx", "pip-audit", "-r", SUPPLIED_REQUIREMENTS),
                ),
            ),
        ),
        supplied_note=(
            "the record's second named hole: it names no mode for a uv tree, so a "
            "uv-locked partition has no vulnerability lens on a read-only clone. The "
            "candidate is an export written to a file - pip-audit's `-r` takes a path "
            "rather than a pipe - and then the `-r` mode the record does name. The "
            "record mentions `uv export --frozen` only to say what a fully resolved "
            "requirements file contains, and prescribes no export-then-audit route for "
            "a uv tree, so the route as a whole is this round's. Supplied for uv "
            "alone: the same export is "
            "what a poetry or pipenv partition has no lockfile for - `uv export "
            "--frozen` reads a uv.lock and those partitions carry none by "
            "construction - so there is no equivalent route to supply them"
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
            "`pip-audit --locked .` reads a PEP 751 lock file (`pylock.*.toml`) and "
            "the project's `pyproject.toml`, and nothing else: it does not read "
            "`uv.lock`, `poetry.lock`, `Pipfile.lock` or a requirements file, so a "
            "target locked with uv or poetry alone is not served by `--locked` and is "
            "the ordinary case rather than the exotic one. Where the partition has a "
            "requirements file, `pip-audit -r <requirements>` parses it and provisions "
            "its own throwaway virtualenv to resolve it, so it needs network rather "
            "than the target's tree."
        ),
        forms=(
            ("pip-audit --locked .", "runs"),
            # `superseded` is what the record says: it names this form and then
            # narrows it with the `--no-deps --disable-pip` pair below. The uv
            # supplied route above runs the un-narrowed form verbatim all the
            # same, and nothing tests that a disposition does not understate what
            # runs - see `forms` in `Invocation`'s docstring.
            ("pip-audit -r <requirements>", "superseded"),
            ("pip-audit -r <requirements> --no-deps --disable-pip", "runs"),
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
        forms=(),
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
        forms=(),
    ),
    Invocation(
        check="docs/docstring-coverage",
        tool="pydocstyle",
        argv=("pydocstyle",),
        record_quote=(
            "`ruff` `D` rules / `pydocstyle` / `interrogate` if present, else an "
            "AST/grep sweep."
        ),
        forms=(),
    ),
    Invocation(
        check="docs/docstring-coverage",
        tool="interrogate",
        argv=("interrogate",),
        record_quote=(
            "`ruff` `D` rules / `pydocstyle` / `interrogate` if present, else an "
            "AST/grep sweep."
        ),
        note=(
            "the record's fallback is one line naming three tools and no arguments; "
            "pydocstyle and interrogate both default to the working directory, so the "
            "bare name is runnable for them"
        ),
        forms=(),
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
                forms=(("bandit -r <pkg>", "runs"),),
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
                forms=(("ruff check --select S", "runs"),),
            ),
            Invocation(
                check=check,
                tool="semgrep",
                argv=("semgrep", "--config", "p/python"),
                record_quote=(
                    "`bandit -r <pkg>` (captures test id like `B602`, severity, "
                    "confidence, `file:line`), or `ruff check --select S` if the "
                    "project standardizes on ruff, or `semgrep --config p/python` for "
                    "dataflow-aware rules."
                ),
                forms=(("semgrep --config p/python", "runs"),),
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
        forms=(("pytest --cov=<pkg> --cov-branch --cov-report=term-missing", "runs"),),
    ),
    Invocation(
        check="test/coverage-reach",
        tool="coverage.py",
        argv=("coverage", "run", "-m", "pytest"),
        then=("coverage", "report", "--show-missing"),
        in_env=True,
        record_quote=(
            "`pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage "
            "run -m pytest` + `coverage report --show-missing`)."
        ),
        note=(
            "the record prescribes two commands in sequence for this route, so the "
            "second is held in `then` rather than dropped"
        ),
        forms=(
            ("coverage report --show-missing", "runs"),
            ("coverage run -m pytest", "runs"),
        ),
    ),
    Invocation(
        check="test/determinism",
        tool="pytest-randomly",
        argv=("pytest",),
        in_env=True,
        record_quote=(
            "`pytest-randomly` randomizes the order as soon as it is installed, so "
            "the command is `pytest` itself; re-run a failing order with `pytest "
            "--randomly-seed=<n>`."
        ),
        forms=(("pytest --randomly-seed=<n>", "alternative"),),
    ),
    Invocation(
        check="test/determinism",
        tool="pytest-rerunfailures",
        # `in_env=True` because this is a pytest plugin like `pytest-randomly` and
        # `pytest-timeout`, resolved into the materialized environment rather than
        # fetched standalone - true of the tool whether or not this entry ever
        # runs a command. It has no effect on the check itself: `argv` is empty,
        # so the row loop never reaches `launcher`. It does matter to
        # `probe_versions`, which calls `launcher` for every tool regardless of
        # `argv` - without it, the version probe would resolve a bare `uvx`
        # interpreter with the plugin never installed, on every partition and
        # grant.
        in_env=True,
        record_quote=(
            "and, for suspected flakies, repeat runs; flag order-dependence and "
            "non-determinism."
        ),
        note=(
            "the record asks for repeat runs and names no flag, so this plugin's own "
            "`--reruns` is nowhere in the prescription"
        ),
        forms=(),
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
        forms=(("pytest --durations=25", "runs"),),
    ),
    Invocation(
        check="test/mutation",
        tool="mutmut",
        argv=("mutmut", "run"),
        in_env=True,
        record_quote="**Python** - `mutmut run` or `cosmic-ray`.",
        forms=(
            ("mutmut results", "alternative"),
            ("mutmut run", "runs"),
        ),
    ),
    Invocation(
        check="test/mutation",
        tool="cosmic-ray",
        in_env=True,
        record_quote=(
            "Run `mutmut` / `cosmic-ray` on the highest-risk modules to measure "
            "whether tests kill injected faults (the truest test-effectiveness signal, "
            "but slow) - enable via argument or ask the user; default off for a quick "
            "pass, recommend on for a scorer/parser-heavy core."
        ),
        note=(
            "the record names the tool and no subcommand, so there is no command here "
            "to run: cosmic-ray drives a session from a TOML config, and writing one "
            "would manufacture the input rather than transcribe the record. Left "
            "empty rather than run bare, which would report a record with no runnable "
            "command as a tool that failed"
        ),
        forms=(),
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
        forms=(),
    ),
)


@lru_cache(maxsize=1)
def _records() -> dict[str, object]:
    """Every check record, parsed once.

    Cached because the derivations below are called once per (check, tool) pair,
    and every re-walk of the skill tree is another chance for the run to be
    reading a different tree than the one it started on.
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


def invocations_for(
    partition: str, *, only_check: str | None = None
) -> tuple[Invocation, ...]:
    """Every invocation one partition runs.

    Scoped by the expectations rather than by a second list, so the harness
    cannot run a set the published record does not grade.

    Args:
        partition: Which partition's scope to read.
        only_check: Narrow the scope to one check id, for re-running a single
            cell without re-running the matrix around it. A filter matching
            nothing raises rather than returning an empty tuple: the pair is
            what fails, either because no invocation names the check or because
            this partition's expectations exclude it, and an empty run would
            write an artifact of zero rows that reads as a check whose tools
            were all absent.
    """
    if partition not in PARTITIONS:
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {PARTITIONS}"
        )
    carried = {e.check for e in expectations_for(partition)}
    scoped = tuple(i for i in INVOCATIONS if i.check in carried)
    if only_check is None:
        return scoped
    filtered = tuple(i for i in scoped if i.check == only_check)
    if not filtered:
        raise ValueError(
            f"no invocation for {only_check!r} on the {partition} partition; "
            f"it carries {sorted({i.check for i in scoped})}"
        )
    return filtered


def packages_for(tool: str) -> tuple[str, ...]:
    """Everything that has to be installed for this tool's route to run.

    The first is the tool itself; anything after it is what the route needs
    present and the fixture does not declare.
    """
    return TOOL_PACKAGES.get(tool, (tool,))


def launcher(
    invocation: Invocation,
    partition: str,
    *,
    granted: bool,
    honour_own_runner: bool = True,
) -> tuple[str, ...]:
    """The words that go in front of the command, and how the tool is obtained.

    Nothing goes in front of a command the record already writes whole, which is
    what `own_runner` names - see that field for why such a route exists at all.
    `honour_own_runner=False` is for a caller running something other than the
    record's command: the version probe runs the tool's own `--version`, which
    still has to be obtained the usual way, and probing it bare would record a
    missing tool where the tool's version belongs.

    An `in_env` tool runs from inside the materialized environment under a
    grant, because the one-shot runner's sandbox cannot see what the target
    resolved: measured on the pylock partition, `uvx deptry` reported
    markupsafe as DEP001 where the route below reported it as DEP003, which is
    the answer the expectation claims. Grading a correct run against the other
    one would send a later pass off to "fix" a record that was right.

    Without the grant there is no environment to run inside, so the same tool
    falls back to the one-shot runner and the run records which it used.

    Every partition but `uv` reaches the environment the same way: `uv run`,
    pointed at that partition's own `.venv/bin/python` with `--python`, and the
    needed package brought in from outside with `--with`. This is deliberate
    and not a shortcut around naming each manager's own runner (`poetry run`,
    `pipenv run`) - those install the package into the partition's own venv to
    make it reachable, and that install is itself a write `audit-core` bars:
    measured on the poetry partition, provisioning `deptry` this way pulled in
    a newer `packaging` and printed `Uninstalling packaging-20.9`, silently
    replacing the exact pin the fixture seeded for `deps/freshness` to find
    outdated. `--with` fetches the tool into a layer outside that venv instead,
    so the venv the checks read is the one materialization built and nothing
    else ever touches it. `--no-project` is load-bearing here, not decoration:
    a partition's copy carries a `pyproject.toml` (`pylock`'s is byte-identical
    to `uv`'s own) and no `uv.lock`, and a bare `uv run` there does project
    discovery from `cwd`, locks and syncs it - writing a `uv.lock` into the
    copy that a later row in the same run would then read, and resolving the
    tool into a fresh project environment instead of the `--python` one named.
    Measured: without the flag, `deptry` still passed on the pylock copy, but
    a `uv.lock` was on disk afterward where none had been before.

    Reaching that venv depends on it existing at `.venv` regardless of which
    manager built it, which is what `_fixture_env`'s
    `POETRY_VIRTUALENVS_IN_PROJECT` / `PIPENV_VENV_IN_PROJECT` are for.

    `argv` itself never changes here - what the record prescribes is untouched
    by any of this; only the words placed in front of it are.
    """
    if honour_own_runner and partition in invocation.own_runner:
        return ()
    packages = packages_for(invocation.tool)
    extra = tuple(word for name in packages[1:] for word in ("--with", name))
    if not (invocation.in_env and granted):
        if packages == (invocation.tool,):
            return ("uvx",)
        return ("uvx", "--from", packages[0], *extra)
    if partition == "uv":
        return ("uv", "run", "--with", packages[0], *extra)
    return (
        "uv",
        "run",
        "--no-project",
        "--python",
        f"{VENV_BIN}/python",
        "--with",
        packages[0],
        *extra,
    )


# What a non-zero exit from this tool means, so `classify` never has to guess
# it from the shape of one observation. The three values:
#
# * `findings` - the tool's whole design is to signal a violation through its
#   exit code, and the report it prints is what tells a genuine hit from a
#   tool that broke before producing one. `classify` still requires content on
#   the tool's own `findings_stream` before it grades a non-zero exit `ok`;
#   this value only says the tool is *capable* of a designed non-zero exit in
#   the first place, which the ones below are not.
# * `failure` - a non-zero exit from this exact invocation is proven to never
#   mean a finding, so content on either stream is never read as one. `mutmut`
#   is the one entry here, and it is proven rather than assumed: `mutmut run`
#   (bare, the record's own invocation, no `mutant_names`) only calls `exit(1)`
#   from setup/collection failures - a stats-collection error, no test
#   associated with any mutant, or (measured on this fixture) a failing
#   baseline reported as `Failed to run clean test` - and the loop that tests
#   the generated mutants and prints survivor counts never calls `sys.exit` or
#   `exit()` on their account; a completed run simply returns. So there is no
#   path from "mutants survived" to a non-zero exit for this command, and the
#   spinner/status text `mutmut` always writes to stdout regardless of outcome
#   is not evidence of anything - reading it as a report, the way `findings`
#   does, is exactly the bug this table exists to stop.
# * `ambiguous` - a reporting/listing tool with no gating flag in the recorded
#   invocation, so nothing here establishes what its non-zero exit would mean;
#   the honest answer is that it is not known, and the conservative reading
#   (never `ok` on a non-zero exit) is what `classify` gives it, same as
#   `failure`. Distinct from `failure` in name because nothing has been proven
#   about these the way it has for `mutmut` - a future observation might
#   promote one to `findings` with a stated reason, never silently.
#
# Every tool a partition could ever hand `classify` a non-zero exit for is
# named here; the exact-set guard in the tests is what holds that, so a tool
# added to `INVOCATIONS` without an entry fails loudly rather than defaulting.
NONZERO_EXIT_KINDS = ("findings", "failure", "ambiguous")

NONZERO_EXIT_MEANING: dict[str, str] = {
    "ruff": "findings",
    "xenon": "findings",
    "vulture": "findings",
    "bandit": "findings",
    "semgrep": "findings",
    "pydocstyle": "findings",
    "interrogate": "findings",
    "deptry": "findings",
    "pip-audit": "findings",
    "pytest-cov": "findings",
    "pytest-randomly": "findings",
    "pytest-timeout": "findings",
    "mutmut": "failure",
    "radon": "ambiguous",
    "pydeps": "ambiguous",
    "uv": "ambiguous",
    "pip": "ambiguous",
    "cyclonedx-py": "ambiguous",
    "pip-licenses": "ambiguous",
    "coverage.py": "ambiguous",
}


def nonzero_exit_meaning(tool: str) -> str:
    """What a non-zero exit from `tool` means, read out of the stated table.

    Raises rather than defaulting, for the same reason `grant_tier` raises on
    an unknown (check, tool) pair: an omitted entry must never read as a
    silent claim, and silence is exactly how xenon and mutmut were misgraded.
    """
    if tool not in NONZERO_EXIT_MEANING:
        raise ValueError(
            f"{tool!r} has no stated non-zero-exit meaning in NONZERO_EXIT_MEANING; "
            "an omitted entry would read as a silent default rather than a decision"
        )
    return NONZERO_EXIT_MEANING[tool]


def classify(
    returncode: int,
    stdout: str,
    stderr: str,
    tool_present: bool,
    *,
    permitted: bool = True,
    findings_stream: str = "stdout",
    nonzero_meaning: str = "findings",
) -> tuple[str, str]:
    """Map one observation into the engine's vocabulary.

    Pure, and it never returns a status outside `STATUSES`: the point of the
    round is that the family is tested against the engine's scale rather than
    that the scale grows to fit what came back.

    **A non-zero exit is not a failure by itself - but only for a tool whose
    designed exit code says so.** bandit, ruff, deptry, pip-audit and a
    shuffled pytest all exit non-zero exactly when they find what this fixture
    planted, so reading the exit code alone would grade every correct run as a
    tool defect. What distinguishes a failure, for one of these, is a non-zero
    exit with nothing on the stream that tool reports on - a tool that ran and
    produced no report. Which stream that is comes from the entry, because it
    varies: measured, `deptry .` on a seeded partition exits 1 with an empty
    stdout and its whole report on stderr, so reading stdout for it would grade
    a run that found every planted seed as a tool failure and a run that found
    nothing as clean.

    **That content-based rule only holds for a tool proven capable of a
    designed non-zero exit**, which `nonzero_meaning` states rather than
    assumes. `mutmut` breaks the rule outright: it writes a spinner and status
    text to stdout on every run, failure or not, so "is there content on the
    stream" cannot tell a completed mutation run from one that died in setup -
    measured, a run that got as far as `Failed to run clean test` and tested
    zero mutants still has non-empty stdout. A tool marked `failure` or
    `ambiguous` is never graded `ok` on a non-zero exit regardless of what is
    on either stream, because a tool that may have done nothing must never
    read as a tool that answered.

    **This is triage rather than grading, and the limit is real in both
    directions.** Nothing here can tell a report from an error message on the
    same stream: `deps/hygiene` on the pipenv partition is *expected* to exit
    non-zero with `DependencySpecificationNotFoundError` on stderr, and under a
    stderr findings-stream that grades `ok` - a false clean where reading stdout
    would have given a false failure. Neither reading is the answer, and neither
    is meant to be: what actually grades a row is matching its content against
    the written expectation, which is the next round's work. What this function
    owes that round is a status that is right about the ordinary case and a
    record complete enough to re-classify from without re-running.

    Args:
        returncode: The command's exit status.
        stdout: What it wrote to stdout.
        stderr: What it wrote to stderr.
        tool_present: Whether the tool could be obtained at all.
        permitted: Whether the run holds the grant this tool needs.
        findings_stream: Which of the two streams this tool reports on.
        nonzero_meaning: What a non-zero exit from this tool means - one of
            `NONZERO_EXIT_KINDS`. Only `findings` ever turns a non-zero exit
            into `ok`, and only then with content on `findings_stream`.

    Returns:
        The status and its reason; the reason is empty for `ok`.
    """
    if nonzero_meaning not in NONZERO_EXIT_KINDS:
        raise ValueError(
            f"nonzero_meaning is {nonzero_meaning!r}; expected one of "
            f"{NONZERO_EXIT_KINDS}"
        )
    if not permitted:
        return ("no-evidence", "not-permitted")
    if not tool_present:
        return ("no-evidence", "tool-unavailable")
    if returncode == 0:
        return ("ok", "")
    if nonzero_meaning == "findings":
        findings = stderr if findings_stream == "stderr" else stdout
        if findings.strip():
            return ("ok", "")
    # `failure` and `ambiguous` both fall through to here on any non-zero
    # exit, and so does `findings` with nothing on its own stream: none of the
    # three is evidence the tool answered.
    return ("no-evidence", "tool-failed")


# How each launcher says it could not obtain the tool it was asked to run.
#
# `_run` detects an absent tool by `FileNotFoundError` on the binary it
# launched, which only ever fires where the command *is* the tool. Everywhere a
# launcher goes in front - `uvx` or `uv run` - that binary exists whatever
# happens next, so the launcher's own resolution failure comes back as an
# ordinary non-zero exit and grades `tool-failed`: a tool nobody could fetch,
# reported as a tool that ran and broke. Measured: `uvx no-such-package-45xyzq`
# exits 1 with "not found in the package registry".
#
# Matching a message is fragile and this is the only signal there is, so the
# match is narrowed twice - it is consulted only when the command's first word
# is one of these launchers, and only when the command failed. Every command
# this file runs starts with `uv`, `uvx`, or a bare tool name `_run` already
# reports as absent by `FileNotFoundError` - poetry and pipenv never head a
# command themselves, since even their own materialization goes through a
# pinned `uvx poetry@...` / `uvx pipenv@...` - so this dict holds only the two
# names a launcher's own resolution failure can actually surface under.
LAUNCHER_MISSES: dict[str, tuple[str, ...]] = {
    "uvx": (
        "not found in the package registry",
        "no solution found when resolving tool dependencies",
    ),
    "uv": (
        "not found in the package registry",
        "no solution found when resolving tool dependencies",
    ),
}


def launcher_missed(
    command: Sequence[str], returncode: int | None, stderr: str
) -> bool:
    """Whether the launcher failed to obtain the tool rather than the tool failing.

    Args:
        command: The argv as it was run, launcher words included.
        returncode: Its exit status; `None` where it never exited.
        stderr: What it wrote to stderr.

    Returns:
        `True` where this is `tool-unavailable` wearing a `tool-failed` exit.
    """
    if returncode == 0 or not command:
        return False
    markers = LAUNCHER_MISSES.get(command[0], ())
    lowered = stderr.lower()
    return any(marker in lowered for marker in markers)


def _fixture_env() -> dict[str, str]:
    """The environment a fixture subprocess runs under.

    The harness runs under `uv run`, which exports `VIRTUAL_ENV` pointing at
    this repository's environment. A package manager invoked in a fixture copy
    with that set resolves against the handbook's environment instead of the
    fixture's, and every `deps` answer would then be about this repository.

    `uv run` also puts this repository's own `.venv/bin` at the front of `PATH`,
    which is the same leak by the other door and a quieter one: that directory
    carries a `pytest` and a `ruff`, so a bare `pytest` or `ruff` invoked in a
    fixture copy resolves from the handbook's environment and answers about the
    handbook's tree rather than the fixture's. It is dropped by path rather
    than by emptying `PATH`, because the launchers themselves - `uv`, `uvx`,
    `poetry`, `pipenv` - are installed outside it and have to stay findable.

    `POETRY_VIRTUALENVS_IN_PROJECT` and `PIPENV_VENV_IN_PROJECT` are set here
    rather than left unset, and that is the opposite of what
    `build_python_fixtures._fixture_env` does with the same two names - both
    functions are enforcing the same invariant from either side of it.
    Materialization writes into the copy, and the copy is not the fixture
    `build_python_fixtures` protects, so a venv landing inside it is exactly
    what this function is for. Left unset, poetry writes its venv to its own
    cache directory and pipenv to `~/.local/share/virtualenvs`, outside the
    copy `reconstruct` made and colliding across runs in the caller's home
    directory instead. Set, both land at `.venv` inside the copy - which is
    what makes `--python .venv/bin/python` below resolve to the tree this run
    actually materialized rather than to nothing, or to a stale one a previous
    run left behind. A future edit that "harmonizes" the two `_fixture_env`
    functions would silently break this.
    """
    env = dict(os.environ)
    for name in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH"):
        env.pop(name, None)
    env["POETRY_VIRTUALENVS_IN_PROJECT"] = "1"
    env["PIPENV_VENV_IN_PROJECT"] = "1"
    own_bin = os.path.normpath(str(REPO_ROOT / ".venv" / "bin"))
    env["PATH"] = os.pathsep.join(
        entry
        for entry in env.get("PATH", "").split(os.pathsep)
        if entry and os.path.normpath(entry) != own_bin
    )
    env["PIPENV_IGNORE_VIRTUALENVS"] = "1"
    return env


def _run(command: Sequence[str], cwd: Path, timeout: int) -> dict[str, object]:
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
    """
    env = _fixture_env()
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

    Two refusals rather than one, because the destructive step is `rmtree` on
    `work_root / partition` and not on `work_root` itself. A work directory that
    is the fixture *root* - `--work-dir fixtures/python`, the obvious choice,
    and where the results file already goes - resolves nowhere under the
    fixture, so the first guard passes; but the destination is then the seeded
    partition itself, and the rmtree deletes it before copytree reads it.
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
    if destination.resolve() == source.resolve():
        raise ValueError(
            f"the copy of {partition} would land on the fixture itself ({source}); "
            "reconstructing onto the target is the write the read-only invariant "
            "forbids, and the rmtree below would delete the seeded partition before "
            "anything read it"
        )
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return destination


def _verdict(
    ran: Sequence[tuple[Sequence[str], dict[str, object]]],
    findings_stream: str,
    nonzero_meaning: str,
) -> dict[str, object]:
    """The status of a route, read from every command it ran.

    A route is as good as its worst step: the first step that does not answer
    decides, and where all of them answer the last one does. So a two-command
    route whose reporting half died is a failure rather than a clean run on the
    strength of its measuring half - which is what classifying on the first
    command alone would have made it.

    Args:
        ran: Each step's argv paired with what `_run` returned for it, in the
            order they ran.
        findings_stream: Which stream this tool reports its findings on.
        nonzero_meaning: What a non-zero exit from this tool means, read once
            by the caller from `NONZERO_EXIT_MEANING` and passed straight
            through to `classify` for every step.

    Returns:
        The `status` and `reason` keys, plus `detail` where one of `DETAILS`
        says what the engine's reason cannot.
    """
    status, reason, detail = "ok", "", ""
    for command, outcome in ran:
        returncode = outcome["returncode"]
        stderr = str(outcome["stderr"])
        # A command that never exited has no exit status, and both ways of
        # ending up there are settled before anything reads output. Substituting
        # a number for the missing status instead - and a wrong substitution is
        # one character away - hands `classify` an exit code the command never
        # returned, next to a stderr `_run` wrote itself. On the one entry whose
        # findings stream *is* stderr, that synthesized `TimeoutExpired` text
        # then reads as the tool's report and a hung deptry grades `ok`.
        if returncode is None:
            if outcome["tool_present"]:
                # Hung. `tool-failed` is what the engine has for it, and the
                # detail is what separates it from a tool that ran and broke:
                # the two need different responses and the reason cannot say
                # which of them happened.
                status, reason, detail = "no-evidence", "tool-failed", "timed-out"
            else:
                # The binary was not there at all, which `_run` reports by name.
                status, reason, detail = "no-evidence", "tool-unavailable", ""
            break
        code = int(returncode)
        present = bool(outcome["tool_present"]) and not launcher_missed(
            command, code, stderr
        )
        status, reason = classify(
            code,
            str(outcome["stdout"]),
            stderr,
            tool_present=present,
            findings_stream=findings_stream,
            nonzero_meaning=nonzero_meaning,
        )
        detail = ""
        if status != "ok":
            break
    verdict: dict[str, object] = {"status": status, "reason": reason}
    if detail:
        verdict["detail"] = detail
    return verdict


def _run_supplied(
    invocation: Invocation,
    steps: Sequence[tuple[str, ...]],
    copy: Path,
    timeout: int,
    row: dict[str, object],
) -> dict[str, object]:
    """Run a route this round contributed, and record it as contributed.

    Each step runs exactly as written, with no launcher prefix - for a different
    reason than `own_runner`'s, where the record's own command already leads with
    a runner. Here there is no record naming a tool for the launcher to go and
    fetch at all, and these routes mix the target's own package manager with a
    fetched one inside a single route.

    A step that does not answer stops the route, so a failed export is never
    followed by an audit of the file it did not write.
    """
    ran: list[tuple[Sequence[str], dict[str, object]]] = []
    for step in steps:
        outcome = _run(step, copy, timeout)
        ran.append((step, outcome))
        if outcome["returncode"] != 0:
            break
    row |= {
        "ran": True,
        "steps": [{"command": list(c), **o} for c, o in ran],
        **ran[-1][1],
    }
    row |= _verdict(
        ran, invocation.findings_stream, nonzero_exit_meaning(invocation.tool)
    )
    return row


def probe_versions(
    partition: str,
    grant: str,
    work_dir: Path,
    timeout: int,
    *,
    blocked_by: Sequence[str] | None = None,
    only_check: str | None = None,
) -> dict[str, str]:
    """Report the version of every tool this partition will invoke.

    Runs through the same `launcher` as the invocation, because a `uvx`-fetched
    tool and a tool on `PATH` are different copies and may differ in version.
    Not through the same `own_runner` suppression, though: the probe is the
    tool's own `--version` rather than the record's command, so it needs the
    tool fetched even where the record's command fetches nothing.
    A probe that fails is recorded as its failure text rather than dropped: an
    absent version is a fact about the run, and a missing key would read as a
    tool that was never invoked.

    Args:
        partition: Which partition's tools to probe, scoped by the same
            `invocations_for` the checks run against.
        grant: Whether the probe runs as though the tree were resolved; passed
            straight to `launcher`, exactly as the real invocation would be.
        work_dir: The materialized copy to run each probe in - the same
            directory the invocations already ran against, not the fixture
            root, so a probe needing project context (`mutmut --version`) sees
            the same tree its check would.
        timeout: Seconds before a probe is abandoned as hung.
        blocked_by: The materialization command that failed, if it did. An
            `in_env` tool's probe never runs against a tree that was never
            built - that would either hang on an absent environment or answer
            from whatever the launcher happens to fall back to, neither of
            which is a fact about the tool - so it is recorded as blocked
            instead, the same way a dependent row is in `run_partition`.
        only_check: The same narrowing `run_partition` ran under, so the map
            holds a version for each tool this run invoked and none for a tool
            it did not. A version beside no row would read as a probed tool
            whose check produced nothing, and probing the partition's whole tool
            set costs a full run's fetches for a one-cell answer.
    """
    granted = grant != "none"
    representative: dict[str, Invocation] = {}
    for inv in INVOCATIONS:
        representative.setdefault(inv.tool, inv)

    versions: dict[str, str] = {}
    for tool in {inv.tool for inv in invocations_for(partition, only_check=only_check)}:
        probe = VERSION_PROBE[tool]
        if probe is None:
            versions[tool] = f"no version route: {NO_VERSION_ROUTE[tool]}"
            continue
        inv = representative[tool]
        if blocked_by is not None and inv.in_env:
            versions[tool] = (
                "environment-unmaterialized: the partition's materialization "
                f"stopped at {' '.join(blocked_by)}, so there is no environment "
                "this probe could run inside"
            )
            continue
        prefix = launcher(inv, partition, granted=granted, honour_own_runner=False)
        command = (*prefix, *probe)
        outcome = _run(command, work_dir, timeout)
        stdout = str(outcome["stdout"]).strip()
        stderr = str(outcome["stderr"]).strip()
        if outcome["returncode"] == 0:
            versions[tool] = stdout or stderr
        else:
            versions[tool] = stdout or stderr or f"exit code {outcome['returncode']}"
    return versions


def run_partition(
    partition: str,
    source: Path,
    work_root: Path,
    grant: str,
    timeout: int,
    *,
    only_check: str | None = None,
) -> dict[str, object]:
    """Run one partition's invocations under one grant state.

    Returns the whole observation rather than a verdict: the raw exit code,
    stdout and stderr are kept so that a later pass can re-classify without
    re-running, and so that a completion the transcription had to make is
    visible beside what it produced.

    `only_check` narrows the run to one check id and reaches the version probe
    as well as the rows, so the observation covers exactly the cell that ran.
    The observation records it under `only_check`, because a file holding one
    check's rows is indistinguishable from a matrix whose other checks all
    produced nothing unless it says which it is. The caller owns the filename;
    `main` gives a filtered run one carrying the check's slug.
    """
    if grant not in GRANTS:
        raise ValueError(f"unknown grant {grant!r}; expected one of {GRANTS}")
    granted = grant != "none"
    copy = reconstruct(partition, source, work_root)
    materialization = []
    # The command that stopped the materialization, or `None` where it finished.
    # A route that fails leaves the copy unresolved, and every row needing the
    # tree then has to say so rather than run against it: run anyway and each
    # such row classifies on its own, `tool-failed` here and spuriously `ok`
    # there, with nothing in the file pointing back at the one cause - which is
    # the harness inventing a finding rather than reporting one.
    blocked_by: list[str] | None = None
    if granted:
        for command in MATERIALIZE[partition]:
            outcome = _run(command, copy, timeout)
            materialization.append({"command": list(command), **outcome})
            if outcome["returncode"] != 0:
                blocked_by = list(command)
                break

    rows = []
    for invocation in invocations_for(partition, only_check=only_check):
        tier = grant_tier(invocation.check, invocation.tool)
        permitted = granted or not tier
        argv = argv_for(invocation, partition)
        supplied = invocation.supplied(partition)
        row: dict[str, object] = {
            "check": invocation.check,
            "tool": invocation.tool,
            "record_argv": list(invocation.prescribed(partition)),
            "completion": list(invocation.completion),
            "note": invocation.note,
            "needs": tier,
            "in_env": invocation.in_env,
        }
        if supplied:
            # Never as `record_argv`: this round contributed the route, and a
            # later pass reading it out of the prescribed field would read a
            # candidate answer as something the record already said.
            row |= {
                "supplied": [list(step) for step in supplied],
                "supplied_note": invocation.supplied_note,
            }
        if not argv and not supplied:
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
        # A row needing the tree is one carrying a tier or running inside the
        # environment; the two sets are not the same, because `pydeps` needs the
        # resolved tree to see the graph and still launches through `uvx`.
        if blocked_by is not None and (tier or invocation.in_env):
            row |= {
                "ran": False,
                "status": "no-evidence",
                "reason": "tool-unavailable",
                "detail": "environment-unmaterialized",
                "blocked_by": blocked_by,
                "why": (
                    "the partition's materialization stopped at "
                    f"{' '.join(blocked_by)}, so the tree this route reads was never "
                    "built and no tool ran; this says nothing about the tool"
                ),
            }
            rows.append(row)
            continue
        if supplied:
            rows.append(_run_supplied(invocation, supplied, copy, timeout, row))
            continue
        # A tool the fixture does not declare is fetched by `launcher` from
        # outside the copy - `uv run --with` (or, off `uv`, the same route
        # pointed `--python` at the copy's own venv) - and never installed into
        # the copy this run owns, never mind the fixture or the shared tree:
        # `audit-core` bars all three, and a package the audit added is never
        # evidence about the target wherever it landed.
        prefix = launcher(invocation, partition, granted=granted)
        command = (*prefix, *argv)
        outcome = _run(command, copy, timeout)
        row |= {"ran": True, "command": list(command), **outcome}
        # A route the record writes as two commands is one route, so both halves
        # reach the verdict. Classifying on the first alone would grade a route
        # whose measuring half ran and whose reporting half died as `ok` with no
        # coverage table behind it - the shape `then` exists to prevent.
        ran: list[tuple[Sequence[str], dict[str, object]]] = [(command, outcome)]
        if invocation.then:
            follow_up = (*prefix, *invocation.then)
            then_outcome = _run(follow_up, copy, timeout)
            row["then"] = {"command": list(follow_up), **then_outcome}
            ran.append((follow_up, then_outcome))
        row |= _verdict(
            ran, invocation.findings_stream, nonzero_exit_meaning(invocation.tool)
        )
        rows.append(row)

    versions = probe_versions(
        partition, grant, copy, timeout, blocked_by=blocked_by, only_check=only_check
    )

    return {
        "partition": partition,
        "grant": grant,
        "source": str(source),
        "only_check": only_check or "",
        "materialization": materialization,
        "results": rows,
        "versions": versions,
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
    parser.add_argument(
        "--check",
        default=None,
        help="run only this check id; the output file gains its slug, so a "
        "partial run cannot overwrite a full matrix artifact",
    )
    args = parser.parse_args(argv)

    source = args.fixture_root / args.partition
    if not source.is_dir():
        parser.error(
            f"{source} is not there; build it first with build_python_fixtures"
        )
    # Beside that one rather than left to `run_partition`, which reaches the same
    # rejection only after copying the whole tree and running a network
    # `uv sync --frozen`. `partition` and `--grant` are validated by argparse
    # `choices`, so this is the one argument a typo in costs minutes and then
    # prints a traceback instead of a usage message. The raise stays in
    # `invocations_for`: it is that function's contract, and this only routes it
    # to the caller in the form the other arguments are rejected in.
    if args.check is not None:
        try:
            invocations_for(args.partition, only_check=args.check)
        except ValueError as err:
            parser.error(str(err))

    work_root = args.work_dir or Path(tempfile.mkdtemp(prefix="python-fixture-lens-"))
    work_root.mkdir(parents=True, exist_ok=True)
    observed = run_partition(
        args.partition,
        source,
        work_root,
        args.grant,
        args.timeout,
        only_check=args.check,
    )

    results_dir = args.fixture_root / RESULTS_DIRNAME
    results_dir.mkdir(parents=True, exist_ok=True)
    # The slug keeps a one-check run off the filename the grading pass reads as
    # the whole cell: a file of one row under that name reports a matrix nobody
    # ran, and it looks exactly like a matrix in which everything else was
    # silent.
    stem = f"{args.partition}-{args.grant}"
    if args.check:
        stem = f"{stem}-{args.check.replace('/', '-')}"
    out_path = results_dir / f"{stem}.json"
    out_path.write_text(json.dumps(observed, indent=2, sort_keys=True) + "\n")
    ran = sum(1 for r in observed["results"] if r.get("ran"))
    print(f"{args.partition} ({args.grant}): {ran} commands run, written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
