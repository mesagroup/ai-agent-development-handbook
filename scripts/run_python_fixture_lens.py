"""Run every `python:` and `typescript:` tooling entry against the seeded fixtures.

The Python half is #45's, the TypeScript half #181's. Both read the records
the same way and differ only in their tables, which carry a `TS_` prefix on the
TypeScript side; the prose below describes the Python half unless it says
otherwise, and the tables after `INVOCATIONS` are what the TypeScript half does
differently.

A row is one check record's prescribed way of running one tool, keyed by the
(check, tool) pair, and the rows come from two places. A record that declares
its commands as `routes:` data is read directly, by `routed_invocations`. A
record whose fallback still lived in prose was **transcribed verbatim** into the
table below; the table is
empty since the docs and security migration, and is the slot a legacy record
would fill if the harness invoked one again. `invocations_for` returns both
populations, the second being empty today.

Either way the point is the same, and it is the mechanism rather than the
decoration: somebody running these by hand repairs a broken command as they go
and the repair never reaches the record, whereas here the deviation needed to
make a tool work is a diff against what the record prescribes. So `argv` is
what the record says, `completion` is what had to be added for the command to
run at all, and `note` says why - and the set of rows carrying a completion is
a finding list before any tool has spoken. What changes between the two
populations is only where `argv` is read from.

A route the record does not prescribe at all is a third thing, and it is held
apart from both: `supplied_by_partition` carries a command **this round
contributed** rather than transcribed, and it never renders as `record_argv` in
the results. They are SBOM and vulnerability routes for dependency files the
record names no subcommand or mode for, so each is a candidate answer to a named
hole rather than a correction to the record - and keeping it out of `record_argv`
is what stops a later pass reading "the harness ran this" as "the record said
this". Both records that leave such a hole have migrated, so both supplied
routes now live in `SUPPLIED`, keyed `(check, tool)` beside `COMPLETIONS` - a
routed row carries one without the record ever prescribing it, which is the
whole reason the overlay exists. The hand-written table can still hold one, and
holds none.

Three fields are derived from the records rather than transcribed, because a
second copy of a fact the records already state is a copy free to drift:

* the grant tier, read per (check, tool) out of the record's own `needs`;
* which checks a partition runs, read out of `expectations_for`, so the harness
  cannot run a set the published record does not grade;
* which tools exist at all, read out of every record's `tooling` for the
  language, which is what the exact-set guard in the tests compares both
  populations against.

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
    uv run python scripts/run_python_fixture_lens.py pnpm --grant none
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
from functools import cache, lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_checks import SKILLS_DIR, Route, load_checks
from build_python_fixtures import (
    DEFAULT_OUTPUT_DIRS,
    PINNED_MANAGERS,
    PUBLIC_NPM_REGISTRY,
    _is_registry_setting,
)
from python_fixture_spec import (
    ISOLATION_TIMEOUT_SECONDS,
    PACKAGE,
    PARTITIONS,
    TS_PARTITIONS,
    _ts_source_prefix,
    expectations_for,
    lang_of,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Where `build_python_fixtures.py` writes each language's partitions, and where
# the results go - beside them, never inside one. Taken from the generator
# rather than spelled again here, so a caller moving the fixtures moves both.
FIXTURE_ROOTS = DEFAULT_OUTPUT_DIRS
RESULTS_DIRNAME = "results"

# The languages this lens runs, and for each the partitions a fixture exists
# for. The Python half is the default everywhere a function takes a `lang`,
# and a function handed a partition derives the language from it with
# `lang_of`, so a caller cannot pair a partition with the other language's
# tables.
LANGS = ("python", "typescript")
FIXTURE_PARTITIONS: dict[str, tuple[str, ...]] = {
    "python": PARTITIONS,
    "typescript": TS_PARTITIONS,
}
ALL_PARTITIONS = PARTITIONS + TS_PARTITIONS

# What a route's `argv_by_partition` may be keyed by, which is not the same set
# as the partitions a fixture exists for. A python route's keys are partition
# names, so the two coincide. A typescript route's keys are package managers,
# and the records name `yarn` where no fixture partition is yarn: a yarn key is
# a command the record prescribes for a target this round has no tree for, so
# it passes validation and applies to no partition rather than raising.
PARTITION_KEYS: dict[str, tuple[str, ...]] = {
    "python": PARTITIONS,
    "typescript": ("npm", "pnpm", "yarn"),
}

# Where a supplied route parks an intermediate it has to hand to the next step.
# Named rather than defaulted so that the file is recognisable as the harness's
# in the copy afterwards, and distinct from any manifest a partition declares -
# a step writing `requirements.txt` would overwrite the pip partition's own.
SUPPLIED_REQUIREMENTS = "audit-export-requirements.txt"

# Where every materialization route below puts the partition's own environment,
# and so what `<path-to-venv-python>` resolves to in the one command a record
# writes that placeholder into. Named here rather than beside `launcher`,
# because the completion that supplies that path reads it too.
VENV_BIN = ".venv/bin"

# The engine's status scale, and the reasons an observation of a command can
# establish. Neither tuple grows here: a fourth status would collapse a
# distinction the engine draws on purpose, and a reason arriving here that no
# run of this file can produce would be a member nothing ever exercises. Both
# are pinned
# by literal equality in the tests so that a member added to either arrives
# visibly - the round exists to test the family against this vocabulary rather
# than to extend it.
#
# `audit-core` carries a fourth reason, `not-prescribed`, and REASONS does not,
# which is deliberate rather than drift. That reason is a check's verdict on a
# partition; a row here is one invocation's observation. Where a record
# prescribes no command there is no invocation to report on, so this file has
# nothing to observe rather than an invocation with a fourth outcome.
#
# Three things in this file are outside the scale on purpose. `not-applicable`
# is a status `classify` can never return: it means the check has no lens in
# the partition's language, which is settled by the record before the harness
# runs rather than by an observation. A row for a record that prescribes no
# command carries `status: ""` - not a fourth status but the absence of one,
# because nothing ran to have a status, and that empty status is this file's
# whole representation of the case the engine reports as `not-prescribed`.
STATUSES = ("ok", "no-evidence", "not-applicable")
REASONS = ("not-permitted", "tool-unavailable", "tool-failed")

# Harness-local, and deliberately a separate field from `reason` rather than
# more reasons. Both name a way a row failed to produce evidence that the
# engine's reasons cannot tell apart on their own: a hung command reads
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

# What a route's command needs installed beside the package its record names,
# where the fixture does not declare it. The package itself is the route's own
# `package` field, read off the record by `packages_for` and placed in front of
# the command by `python_one_shot` as `audit-core`'s route-running paragraph
# writes the rule, so nothing here restates a record. What is here is harness
# plumbing no record states: **the fixture declares no pytest**, so a route whose
# command runs the target's suite has to bring one, whichever population
# supplies the row: `coverage run -m pytest` and `mutmut run` are both read from
# their records rather than transcribed here, and both die on
# `No module named pytest` otherwise, which reads as a tool that failed rather
# than as a package nobody installed - a failure this harness would have
# invented, on an entry the record had right. The pytest plugins need no entry
# because each depends on pytest already, so naming the plugin brings the runner
# with it.
HARNESS_COMPANIONS: dict[str, tuple[str, ...]] = {
    "coverage.py": ("pytest",),
    "mutmut": ("pytest",),
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
# tool either population names has an entry, `None` where it does not, and it is
# only legal beside a reason in `NO_VERSION_ROUTE`: the same shape as
# `ungranted_note`'s `none` sentinel, and for the same reason - an omitted entry
# must never read as a silent default.
#
# `grimp` and `hypothesis` carry no `argv` on any row, in either population: no
# record prescribes a command line for either, naming the tool as something the
# check computes over or inspects rather than invokes, so neither's own console
# entry point (`hypothesis` needs `click`, which nothing here installs; `grimp`
# has no console entry point at all) is what the family actually runs. Their
# probes read the installed distribution's own metadata instead, through a
# `python -c` the probe spells and nothing else: `launcher` is handed `python`
# as the command, and by `audit-core`'s rule a package that is not the
# command's name is named to the runner, so both are `in_env=False` everywhere
# and run as `uvx --from grimp python -c ...`. Measured with uvx 0.12: that
# form prints grimp's and hypothesis's versions. The probe carries no runner
# flag of its own, because `launcher` compares the probe's first word with the
# package, and a flag there would be compared as though it were the command.
#
# The four pytest plugins are the same shape and `in_env=True`: under a grant
# the tool is present in the materialized environment, added via the same
# `--with` `launcher` computes for the real check, and the bare `python -c`
# finds it; under no grant the probe falls back to the one-shot runner, which
# the same rule tells the package, so it reports the version a one-shot fetch
# resolves - measured, `uvx --from pytest-cov python -c ...` reports it where
# the bare `uvx python -c ...` raises `PackageNotFoundError` - and the route
# itself does not run, as `launcher` says.
_METADATA_VERSION = "from importlib.metadata import version; print(version({0!r}))"

VERSION_PROBE: dict[str, tuple[str, ...] | None] = {
    "ruff": ("ruff", "--version"),
    "radon": ("radon", "--version"),
    "xenon": ("xenon", "--version"),
    "grimp": ("python", "-c", _METADATA_VERSION.format("grimp")),
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
    "hypothesis": ("python", "-c", _METADATA_VERSION.format("hypothesis")),
}

# Empty on purpose rather than absent: every tool the harness enumerates, from
# the table or from a record's routes, turned out to have a working route, verified by hand against the installed package and
# against the actual command `launcher` resolves for it (not just that some
# `--version` or `importlib.metadata` form exists in isolation) - so there is
# nothing here to explain. The dict stays because `probe_versions` reads it, and
# a future tool with no route at all names itself here rather than silently
# taking `None`.
NO_VERSION_ROUTE: dict[str, str] = {}

# What a declared command form is for. A disposition says what the *record* names
# a form for, and `runs` is the only value the harness acts on. Each of the other
# two says a different thing about a form the harness does not run:
#
# * `superseded` - the record names the form and then narrows the same command,
#   the way the `--no-deps --disable-pip` pair narrows `pip-audit -r
#   <requirements>`, and the narrower form is the one it goes on to prescribe.
# * `alternative` - a second route the record keeps valid without making it the
#   default here: `cyclonedx-py environment`, more accurate where the run may
#   execute the target against its materialized tree and useless on a
#   read-only clone; `pip-licenses --format json`, the
#   same list presented machine-readably; `mutmut results`, the other of two ways
#   the record offers to read the tally; `pytest --randomly-seed=<n>`, the seeded
#   re-run the record keeps for reproducing a failing order, where the command it
#   prescribes first is `pytest` bare. Nothing narrows these and nothing warns
#   against them - the record simply prescribes something else first. Read as
#   "a route for a partition shape the fixtures lack" it fits none of them, and
#   it would make the value a claim about the fixture set rather than about the
#   record, which is the one thing a disposition never is.
#
# There is no value here for a form a record names in order to warn against, and
# that is a decision rather than a gap: a `disposition: forbidden` route
# contributes no row and no form. `routed_invocations` drops it before grouping,
# so a form the record warns against is never offered to the guards as a form
# the record prescribes, and the one property that does read those routes - no
# command a row runs starts with a forbidden argv - lives in the TypeScript
# harness tests, where the records declaring them are.
#
# What a warning looks like on a route that is not `forbidden`: records warn against
# multi-token forms, `arch/cycles` naming `pydeps --show-cycles` and saying that
# form alone has no textual output channel at all, and `deps/inventory` saying it
# has no route through `cyclonedx-py poetry` for a PEP 621 manifest. Each still
# carries the disposition describing what the record does with it - the first
# `superseded`, because the record narrows the same command; the second `runs`,
# because the harness runs it on the partition whose manifest it does read. Both
# records declare their routes now, so those two forms are derived by `_forms_for`
# and the prose extractor sees neither; they are examples of what a record does
# with a warning, not of where this module gets one from. A value with no user is
# ceremony that reads as coverage, so this tuple holds exactly the values some
# declared form carries, and a test in the suite fails when it stops doing so.
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
        tool: A name from that record's `tooling` for the row's language.
        argv: The command **as the record writes it**. Empty where the record
            names the tool without prescribing a command - a library, a reading
            pass, or a route conditional on a config file the fixture does not
            carry. An empty `argv` is a fact about the record, not a gap here.
        argv_by_partition: Where the record prescribes a different command per
            partition - `cyclonedx-py`'s subcommand "matching the partition's
            own dependency file", `pip-audit`'s mode - the command for each,
            as `(partition, argv)` pairs. Derived from the route's
            `argv_by_partition` for every row that carries one today; a
            hand-written entry would transcribe them, and none does. A partition paired
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
        completion_by_partition: A completion that differs per partition, as
            `(partition, tokens)` pairs appended after `completion`. The
            TypeScript half needs it where an operand is a path into the seeded
            package, which is the tree root on npm and a workspace member on
            pnpm; the Python partitions share one layout and leave it empty.
        fills: Placeholders the record writes in its argv, as
            `(placeholder, value)` pairs substituted into the command a row runs
            and never into `prescribed`. Appending cannot complete one inside a
            token, `--sequence.seed=<n>`, or one standing before or between
            other tokens, dependency-cruiser's `--ts-config <tsconfig> <dir>`,
            so a fill is the other shape a completion takes, and it travels
            under the same `note`. A value only `run_partition` knows, such as
            `<report-path>`'s file in the run's work root, is filled with a
            token resolved there, `REPORT_PATH_TOKEN`, so a row's recorded
            `fills` shows the token rather than the path.
        then: A second command the record prescribes in sequence, where it does -
            `coverage run -m pytest` followed by `coverage report --show-missing`
            is one route, not two, and dropping the half that prints the report
            would leave the route looking like a tool that produced nothing.
            The order is the route's: `argv` and `then` are two fields of one
            route, read in that order by `routed_invocations`, and the suite
            holds that some route in the tree still carries one.
        note: Why the completion was needed. Required whenever `completion`
            is non-empty.
        in_env: Whether the tool has to run from inside the materialized
            environment rather than through a one-shot runner.
        findings_stream: Which stream this tool writes its report to, and so
            which one `classify` reads to tell a tool that answered from one
            that failed. `stdout` is the default and a record says otherwise on
            the route, which deptry and xenon each do: deptry writes its
            whole report to stderr and leaves stdout empty, and xenon
            reports its breach there with stdout empty too. Both are
            measured, and they are the reason this is a field rather than an
            assumption: read on stdout, a deptry run that finds every
            planted seed grades as a tool failure and one that finds nothing
            grades clean, which is the classification exactly inverted on
            the entry the fixture was seeded for. The count is not stated
            here because it is a fact about the records rather than about
            this field - `grep findings_stream` over the check tree is the
            answer, and a third record adding one must not have to find this
            sentence.
        package: The package a one-shot runner fetches for this tool, read from
            the routes' `package` field, which the loader fills with the tool's
            name where the record names none. Empty only on a row built by hand,
            which then fetches the tool by its name.
        alone_insufficient: What the route's own result still needs before it is
            the check's answer, read from the route this row runs - the `runs`
            command route where there is one, otherwise the caveats of the
            group's routes as `_caveat_for_no_command` composes them - and written
            onto the results row under the same key. Empty where the route's
            result stands alone. Where the group has a `runs` route the field is
            not held consistent across it the way `findings_stream` is: a
            `superseded` route's caveat is about that route, and only the one
            the row runs says what the row's result lacks. The status a row
            carries is unchanged by it - `audit-core`'s
            scale does not grow - so it is the row's other field a reader, and
            the grader, has to read to see that an `ok` with a hit is a
            candidate rather than the check answered.
        forms: Every command form this record prescribes for this route, as
            `(form, disposition)` pairs, derived by `_forms_for` from the
            route's `argv`, `argv_by_partition` and `then`. The declaration is
            what the coverage and disposition properties compare against the
            commands the row runs.

            A form is not always led by this entry's tool, so the declaration is
            keyed on the route rather than on the name: the record prescribes
            `pytest --randomly-seed=<n>` for `pytest-randomly` and `uv export
            --format=cyclonedx1.5 --frozen` where `cyclonedx-py` has no uv
            subcommand, and a declaration keyed on the tool's name would hold
            nothing for either while the record went on prescribing it.

            A disposition is a claim about the record and not about this table:
            it says what the record names the form for, never whether anything
            here runs it.
            The two can still diverge, inside bounds the suite now sets. A form
            declared `runs` that no argv carries fails the coverage property. A
            form the harness runs as written while declaring it `superseded` or
            `alternative` fails the property holding prescribed and completed
            commands against the non-`runs` declarations - whether the record
            prescribed the whole of it or a completion supplied the rest.
            Flipping the last `runs` form off an entry fails the property
            requiring an entry that declares forms to declare one it runs,
            before any argv is touched, which is what keeps a disposition from
            working as a per-form off-switch. What is left is narrower and stated
            where it is held: a non-`runs` form run as a strict prefix plus an
            unrelated token, and a disposition simply wrong about its record,
            which no extraction can read out of prose.
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
    argv: tuple[str, ...] = ()
    argv_by_partition: tuple[tuple[str, tuple[str, ...]], ...] = ()
    supplied_by_partition: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = ()
    supplied_note: str = ""
    own_runner: tuple[str, ...] = ()
    completion: tuple[str, ...] = ()
    completion_by_partition: tuple[tuple[str, tuple[str, ...]], ...] = ()
    fills: tuple[tuple[str, str], ...] = ()
    then: tuple[str, ...] = ()
    note: str = ""
    in_env: bool = False
    package: str = ""
    findings_stream: str = "stdout"
    forms: tuple[tuple[str, str], ...] = ()
    alone_insufficient: str = ""

    def __post_init__(self) -> None:
        if (self.completion or self.completion_by_partition or self.fills) and (
            not self.note
        ):
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
        """The four ways a supplied route would stop being distinguishable.

        A partition carrying two routes, a partition named twice, an entry
        with no note, and a supplied route beside `in_env`. Two of those four
        are properties of `supplied_by_partition` alone and `Supplied` rejects
        them too, which is deliberate rather than a split nobody finished: the
        two populations reach a row by different doors. A hand-written
        `INVOCATIONS` entry constructs an `Invocation` directly and never
        builds a `Supplied` at all, so a check that only lived there would
        leave that door unguarded, and an overlay entry reaches this method
        only once its fields have been copied onto a row, so a check that only
        lived here would name the row rather than the literal the mistake is
        in. Every supplied route in the tree comes through the overlay today -
        both records that leave a hole have migrated - so this method is
        currently the second guard on all of them rather than the only guard
        on any. That is a fact about the records, not about the door: the
        constructor is public to the table and the table can still carry one.
        What would be a defect is the two disagreeing about which shapes they
        reject.
        """
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


# The plugin runtime's variable for the directory its install lives in. A route
# spells a file the plugin ships under it - dependency-cruiser's `--config` -
# because a path relative to the skill directory resolves nowhere a run's working
# directory is. A fixture run is a run from this checkout, so the variable stands
# for the checkout root. It is expanded where the command is composed rather than
# as a fill: the record left nothing to the caller here, the token is complete
# as written, and `record_argv` keeps it literal so a reader sees what the
# record says. A literal `${CLAUDE_PLUGIN_ROOT}` reaching the tool is the lens's
# defect, not the record's.
PLUGIN_ROOT_VARIABLE = "${CLAUDE_PLUGIN_ROOT}"


def plugin_root(skill_dir: Path) -> Path:
    """The plugin's install directory, from the base directory of any of its skills.

    `audit-core`'s route-running paragraph tells a run where the directory comes
    from: three levels above the base directory Claude Code prints for a skill,
    which is `.agents/skills/<skill>/` under it. The shell a run's commands use
    does not set the variable - measured in a Claude Code session - so this is
    the derivation a sweep makes, and the lens makes the same one rather than
    reading a constant that could agree with the engine by accident.
    """
    return skill_dir.parents[2]


def expand_plugin_root(command: Sequence[str]) -> tuple[str, ...]:
    """`command` with the plugin root variable expanded as the engine says to.

    The root is derived from `audit-core`'s own skill directory by
    `plugin_root`, which in a fixture run is this checkout's root.
    """
    root = str(plugin_root(SKILLS_DIR / "audit-core"))
    return tuple(token.replace(PLUGIN_ROOT_VARIABLE, root) for token in command)


def argv_for(invocation: Invocation, partition: str) -> tuple[str, ...]:
    """The command this entry runs on one partition, completion included.

    Returns `()` where the record prescribes no command, which is a reading pass
    rather than a failure - the caller records it as such instead of running
    nothing and blaming a tool.
    """
    if partition not in ALL_PARTITIONS:
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {ALL_PARTITIONS}"
        )
    base = invocation.prescribed(partition)
    if not base:
        return ()
    filled = base
    for placeholder, value in invocation.fills:
        filled = tuple(token.replace(placeholder, value) for token in filled)
    per_partition = dict(invocation.completion_by_partition).get(partition, ())
    return filled + invocation.completion + per_partition


@dataclass(frozen=True)
class Completion:
    """What a partition needed that the record did not say, and why.

    Round-owned, which is the whole reason it is here and not in the record:
    a record whose command needs completing is a record to correct, and the
    completion is this round's report of that. `tokens` never reaches the
    prescribed command, so what the record said stays distinguishable from
    what the audit added.
    """

    tokens: tuple[str, ...]
    note: str

    def __post_init__(self) -> None:
        if not self.tokens:
            raise ValueError("a completion with no tokens is not a completion")
        if not self.note:
            raise ValueError(
                "a completion needs the reason it was needed; unexplained, it "
                "reports a repaired command as a clean run"
            )


# Keyed `(check, tool)` to match a row rather than a record: a tool answering
# two checks may need completing for one and not the other.
COMPLETIONS: dict[tuple[str, str], Completion] = {
    ("arch/complexity", "radon"): Completion(
        tokens=("src",),
        note=(
            "`radon cc` takes a path and the record names none; ruff defaults "
            "to the working directory and radon does not, so the same sentence "
            "is runnable for one tool and not the other"
        ),
    ),
    ("arch/complexity", "xenon"): Completion(
        tokens=("--max-absolute", "B", "src"),
        note=(
            "the record names the tool and no arguments; xenon needs both a "
            "threshold and a path, and the expectation is written against "
            "`--max-absolute B`"
        ),
    ),
    ("security/crypto", "bandit"): Completion(
        tokens=(f"src/{PACKAGE}",),
        note=(
            "`<pkg>` is a placeholder the record leaves to the caller and the route "
            "stops at `-r`; the seeded package is at src/" + PACKAGE
        ),
    ),
    ("security/dangerous-calls", "bandit"): Completion(
        tokens=(f"src/{PACKAGE}",),
        note=(
            "`<pkg>` is a placeholder the record leaves to the caller and the route "
            "stops at `-r`; the seeded package is at src/" + PACKAGE
        ),
    ),
    ("security/injection", "bandit"): Completion(
        tokens=(f"src/{PACKAGE}",),
        note=(
            "`<pkg>` is a placeholder the record leaves to the caller and the route "
            "stops at `-r`; the seeded package is at src/" + PACKAGE
        ),
    ),
    ("security/unsafe-io", "bandit"): Completion(
        tokens=(f"src/{PACKAGE}",),
        note=(
            "`<pkg>` is a placeholder the record leaves to the caller and the route "
            "stops at `-r`; the seeded package is at src/" + PACKAGE
        ),
    ),
    ("arch/cycles", "pydeps"): Completion(
        tokens=(f"src/{PACKAGE}",),
        note="pydeps takes the package to graph and the record names none",
    ),
    ("arch/dead-code", "vulture"): Completion(
        tokens=("src", "tests"),
        note=(
            "vulture takes the paths to scan and the record names none; both "
            "trees are passed because a symbol referenced only by a test is "
            "not dead, and scanning src alone would report the suite's own "
            "callees as unused"
        ),
    ),
    # The flag the path completes is the record's, not this table's: measured,
    # `uv pip list --outdated` with the interpreter unnamed prints nothing at
    # exit 0 on a partition whose environment has three outdated packages,
    # because an inner `uv` - the command rather than the thing running it -
    # does its own environment resolution and does not inherit the `--python`
    # the overlay already named. The record's route names the interpreter
    # explicitly for that reason and stops at the flag, so the only thing left
    # to supply here is the path.
    ("deps/freshness", "uv"): Completion(
        tokens=(f"{VENV_BIN}/python",),
        note=(
            "`<path-to-venv-python>` is a placeholder the record leaves to the caller; "
            "it resolves to the interpreter the partition's own materialization built "
            "inside the copy this run owns"
        ),
    ),
    ("deps/hygiene", "deptry"): Completion(
        tokens=(".",),
        note=(
            "deptry takes a scan root and the record's argv stops short of it; its "
            "note gives the root as `.` with the target as the working directory, "
            "and the answer moves with it - `deptry src` makes the package local and "
            "the self-import rows vanish - so this completion supplies `.`"
        ),
    ),
    ("test/coverage-reach", "pytest-cov"): Completion(
        tokens=(f"--cov={PACKAGE}",),
        note=(
            "`<pkg>` is a placeholder the record leaves to the caller; the seeded "
            "package is " + PACKAGE
        ),
    ),
    ("test/isolation", "pytest-timeout"): Completion(
        tokens=(f"--timeout={ISOLATION_TIMEOUT_SECONDS}",),
        note=(
            "the record prescribes `--durations=25`, which is core pytest and never "
            "exercises pytest-timeout, the tool the record names; the timeout comes "
            "from the fixture's own ISOLATION_TIMEOUT_SECONDS, which the expectation "
            "is written against"
        ),
    ),
}


@dataclass(frozen=True)
class Supplied:
    """A route this round contributed where the record prescribes none.

    Round-owned for the reason `Completion` is: the record naming no route for
    a partition is a hole in the record, and this is the candidate answer this
    round tests against it. Keyed `(check, tool)` beside `COMPLETIONS`, so a
    migrated record's supplied route lives where its completion does rather
    than in the record that, by definition, does not prescribe it.

    Validates the shape of what it holds: a steps tuple that is empty, a
    partition named twice, a missing note, or a step with no tokens. Which
    door catches which matters more than the overlap's size, so: `Supplied`
    rejects all four, and `Invocation._check_supplied` rejects two of them, a
    partition named twice and a missing note. An empty `by_partition` and a
    step with no tokens reach an `Invocation` unrejected, which is safe only
    because every supplied route in the tree is written here first - a
    hand-written entry passing `supplied_by_partition` directly would meet
    neither check. `_check_supplied` holds two shapes this class cannot see at
    all, being about the rest of the row: a partition carrying both a
    prescribed route and a supplied one, and a supplied route beside `in_env`.
    Failing here rather than there is the better failure where both fire, at
    the literal carrying the mistake rather than at the row it is copied onto.
    """

    by_partition: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]
    note: str

    def __post_init__(self) -> None:
        if not self.by_partition:
            raise ValueError("a supplied route with no steps is not a route")
        if not self.note:
            raise ValueError(
                "a supplied route needs the reason the record has none; "
                "unexplained, it reads as a command the record prescribed"
            )
        named = [partition for partition, _ in self.by_partition]
        if len(named) != len(set(named)):
            raise ValueError(
                f"names a partition twice in a supplied route ({named}), so "
                "one of the two never runs"
            )
        for partition, steps in self.by_partition:
            for step in steps:
                if not step:
                    raise ValueError(
                        f"{partition}: a supplied route step with no tokens "
                        "would hand the runner an empty command to execute, "
                        "which reports as a tool that failed rather than as "
                        "the hole in the record it actually is"
                    )


# The round's own contributions, for a partition a migrated record prescribes
# no route for. Both entries are that shape: `deps/inventory` names no
# subcommand for a PEP 751 lock file, and `deps/vulnerabilities` names no mode
# for a uv tree, so on those two partitions the records' own routes run
# nothing. Each stays here rather than moving into the record beside the routes
# it answers, for the reason a completion does: a record declaring a supplied
# route would be prescribing it, and the whole point is that it never renders
# as `record_argv`.
SUPPLIED: dict[tuple[str, str], Supplied] = {
    ("deps/inventory", "cyclonedx-py"): Supplied(
        by_partition=(
            ("pylock", (("uvx", "cyclonedx-py", "requirements", "pylock.toml"),)),
        ),
        note=(
            "the record's first named hole: it names no route at all for a PEP 751 "
            "file, and this step points the requirements subcommand at one, so it is "
            "a candidate this round tests rather than a correction it has made. It "
            "never reaches record_argv, which stays the record's own command per "
            "partition, and the record prescribes none on this one"
        ),
    ),
    ("deps/vulnerabilities", "pip-audit"): Supplied(
        by_partition=(
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
        note=(
            "the record's second named hole: it names no mode for a uv tree, so a "
            "uv-locked partition has no vulnerability lens on a read-only clone. The "
            "candidate is an export written to a file - pip-audit's `-r` takes a path "
            "rather than a pipe - and then the `-r` mode the record does name. The "
            "record mentions `uv export --frozen` only to say what a fully resolved "
            "requirements file contains, and prescribes no export-then-audit route for "
            "a uv tree, so the route as a whole is this round's. Supplied for uv "
            "alone: the same export is what a poetry or pipenv partition has no "
            "lockfile for - `uv export --frozen` reads a uv.lock and those "
            "partitions carry none by construction - so there is no equivalent "
            "route to supply them"
        ),
    ),
}


# The transcription, one entry per (check, tool) pair, for a record whose command
# lives in prose rather than in a route. Empty since the docs and security
# migration: every record the Python fixture harness invokes now declares
# `routes:`, so every row comes from `routed_invocations` and nothing here is
# read from a `## Tooling fallback` section. The shape is kept, rather than the
# name retired, until the legacy readers are retired: the loader now refuses a
# record-level `tooling:`, so no record on a real tree can put a row here.
INVOCATIONS: tuple[Invocation, ...] = ()


# ---------------------------------------------------------------------------
# The TypeScript half's tables (#181). Each is the counterpart of a Python table
# above and is held to an exact set by `tests/scripts/test_typescript_fixture_harness.py`,
# for the reason the Python tables are: a key missing from one of these must
# fail a test rather than read as a silent default.
# ---------------------------------------------------------------------------

# How each TypeScript partition's tree is materialized, run only inside the copy
# `reconstruct` makes and never in `fixtures/typescript`. Both install from the
# committed lockfile and refuse to refresh it - `npm ci` by construction, pnpm
# by `--frozen-lockfile` - for the reason `MATERIALIZE` gives: a resolution the
# fixture never committed is a different tree from the one the expectations
# were written against. `--ignore-scripts` because nothing seeded needs an
# install hook, and a hook is target code running before the grant that
# permits it has been checked. `pnpm` resolves to corepack's shim, which reads
# the tree's own `packageManager` pin, through the directory `TS_SHIM_COMMAND`
# writes and `_ts_fixture_env` puts first on PATH.
TS_MATERIALIZE: dict[str, tuple[tuple[str, ...], ...]] = {
    "npm": (("npm", "ci", "--ignore-scripts"),),
    "pnpm": (("pnpm", "install", "--frozen-lockfile", "--ignore-scripts"),),
}

# The partitions whose package manager comes from corepack rather than from the
# host, and where its shim goes. npm is the host's own and the fixture build
# already held it to the pin; pnpm is not a host tool, so it is enabled into a
# directory under the run's work root - beside the copy rather than inside it,
# since the copy is the tree the tools read - before anything on that partition
# runs, the ungranted run included, because `pnpm audit` needs no grant.
TS_COREPACK_MANAGED = ("pnpm",)
TS_SHIM_DIRNAME = "corepack-shims"


def ts_shim_command(manager: str, shim_dir: Path) -> tuple[str, ...]:
    """The command that puts corepack's shim for `manager` in `shim_dir`."""
    return ("corepack", "enable", manager, "--install-directory", str(shim_dir))


# Which package manager owns each subcommand a record names as a tool. Such a
# tool is not a package: no one-shot runner fetches `npm audit`, and it runs on
# the partition whose manager it belongs to and on no other - `npm audit` on a
# pnpm tree is `ENOLOCK`, as the TypeScript smoke run measured, and that is an
# observation about pointing the wrong manager at a tree rather than about the
# tool. So a row keyed on one of these takes no launcher prefix, and on a
# partition managed by something else it is recorded as not run, with the
# reason. A yarn tool runs on no partition, because no fixture is yarn.
TS_MANAGER_TOOLS: dict[str, str] = {
    "npm audit": "npm",
    "npm outdated": "npm",
    "npm sbom": "npm",
    "pnpm audit": "pnpm",
    "pnpm outdated": "pnpm",
    "pnpm licenses list": "pnpm",
    "yarn npm audit": "yarn",
    "yarn licenses list": "yarn",
}

# The words in front of a TypeScript command, per partition. A one-shot fetch
# names the package rather than leaning on the command name, which is what the
# records themselves do on every fetcher-led route: `dependency-cruiser`'s bin
# is `depcruise`, and a bare `npx depcruise` is the dependency-confusion
# placeholder the records forbid. On pnpm the flag precedes `dlx`, as the
# records spell it, because `pnpm dlx --package=` reads the flag as a package
# spec. An `in_env` tool under a grant runs the tree's own copy instead:
# `npx --no` declines to fetch, though it still resolves a copy from npx's own
# cache, so a tool that runs is no proof the tree carries it, and `pnpm exec`
# runs whatever its PATH holds, the workspace's own bin first. `--no` rather than the older
# `--no-install`, which npm 11's own documentation calls deprecated and
# converts to `--no`, so the spelling is what actually runs. The `--` ends
# npx's own options, as it does in the one-shot form: without it npx reads a
# trailing flag as its own, so the version probe `npx --no vitest --version`
# printed npm's version rather than vitest's. The pnpm config flag turns off
# `verifyDepsBeforeRun`, which pnpm 11 defaults to `install`: `pnpm exec` then
# installs into the tree before running whenever it judges `node_modules` out
# of date, outside the frozen, scripts-off build `TS_MATERIALIZE` made.
# Measured on a scratch project with a dependency added after install: pnpm
# 11.28.5's bare `pnpm exec` installed it, and the flagged form did not; pnpm
# 9.15.9, the fixtures' pin, accepts the flag and runs the command unchanged.
TS_ONE_SHOT: dict[str, tuple[str, ...]] = {
    "npm": ("npx", "--yes", "--package={package}", "--"),
    "pnpm": ("pnpm", "--package={package}", "dlx"),
}
TS_IN_ENV: dict[str, tuple[str, ...]] = {
    "npm": ("npx", "--no", "--"),
    "pnpm": ("pnpm", "--config.verify-deps-before-run=false", "exec"),
}

# What reports each TypeScript tool's version, after the launcher's prefix. A
# manager subcommand reports its manager's version, and runs bare for the reason
# `TS_MANAGER_TOOLS` gives. A fetched tool's probe spells the bin, which is not
# always the package: `depcruise`, `ncu` and `cdxgen` are the bins of
# `dependency-cruiser`, `npm-check-updates` and `@cdxgen/cdxgen`, and the
# launcher names the package. `None` is legal only beside a reason in
# `TS_NO_VERSION_ROUTE`, as on the Python side.
TS_VERSION_PROBE: dict[str, tuple[str, ...] | None] = {
    "npm audit": ("npm", "--version"),
    "npm outdated": ("npm", "--version"),
    "npm sbom": ("npm", "--version"),
    "pnpm audit": ("pnpm", "--version"),
    "pnpm outdated": ("pnpm", "--version"),
    "pnpm licenses list": ("pnpm", "--version"),
    "madge": ("madge", "--version"),
    "dependency-cruiser": ("depcruise", "--version"),
    "vitest": ("vitest", "--version"),
    "jest": ("jest", "--version"),
    "c8": ("c8", "--version"),
    "npm-check-updates": ("ncu", "--version"),
    "@cdxgen/cdxgen": ("cdxgen", "--version"),
    "osv-scanner": None,
}

TS_NO_VERSION_ROUTE: dict[str, str] = {
    "osv-scanner": (
        "a standalone binary in no language registry, so neither `npx` nor "
        "`pnpm dlx` can obtain it, and the record's route for it is a procedure "
        "prescribing no command; a probe through either launcher would fetch "
        "whatever the registry carries under that name instead"
    ),
}

# What a non-zero exit from each TypeScript tool means, in `NONZERO_EXIT_KINDS`.
# Each `findings` entry is from the tool's own documentation or source rather
# than assumed: `npm audit`, `pnpm audit`, `npm outdated` and `pnpm outdated` exit
# 1 when they find a vulnerable or outdated dependency (pnpm's source returns
# `exitCode: outdatedPackages.length === 0 ? 0 : 1`, and the same for audit's
# advisories); madge's CLI sets exit code 1 when `--circular` finds a cycle;
# dependency-cruiser exits with the count of error-severity violations, which
# under the rule-less config the plugin ships is never more than zero, so on
# those routes a non-zero exit carries no findings on stdout and classifies as
# the failure it is; and
# vitest and jest exit 1 on a failing test, which is the planted finding for
# `test/determinism`. `npm sbom`, `pnpm licenses list` and `@cdxgen/cdxgen` are
# reporting commands with no gating flag in the prescribed invocation - cdxgen's
# gates are `--fail-on-error` and `--introspect-fail-below`, and the record's argv
# passes neither - so nothing establishes that their non-zero exit is ever a
# finding, and they are `ambiguous`.
TS_NONZERO_EXIT_MEANING: dict[str, str] = {
    "npm audit": "findings",
    "pnpm audit": "findings",
    "npm outdated": "findings",
    "pnpm outdated": "findings",
    "madge": "findings",
    "dependency-cruiser": "findings",
    "vitest": "findings",
    "jest": "findings",
    "npm sbom": "ambiguous",
    "pnpm licenses list": "ambiguous",
    "@cdxgen/cdxgen": "ambiguous",
}

# The shuffle seed `test/determinism` fills its `<n>` with. Measured, never
# guessed: the TypeScript build smoke record names seed 3 as the smallest
# non-zero seed that reverses the order-dependent pair under vitest 5.0.2, and
# names why it prefers 3 to the smaller 0, which a reader may take for a falsy
# default. It was measured on the npm partition only; whether it reverses the
# pair on pnpm is what the run records.
TS_SHUFFLE_SEED = 3


@dataclass(frozen=True)
class TsCompletion:
    """What a TypeScript command needed that the record did not say, per partition.

    `Completion`'s counterpart, with two differences the TypeScript fixtures
    force. A path operand differs by partition, because the seeded package is the
    tree root on npm and `packages/core` on pnpm, so `by_partition` carries the
    tokens per partition. And a placeholder can sit inside a token, or stand
    as a token among others, which appending cannot complete, so `fills`
    substitutes it. A row `TS_RUN_IN_PACKAGE` names runs from the seeded package
    instead, so its fills are package-relative and the same on both partitions.
    All of them stay out of the record's own argv, as a completion does.
    """

    note: str
    by_partition: tuple[tuple[str, tuple[str, ...]], ...] = ()
    fills: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not (self.by_partition or self.fills):
            raise ValueError("a completion with no tokens and no fills is not one")
        if not self.note:
            raise ValueError(
                "a completion needs the reason it was needed; unexplained, it "
                "reports a repaired command as a clean run"
            )
        for partition, tokens in self.by_partition:
            if partition not in TS_PARTITIONS or not tokens:
                raise ValueError(
                    f"{partition}: a per-partition completion names a TypeScript "
                    "partition and carries at least one token"
                )


def _seeded(partition: str, path: str) -> str:
    """`path` inside the seeded package, as it lands in this partition's tree."""
    return f"{_ts_source_prefix(partition)}{path}"


def _per_ts_partition(*paths: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        (partition, tuple(_seeded(partition, path) for path in paths))
        for partition in TS_PARTITIONS
    )


_TS_DEPCRUISE_COMPLETION = TsCompletion(
    fills=(("<tsconfig>", "tsconfig.json"), ("<dir>", "src")),
    note=(
        "`<tsconfig>` and `<dir>` are the two operands the record leaves to the "
        "caller: the seeded package's own tsconfig.json, which carries the "
        "compiler options rather than only `references`, and its src/. Both are "
        "relative to the seeded package, which the row runs from, as "
        "`TS_RUN_IN_PACKAGE` says"
    ),
)

# The TypeScript rows that run from the seeded package's own directory - the tree
# root on npm, packages/core on pnpm - rather than from the tree root, keyed
# `(check, tool)` with the record's reason. dependency-cruiser resolves the
# `include` of the tsconfig `--ts-config` names against its working directory
# rather than against the tsconfig's own: measured on the pnpm fixture, run from
# the root with `--ts-config packages/core/tsconfig.json packages/core/src` it
# exits 1 with TS18003, no inputs found for `include` `["src","test"]`, and run
# from packages/core with `--ts-config tsconfig.json src` it builds the graph.
# The record's note says the command runs from the directory holding the
# tsconfig, and this table is that sentence for the rows the lens runs.
_FROM_THE_TSCONFIG = (
    "dependency-cruiser resolves the tsconfig's `include` against its working "
    "directory, so the route runs from the directory holding `<tsconfig>`"
)
TS_RUN_IN_PACKAGE: dict[tuple[str, str], str] = {
    ("arch/cycles", "dependency-cruiser"): _FROM_THE_TSCONFIG,
    ("arch/coupling", "dependency-cruiser"): _FROM_THE_TSCONFIG,
    ("arch/over-decomposition", "dependency-cruiser"): _FROM_THE_TSCONFIG,
}


def workdir_for(invocation: Invocation, partition: str) -> str:
    """Where in the copy this row runs, relative to its root; `""` is the root."""
    if lang_of(partition) != "typescript":
        return ""
    if (invocation.check, invocation.tool) not in TS_RUN_IN_PACKAGE:
        return ""
    return _ts_source_prefix(partition).rstrip("/")


# What a route's report-file placeholder is filled with: a token, because the
# file it stands for is named per run - outside the copy, in the run's own work
# root - and `run_partition` is the only place that knows the root. The record
# writes `<report-path>` where its tool must be handed a file to write: vitest's
# JSON reporter writes `.vitest/json/output.json` under the project otherwise,
# measured on the seeded npm fixture with vitest 5.0.2, which the no-writes
# invariant bars.
REPORT_PATH_TOKEN = "{report_path}"

TS_COMPLETIONS: dict[tuple[str, str], TsCompletion] = {
    ("arch/cycles", "madge"): TsCompletion(
        by_partition=_per_ts_partition("tsconfig.json", "src"),
        note=(
            "`--ts-config` takes the partition's own tsconfig, which the record "
            "says it can name no single value for, and madge takes the directory "
            "to graph, which the record names none for; both are in the seeded "
            "package, the tree root on npm and packages/core on pnpm"
        ),
    ),
    ("arch/cycles", "dependency-cruiser"): _TS_DEPCRUISE_COMPLETION,
    ("arch/coupling", "dependency-cruiser"): _TS_DEPCRUISE_COMPLETION,
    ("arch/over-decomposition", "dependency-cruiser"): _TS_DEPCRUISE_COMPLETION,
    ("test/isolation", "vitest"): TsCompletion(
        fills=(("<report-path>", REPORT_PATH_TOKEN),),
        note=(
            "`<report-path>` is the file the record leaves to the caller for the "
            "JSON report; the round names one in its work root, outside the copy, "
            "and reads it back into the row as `report`"
        ),
    ),
    ("test/determinism", "vitest"): TsCompletion(
        fills=(("<n>", str(TS_SHUFFLE_SEED)),),
        note=(
            "`<n>` is the seed the record leaves to the caller; the value is the "
            "one the TypeScript build smoke record measured as reversing the "
            "order-dependent pair"
        ),
    ),
}


@dataclass(frozen=True)
class AppliesWhen:
    """Whether a route's `applies_when` holds on the TypeScript fixtures, and why.

    A route carrying the field says what the target must carry for it to apply,
    in prose no harness can evaluate. Answered here once per row, from what the
    fixtures were built to carry, so a row whose precondition fails is recorded
    as not run for that reason rather than run and graded as a tool that broke.
    """

    holds: bool
    why: str

    def __post_init__(self) -> None:
        if not self.why:
            raise ValueError("an applies_when answer needs the fixture fact behind it")


# Keyed `(check, tool)` to match a row. Every TypeScript row whose prescribed
# route carries `applies_when` has an entry, whether or not its check is in the
# expectations this round grades, so a record adding a precondition fails a test
# instead of running on a fixture it does not describe. The answer is the same
# on both partitions, because both carry the same seeded package.
_VITEST = AppliesWhen(
    True,
    "both partitions declare vitest as their runner, and the seeded tests import it",
)
_NOT_JEST = AppliesWhen(
    False, "neither partition declares jest; the fixtures' runner is vitest"
)
_NOT_YARN_CLASSIC = AppliesWhen(
    False, "no fixture partition is on Yarn Classic; the partitions are npm and pnpm"
)
TS_APPLIES_WHEN: dict[tuple[str, str], AppliesWhen] = {
    ("arch/cycles", "madge"): AppliesWhen(
        True,
        "the seeded tsconfig.json extends nothing, so no base config lives in "
        "node_modules",
    ),
    ("arch/layering", "dependency-cruiser"): AppliesWhen(
        False,
        "the fixtures carry no .dependency-cruiser config of their own; planting "
        "one would have the fixture declare the boundary the check tests",
    ),
    ("test/coverage-reach", "vitest"): _VITEST,
    ("test/coverage-reach", "jest"): _NOT_JEST,
    ("test/determinism", "vitest"): _VITEST,
    ("test/determinism", "jest"): _NOT_JEST,
    ("test/isolation", "vitest"): _VITEST,
    ("deps/licenses", "yarn licenses list"): _NOT_YARN_CLASSIC,
    ("deps/transitive-licenses", "yarn licenses list"): _NOT_YARN_CLASSIC,
}


def not_run_on(invocation: Invocation, partition: str) -> tuple[str, str] | None:
    """Why a row that prescribes a command does not run on this partition, if so.

    Returns `(kind, why)` - `manager` where the tool is another manager's
    subcommand, `applies-when` where the route's precondition fails on the
    fixture - or `None` where the row runs. Always `None` on a Python partition:
    no python route is manager-owned or carries a precondition this lens reads.
    """
    if lang_of(partition) != "typescript":
        return None
    manager = TS_MANAGER_TOOLS.get(invocation.tool)
    if manager is not None and manager != partition:
        return (
            "manager",
            f"`{invocation.tool}` is {manager}'s own subcommand and this partition's "
            f"package manager is {partition}, so it has no lockfile of {manager}'s "
            "to read",
        )
    answer = TS_APPLIES_WHEN.get((invocation.check, invocation.tool))
    if answer is not None and not answer.holds:
        return ("applies-when", f"the route's applies_when does not hold: {answer.why}")
    return None


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


def tools_named_in_records(lang: str = "python") -> set[str]:
    """Every tool any record offers for `lang`.

    Read from the records rather than listed here, so a tool added to a record
    and missing from its routes fails the exact-set guard instead of going
    unexercised behind a full-looking run.
    """
    return {
        tool for check in _records().values() for tool in check.tooling.get(lang, ())
    }


def grant_tier(check: str, tool: str, lang: str = "python") -> str:
    """What the command this row runs needs present before it answers.

    Derived from the record's own tier rather than transcribed beside the
    invocation: a copy of a tier the record already states is a copy free to
    drift, and the drift would be invisible - a tool run under the wrong grant
    still produces output.

    **On a migrated record the tier is the prescribed route's, not the tool's.**
    `run_partition` gates one thing on this - whether the row's command may run
    at all - and the command it would run is the `disposition: runs` route's.
    `record.needs` cannot answer that, because `_project_needs` collapses a
    record's routes onto their tools: `deps/inventory` prescribes
    `cyclonedx-py` subcommands that read a dependency file and, as an
    `alternative`, `cyclonedx-py environment`, which reads the installed
    environment by starting its interpreter and carries `target-execution`
    for it. Reading the projected pair
    makes one tiered `alternative` route withhold the whole row, so at
    `--grant none` a check that answers from a lockfile reports
    `no-evidence (not-permitted)` having run nothing - a silence that reads as
    a result, produced by a tier the record was right to declare.

    The same reading per route is why `deps/inventory` does not have to state
    an ungranted expectation: see
    `audit_checks._languages_whose_tools_all_need_a_grant`, which asks the
    neighbouring question about the record rather than about one row.

    A record on the legacy schema has no routes to read, and its tier is per
    tool by construction, so it keeps the projected reading; the loader refuses
    one outside `legacy_schema=True`, so the branch goes with the legacy readers.

    Returns:
        `resolved-tree`, `target-execution`, or the empty string where the
        command this row runs answers from a read-only clone.
    """
    checks = _records()
    if check not in checks:
        raise ValueError(f"no check record {check!r}")
    record = checks[check]
    if tool not in record.tooling.get(lang, ()):
        raise ValueError(f"{check} does not offer {tool!r} for {lang}")
    if record.routes:
        prescribed = [
            route
            for route in record.routes
            if route.lang == lang
            and route.tool == tool
            and route.kind == "command"
            and route.disposition == "runs"
        ]
        if prescribed:
            return prescribed[0].needs or ""
    for tier, tools in record.needs.items():
        if tool in tools:
            return tier
    return ""


def _partition_keys(
    check: str, tool: str, route: object, lang: str = "python"
) -> tuple[str, ...]:
    """The route's per-partition keys, checked against `PARTITION_KEYS[lang]`.

    Held for every command route rather than only the `runs` one, because a
    form is derived from every command route: a key outside the vocabulary on a
    `superseded` route would contribute a form no partition could ever run,
    which reads as a record whose prescription the harness ignores.

    Raises:
        ValueError: If the route names a key that is not a partition of
            this lens. It would thread into an entry `prescribed` never finds,
            so the command would silently never run.
    """
    keys = PARTITION_KEYS[lang]
    unknown = sorted(set(route.argv_by_partition) - set(keys))
    if unknown:
        raise ValueError(
            f"{check}/{tool}: argv_by_partition names {unknown}, which is not a "
            f"partition of this lens ({list(keys)}); a {lang} route's keys "
            "are partition names, and one that is not would thread into a "
            "command no partition ever runs"
        )
    return tuple(route.argv_by_partition)


def _forms_for(
    check: str, tool: str, route: object, lang: str = "python"
) -> tuple[tuple[str, str], ...]:
    """Every distinct command this route prescribes, as a form.

    Its shared `argv` where it has one, each per-partition command, and its
    `then`. A route with no shared argv would otherwise contribute the empty
    string, which `Invocation._check_forms` raises on. Two partitions
    prescribing the same command contribute one form: `_check_forms` rejects a
    duplicate, and one command is one form whatever number of partitions run
    it.

    Deduplicated on the joined string, not the argv tuple: `_check_forms` is
    the authority on what collides, and it dedups on the string a form
    actually is. Two distinct tuples can join to the same string wherever a
    token carries an embedded space - `("a", "b c")` and `("a", "b", "c")`
    both join to `"a b c"` - and deduplicating the tuples instead would let
    both through, only for `_check_forms` to then raise on the joined
    duplicate it never had a chance to avoid contributing.

    The `then` takes the route's disposition because it is that route's second
    half rather than a route of its own, and it is a form because the row runs
    it - left out, it is a command the row runs that no guard sees declared.
    """
    forms: list[str] = []
    if route.argv:
        forms.append(" ".join(route.argv))
    for partition in _partition_keys(check, tool, route, lang):
        joined = " ".join(route.argv_by_partition[partition])
        if joined not in forms:
            forms.append(joined)
    if route.then:
        forms.append(" ".join(route.then))
    return tuple((form, route.disposition) for form in forms)


def _argv_by_partition(
    check: str, tool: str, route: object, lang: str = "python"
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """One entry per partition, where the record narrows the command per partition.

    Returns `()` where the route names no partition, which leaves the row's
    shared `argv` as the one command every partition runs. Otherwise one entry
    per fixture partition of the language, so a key naming none - `yarn` on a
    typescript route - is validated and then applies to no partition.

    A route may carry a shared `argv` and per-partition ones at once, and
    `Invocation` admits one or the other, so a route carrying both expands
    here: the override where the route names the partition, the shared argv
    everywhere else - `.get(partition, route.argv)` falls back to the shared
    command for a partition the map does not name. Where the route carries no
    shared `argv`, that fallback is `()`, so a partition the map does not name
    has no command at all rather than inheriting one; the loader now permits
    an absent shared `argv` beside a present `argv_by_partition` for exactly
    this.

    What still has no spelling is the opposite shape: a route that carries a
    non-empty shared `argv` and needs one particular partition to have none of
    its own. Naming that partition in the map only offers it a different
    command, never withholds one, because the fallback for every other
    partition is the shared argv itself, and the loader rejects an empty
    per-partition entry outright. No record in the tree is that shape, and it
    gets no spelling until one is.

    Raises:
        ValueError: If the route names a key that is not a partition of
            this lens, via `_partition_keys`. This function runs only for the
            `runs` route, so a bad key on a `superseded` or `alternative`
            route would otherwise reach `forms` unchecked and declare a form
            no partition could run; `_forms_for` calls `_partition_keys` for
            every command route for that reason, and this call keeps this
            function's own check reachable too rather than only reachable
            through that other caller.
    """
    if not route.argv_by_partition:
        return ()
    _partition_keys(check, tool, route, lang)
    return tuple(
        (p, tuple(route.argv_by_partition.get(p, route.argv)))
        for p in FIXTURE_PARTITIONS[lang]
    )


def _own_runner_partitions(
    check: str, tool: str, route: object, lang: str = "python"
) -> tuple[str, ...]:
    """The partitions whose prescribed command takes no launcher prefix.

    `True` claims every command the route prescribes is complete as written,
    and what that covers depends on whether the route has a shared `argv` to
    fall back to. Where it does, every partition runs a command - its own
    override, or the shared argv - so `True` covers every fixture partition of
    the language. A key naming no fixture partition, `yarn` on a typescript
    route, is left out of either form: no partition runs its command, and
    `Invocation._check_own_runner` rejects a partition with none.
    Where it does not, the route prescribes a command only for the
    partitions its map names, so `True` is a claim about those alone; naming
    an unnamed partition too would claim completeness for a command that
    does not exist, which is exactly what `Invocation._check_own_runner`
    rejects, so this stops short of the claim rather than making it and
    relying on that guard to catch it. A list names partitions directly, and
    claims it of those alone either way.

    Neither claim is checkable here, or by the loader: whether a command needs
    a runner in front of it is a fact about the command. So `True` on a route
    whose overrides are runner-led while its shared argv is not marks the
    fallback partitions self-running and they go unfetched, with no error
    anywhere. The list form is what such a route wants. The alternative -
    deciding it from whether the argv's first token looks like a runner - is
    the inference this schema exists to replace, so this stays a claim the
    record makes and the reader checks.
    """
    fixture = FIXTURE_PARTITIONS[lang]
    if route.own_runner is True:
        if route.argv:
            return fixture
        keys = _partition_keys(check, tool, route, lang)
        return tuple(k for k in keys if k in fixture)
    return tuple(p for p in route.own_runner or () if p in fixture)


def _reason_for_no_command(check: str, tool: str, routes: Sequence[Route]) -> str:
    """Why a row prescribes no command, in the record's own words.

    The reason belongs to the routes the record prescribes by default - its
    `disposition: runs` ones - because those are what a default run would
    have taken. Where the group declares none, every route in it is a
    candidate: that is the `forbidden` and `alternative` singleton, where the
    one route the record carries is the only thing there is to read.

    Where more than one candidate survives, the row carries all of them
    rather than the first. The guard this replaced raised there, on the sound
    reason that a row silently taking one of several notes attributes the
    wrong explanation to a run - but its premise, that a tool prescribing no
    command has at most one route explaining why, is one the record set has
    outgrown in three different ways at once. `test/coverage-reach`'s `c8`
    routes differ by `disposition`, `applies_when` and `needs` together (the
    refusal around a Vitest command is `forbidden` and carries neither, the
    plain form for a runner it can observe runs under `target-execution`),
    `test/mutation`'s Stryker routes by `disposition`, and `arch/complexity`'s
    two `eslint` routes only by `needs` - the same two rules under an
    audit-owned flat config or under the target's own.

    Requiring records to merge such notes into one route was the cheaper
    alternative and is not available: a route carries one `needs`, so merging
    `arch/complexity`'s pair means dropping one of its two tiers, and the
    untiered one is exactly what keeps `typescript` out of
    `_silenced_languages` for that record. Reading the disposition alone
    reaches Stryker and `c8`; `applies_when` distinguishes nothing on its own
    today.

    A composed note prefixes each candidate's note with its `applies_when`
    where it has one, because the precondition is what tells the modes apart
    and a note written under one can read as nonsense without it - `c8`'s
    second note opens on "`c8`'s plain form remains the measurement there",
    and "there" is its `applies_when`. A single candidate is not prefixed:
    with nothing to distinguish it the precondition stays on the route where
    a reader of the record finds it, and prefixing unconditionally would
    rewrite the note of every live row whose one route carries an
    `applies_when`.

    Args:
        check: The record's id, for the message.
        tool: The tool the group is keyed on, for the message.
        routes: The group's routes, in record order.

    Returns:
        The candidates' notes, in record order, joined by a blank line.

    Raises:
        ValueError: If several candidates survive and none of them carries a
            note. The row would then reach the artifact saying it ran nothing
            and not why, with no single route to attribute the absence to
            either - the one shape where the guard this replaced was right
            about there being nothing to choose. A lone candidate's note is
            returned as it is, empty or not, because
            `test_a_routed_row_prescribing_no_command_carries_the_records_reason`
            already holds every such row in the tree and a second guard here
            would make a noteless route the concern of tests about partition
            keys and supplied overlays, which it is not.
    """
    candidates = [r for r in routes if r.disposition == "runs"] or list(routes)
    if len(candidates) == 1:
        return candidates[0].note
    reason = "\n\n".join(
        " ".join(
            piece for piece in ((r.applies_when or "").strip(), r.note.strip()) if piece
        )
        for r in candidates
        if (r.note or "").strip()
    )
    if not reason:
        raise ValueError(
            f"{check}/{tool}: prescribes no command and declares "
            f"{len(candidates)} routes it prescribes, none of which carries a "
            "note, so the row would reach the artifact saying it ran nothing "
            "and not why - and there is no single route to attribute the "
            "absence to either"
        )
    return reason


def _caveat_for_no_command(routes: Sequence[Route]) -> str:
    """What a row prescribing no command still needs, in the record's own words.

    The same composition `_reason_for_no_command` makes of the notes, for the
    same reason: with no `runs` command route there is no one route to read the
    field from, and the record shapes that reach this split one tool across
    routes on purpose. `arch/hidden-coupling`'s two `eslint` procedures are the
    live case - an audit-owned config and the target's own, distinguished by
    `needs` - and each states a caveat about its own mode. Refusing the row, as
    the guard this replaced did, made the whole TypeScript selection raise over
    a record that is right; taking one would attribute the other mode's caveat
    to the row.

    The candidates are the group's `runs` routes, or every route where there is
    none. Identical caveats are one caveat. Where several distinct ones survive,
    each is prefixed with its route's `applies_when` where it has one, as the
    composed note is, and they are joined by a blank line in record order.
    """
    candidates = [r for r in routes if r.disposition == "runs"] or list(routes)
    carried = [r for r in candidates if (r.alone_insufficient or "").strip()]
    distinct: list[Route] = []
    for route in carried:
        if all(route.alone_insufficient != d.alone_insufficient for d in distinct):
            distinct.append(route)
    if len(distinct) <= 1:
        return distinct[0].alone_insufficient if distinct else ""
    return "\n\n".join(
        " ".join(
            piece
            for piece in ((r.applies_when or "").strip(), r.alone_insufficient.strip())
            if piece
        )
        for r in distinct
    )


@cache
def routed_invocations(lang: str = "python") -> tuple[Invocation, ...]:
    """Every row a migrated record prescribes, read from the record.

    One row per `(check, tool)` rather than per route: a record may narrow the
    same tool's command twice, once `runs` and once `superseded`, and those are
    two forms of one row. A route naming no tool is a reading pass and produces
    no row. A route whose `kind` is not `command` produces a row prescribing no
    command, which is what the record says and what the engine grades - and
    where several of a group's routes explain that absence,
    `_reason_for_no_command` carries each of them, because one row per tool is
    the unit this returns and the record's split is deliberate.

    `lang` only, `python` by default. A `lang: any` route is applicable to
    either language's partitions by its own note, and selecting it would still
    be wrong here: it adds a check the expectations do not grade, so the
    three-way equality that holds the harness to them would fail rather than
    the round quietly growing a row nothing checks.

    A `disposition: forbidden` route is dropped before grouping, in either
    language: the record names it to warn against it, so it is neither a row
    nor a form the guards should read as prescribed. Grouped with the rest, the
    `depcruise` and `cyclonedx-npm` placeholders would each become a row of
    their own and be fetched and run, which is the exact outcome the record
    forbids.

    A completion comes from `COMPLETIONS` on a python row and from
    `TS_COMPLETIONS` on a typescript one, and only a python row can carry a
    supplied route.

    A row's `note` says why it is not simply the record's command running as
    written, which is the only thing worth carrying into the artifact. Two
    things produce that. Where the round had to complete the command, the
    reason is round-owned and comes from `COMPLETIONS`. Where the record
    prescribes no command at all, the reason is the record's own and comes
    from the notes of the routes it prescribes, composed by
    `_reason_for_no_command` where there is more than one. A command that ran as written explains itself and
    carries none.

    A row's supplied route comes from `SUPPLIED`, never from a route - a
    record declaring one would be prescribing it, which is the distinction the
    overlay exists to preserve. It carries its own `supplied_note`, so those
    two reasons a row's `note` can be round-owned stay a completion and
    nothing else; a supplied route is not a third one.

    A row's `then` is the `runs` route's own - never a `superseded` or
    `alternative` route's, even where one of those carries a `then` of its
    own - because `then` is what the round executes after `argv`, and `argv`
    is already the `runs` route's. `then` is also one of the row's `forms`:
    the row runs it regardless, so a `then` left out of `forms` would be a
    command the row runs with no guard ever seeing it declared.

    Raises:
        ValueError: If a group carries more than one `runs` command route, two
            different `findings_stream` values, two different `in_env` values,
            a non-`forbidden` disposition outside `DISPOSITIONS`, or - where it prescribes no
            command and no completion was supplied - no route carrying a note
            to read the reason off. The first four would otherwise resolve
            silently to whichever route happened to come first; the last is
            `_reason_for_no_command`'s, which composes where several routes
            explain the absence rather than refusing to choose between them.
    """
    rows: list[Invocation] = []
    for check_id, record in sorted(_records().items()):
        if not record.routes:
            continue
        groups: dict[str, list] = {}
        for route in record.routes:
            if route.lang != lang or not route.tool:
                continue
            if route.disposition == "forbidden":
                continue
            groups.setdefault(route.tool, []).append(route)
        for tool, routes in sorted(groups.items()):
            commands = [r for r in routes if r.kind == "command"]
            for route in commands:
                if route.disposition not in DISPOSITIONS:
                    raise ValueError(
                        f"{check_id}/{tool}: route disposition "
                        f"{route.disposition!r} is one the record loader permits "
                        f"and this module's form vocabulary {DISPOSITIONS} does "
                        "not carry, so nothing here decides whether the harness "
                        "may offer it as a form. `forbidden` was the last such "
                        "value and is dropped before grouping; a new one needs "
                        "the same decision, which is not a widened tuple"
                    )
            runs = [r for r in commands if r.disposition == "runs"]
            if len(runs) > 1:
                raise ValueError(
                    f"{check_id}/{tool}: {len(runs)} command routes declare "
                    "`runs`, so which one the round ran would depend on their "
                    "order in the record"
                )
            streams = {r.findings_stream for r in routes}
            if len(streams) > 1:
                raise ValueError(
                    f"{check_id}/{tool}: routes disagree on findings_stream "
                    f"({sorted(streams)}); classify reads one stream, and "
                    "picking either would grade every run of this tool"
                )
            in_env = {bool(r.in_env) for r in routes}
            if len(in_env) > 1:
                raise ValueError(
                    f"{check_id}/{tool}: routes disagree on in_env, so whether "
                    "the tool launches through the partition's environment "
                    "would depend on their order in the record"
                )
            packages = {r.package or tool for r in routes}
            if len(packages) > 1:
                raise ValueError(
                    f"{check_id}/{tool}: routes disagree on package "
                    f"({sorted(packages)}), so which distribution a runner "
                    "fetched would depend on their order in the record"
                )
            if lang == "python":
                supplied = COMPLETIONS.get((check_id, tool))
                contributed = SUPPLIED.get((check_id, tool))
                ts_completion = None
            else:
                supplied = contributed = None
                ts_completion = TS_COMPLETIONS.get((check_id, tool))
            if runs:
                caveat = runs[0].alone_insufficient or ""
            else:
                caveat = _caveat_for_no_command(routes)
            per_partition = (
                _argv_by_partition(check_id, tool, runs[0], lang) if runs else ()
            )
            argv = () if per_partition else (tuple(runs[0].argv) if runs else ())
            if supplied:
                note = supplied.note
            elif ts_completion:
                note = ts_completion.note
            elif argv or per_partition:
                note = ""
            else:
                note = _reason_for_no_command(check_id, tool, routes)
            rows.append(
                Invocation(
                    check=check_id,
                    tool=tool,
                    argv=argv,
                    argv_by_partition=per_partition,
                    own_runner=(
                        _own_runner_partitions(check_id, tool, runs[0], lang)
                        if runs
                        else ()
                    ),
                    forms=tuple(
                        f for r in commands for f in _forms_for(check_id, tool, r, lang)
                    ),
                    findings_stream=streams.pop(),
                    in_env=in_env.pop(),
                    package=packages.pop(),
                    completion=supplied.tokens if supplied else (),
                    completion_by_partition=(
                        ts_completion.by_partition if ts_completion else ()
                    ),
                    fills=ts_completion.fills if ts_completion else (),
                    then=tuple(runs[0].then) if runs else (),
                    note=note,
                    supplied_by_partition=(
                        contributed.by_partition if contributed else ()
                    ),
                    supplied_note=contributed.note if contributed else "",
                    alone_insufficient=caveat,
                )
            )
    return tuple(rows)


def invocations_for(
    partition: str, *, only_check: str | None = None
) -> tuple[Invocation, ...]:
    """Every invocation one partition runs.

    Scoped by the expectations rather than by a second list, so the harness
    cannot run a set the published record does not grade. The rows come from
    two places: the records for those that declare their routes, and this
    file's `INVOCATIONS`, the legacy slot, empty today.

    The language is the partition's, so a TypeScript partition reads the
    `lang: typescript` rows and the TypeScript expectations. `INVOCATIONS`, the
    legacy slot, is Python's alone.

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
    if partition not in ALL_PARTITIONS:
        raise ValueError(
            f"unknown partition {partition!r}; expected one of {ALL_PARTITIONS}"
        )
    lang = lang_of(partition)
    carried = {e.check for e in expectations_for(partition)}
    legacy = INVOCATIONS if lang == "python" else ()
    everything = legacy + routed_invocations(lang)
    scoped = tuple(i for i in everything if i.check in carried)
    if only_check is None:
        return scoped
    filtered = tuple(i for i in scoped if i.check == only_check)
    if not filtered:
        raise ValueError(
            f"no invocation for {only_check!r} on the {partition} partition; "
            f"it carries {sorted({i.check for i in scoped})}"
        )
    return filtered


def packages_for(invocation: Invocation) -> tuple[str, ...]:
    """Everything that has to be installed for this row's route to run.

    The first is the route's own `package`, or the tool's name on a row that
    carries none; anything after it is what the route needs present and the
    fixture does not declare, from `HARNESS_COMPANIONS`.
    """
    return (
        invocation.package or invocation.tool,
        *HARNESS_COMPANIONS.get(invocation.tool, ()),
    )


def python_one_shot(packages: Sequence[str], command: str) -> tuple[str, ...]:
    """The isolated runner in front of a Python route's command, by the engine's rule.

    `audit-core`'s route-running paragraph: a runner handed only a command
    fetches the package named like that command, so wherever the package that
    provides it is not the command's own name the runner is told the package,
    as `uvx --from <package>`, and the argv runs as written after it. The
    comparison is with `command`, the first word of what runs, and not with
    the route's `tool`: `pytest-cov` is both a route's tool and its package
    while the command is `pytest`, and the bare `uvx pytest` would fetch pytest
    without the plugin. A companion the harness adds rides along as `--with`,
    which needs `--from` to name the first package even where it is the
    command's own name, since `uvx --with` alone would still resolve the
    command by its name.
    """
    package, *companions = packages
    if package == command and not companions:
        return ("uvx",)
    extra = tuple(word for name in companions for word in ("--with", name))
    return ("uvx", "--from", package, *extra)


def launcher(
    invocation: Invocation,
    partition: str,
    *,
    granted: bool,
    honour_own_runner: bool = True,
    command: str | None = None,
) -> tuple[str, ...]:
    """The words that go in front of the command, and how the tool is obtained.

    `command` is the first word of what will run after these words, which
    decides whether an isolated runner has to be told the package: the record's
    own argv on this partition where the caller passes none, and the caller's
    where it runs something else, as the version probe does.

    Nothing goes in front of a command the record already writes whole, which is
    what `own_runner` names - see that field for why such a route exists at all.
    `honour_own_runner=False` is for a caller running something other than the
    record's command: the version probe runs the tool's own `--version`, which
    still has to be obtained the usual way, and probing it bare would record a
    missing tool where the tool's version belongs.

    A TypeScript partition's words come from `_ts_launcher`; everything below
    this paragraph is the Python half.

    An `in_env` tool runs from inside the materialized environment under a
    grant, because the one-shot runner's sandbox cannot see what the target
    resolved: measured on the pylock partition, `uvx deptry` reported
    markupsafe as DEP001 where the route below reported it as DEP003, which is
    the answer the expectation claims. Grading a correct run against the other
    one would send a later pass off to "fix" a record that was right.

    Without the grant there is no environment to run inside. A tiered route is
    then not run at all; what still reaches this branch - the version probe,
    which runs whatever the grant - falls back to the one-shot runner, and the
    run records which it used.

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

    The `uv` partition does run inside its own project, so it takes
    `--no-sync`: a bare `uv run` locks and syncs the project before running the
    command, so against a `uv.lock` gone stale beside its `pyproject.toml` it
    rewrites the lock and re-syncs the venv the checks read. `--frozen` is not
    enough on its own: it leaves the lock alone and still syncs the venv to it,
    reinstalling anything the materialization left out. Measured with uv 0.12
    on a scratch project with a stale lock and a package removed from its venv:
    bare `uv run --with` rewrote the lock and installed the new dependency,
    `--frozen` kept the lock and reinstalled the removed package, and
    `--no-sync` changed neither. The seeded lock is fresh and its venv
    complete, so no fixture run shows the difference; a real target's need not
    be either.

    Reaching that venv depends on it existing at `.venv` regardless of which
    manager built it, which is what `_fixture_env`'s
    `POETRY_VIRTUALENVS_IN_PROJECT` / `PIPENV_VENV_IN_PROJECT` are for.

    `argv` itself never changes here - what the record prescribes is untouched
    by any of this; only the words placed in front of it are.
    """
    if honour_own_runner and partition in invocation.own_runner:
        return ()
    if lang_of(partition) == "typescript":
        return _ts_launcher(invocation, partition, granted=granted)
    packages = packages_for(invocation)
    extra = tuple(word for name in packages[1:] for word in ("--with", name))
    if not (invocation.in_env and granted):
        if command is None:
            words = argv_for(invocation, partition)
            command = words[0] if words else invocation.tool
        return python_one_shot(packages, command)
    if partition == "uv":
        return ("uv", "run", "--no-sync", "--with", packages[0], *extra)
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


def _ts_launcher(
    invocation: Invocation, partition: str, *, granted: bool
) -> tuple[str, ...]:
    """`launcher`'s TypeScript half, once `own_runner` has had its say.

    A manager subcommand runs bare: it is the partition's own manager, which
    `_ts_fixture_env` has already put on PATH, and there is no package to fetch.
    An `in_env` tool under a grant runs the tree's own copy through
    `TS_IN_ENV`; anything else is fetched once through `TS_ONE_SHOT`, naming
    the route's `package` as the package, or the tool's name on a row that
    carries none, so the command after it never has to be the package's name. As on the Python side, the argv itself never
    changes here.
    """
    if invocation.tool in TS_MANAGER_TOOLS:
        return ()
    if invocation.in_env and granted:
        return TS_IN_ENV[partition]
    return tuple(
        word.format(package=invocation.package or invocation.tool)
        for word in TS_ONE_SHOT[partition]
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
# a record's route names without an entry here fails loudly rather than defaulting.
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


def nonzero_exit_meaning(tool: str, lang: str = "python") -> str:
    """What a non-zero exit from `tool` means, read out of the stated table.

    Raises rather than defaulting, for the same reason `grant_tier` raises on
    an unknown (check, tool) pair: an omitted entry must never read as a
    silent claim, and silence is exactly how xenon and mutmut were misgraded.
    """
    table = NONZERO_EXIT_MEANING if lang == "python" else TS_NONZERO_EXIT_MEANING
    if tool not in table:
        raise ValueError(
            f"{tool!r} has no stated non-zero-exit meaning for {lang}; "
            "an omitted entry would read as a silent default rather than a decision"
        )
    return table[tool]


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
# The TypeScript launchers fail the same way. Measured on 2026-09-26, each
# writing to stderr: `npx --yes --package=no-such-package-45xyzq -- ...` exits 1
# with "npm error code E404" and "npm error 404 Not Found", and so does
# `npx --no -- no-such-tool-45xyzq`, which falls through to the registry; and
# `pnpm --package=no-such-package-45xyzq dlx ...` exits non-zero with
# "ERR_PNPM_FETCH_404" and "is not in the npm registry".
#
# Matching a message is fragile and this is the only signal there is, so the
# match is narrowed twice - it is consulted only when the command's first word
# is one of these launchers, and only when the command failed. Every command
# this file runs starts with one of these launchers or with a bare tool name
# `_run` already reports as absent by `FileNotFoundError` - poetry and pipenv
# never head a command themselves, since even their own materialization goes
# through a pinned `uvx poetry@...` / `uvx pipenv@...` - so this dict holds the
# names a launcher's own resolution failure can actually surface under. A bare
# `npm` or `pnpm` subcommand (`npm audit`, `pnpm outdated`) fetches no tool, so
# its 404s are about the target's dependencies rather than a missing tool, and
# neither name is a key here.
LAUNCHER_MISSES: dict[str, tuple[str, ...]] = {
    "uvx": (
        "not found in the package registry",
        "no solution found when resolving tool dependencies",
    ),
    "uv": (
        "not found in the package registry",
        "no solution found when resolving tool dependencies",
    ),
    "npx": ("npm error code e404", "npm error 404 not found"),
}

# `pnpm` heads both a one-shot fetch (`pnpm --package=X dlx`) and the package
# manager's own subcommands, so its markers apply only where the command is a
# `dlx` fetch: a 404 from `pnpm audit` is not a missing tool.
PNPM_DLX_MISSES: tuple[str, ...] = ("err_pnpm_fetch_404", "is not in the npm registry")


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
    if command[0] == "pnpm" and "dlx" in command:
        markers = PNPM_DLX_MISSES
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


def _ts_fixture_env(shim_dir: Path | None = None) -> dict[str, str]:
    """The environment a TypeScript fixture subprocess runs under.

    `_fixture_env`'s removals first, since the harness still runs under
    `uv run`. Then the registry overrides go, as in
    `build_python_fixtures.ts_fixture_env`, and the public registry is named, so
    a materialization resolves the lockfile's own URLs and a one-shot fetch
    reaches the registry the records name. Corepack neither prompts before
    fetching the pinned pnpm, which would hang a run with no terminal, nor pins
    a `packageManager` of its own into a manifest in the copy. `shim_dir`, where
    `ts_shim_command` put corepack's pnpm, goes first on PATH.
    """
    env = _fixture_env()
    for name in [n for n in env if _is_registry_setting(n)]:
        del env[name]
    env["npm_config_registry"] = PUBLIC_NPM_REGISTRY
    env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] = "0"
    env["COREPACK_ENABLE_AUTO_PIN"] = "0"
    if shim_dir is not None:
        env["PATH"] = os.pathsep.join(
            entry for entry in (str(shim_dir), env.get("PATH", "")) if entry
        )
    return env


def _runner(env: dict[str, str] | None):
    """`_run` bound to one environment, or to `_fixture_env`'s where `env` is None.

    The Python half never passes an environment, so its calls keep `_run`'s
    three-argument shape exactly; `_run` is looked up at call time, so a test
    replacing it replaces it here too.
    """
    if env is None:
        return lambda command, cwd, timeout: _run(command, cwd, timeout)
    return lambda command, cwd, timeout: _run(command, cwd, timeout, env=env)


def _run(
    command: Sequence[str],
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    """Run one command and report what happened, distinguishing the failures.

    A tool that is missing and a tool that ran and failed are different facts -
    the engine's `tool-unavailable` and `tool-failed` depend on telling them
    apart - so `FileNotFoundError` is caught by name and reported as absence
    rather than collapsing into a non-zero exit. Nothing is swallowed: every
    other exception is reported with its type and message.

    Args:
        command: The argv to run.
        cwd: Where in the materialized copy to run it: the copy's root, or
            the seeded package for a row `TS_RUN_IN_PACKAGE` names.
        timeout: Seconds before the command is abandoned as hung.
        env: The environment to run it under; `_fixture_env()` where `None`.
    """
    if env is None:
        env = _fixture_env()
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=env,
            # Never the caller's terminal: npx assumes `--yes` only where stdin
            # is not a TTY, so a record's own `npx --package ...` route run from
            # an interactive shell would wait on "Ok to proceed?" until the
            # timeout and grade as a hung tool.
            stdin=subprocess.DEVNULL,
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
    env: dict[str, str] | None = None,
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
        env: The environment `run_partition` ran the rows under; `None` on a
            Python partition, which runs under `_fixture_env`.

    A TypeScript tool that is another manager's subcommand is not probed on
    this partition at all: its rows never run here, and with only this
    partition's manager provisioned, `pnpm --version` inside an npm-pinned tree
    would be corepack refusing an undeclared manager rather than a version.
    """
    lang = lang_of(partition)
    run = _runner(env)
    granted = grant != "none"
    representative: dict[str, Invocation] = {}
    legacy = INVOCATIONS if lang == "python" else ()
    for inv in legacy + routed_invocations(lang):
        representative.setdefault(inv.tool, inv)
    probes = VERSION_PROBE if lang == "python" else TS_VERSION_PROBE
    absent = NO_VERSION_ROUTE if lang == "python" else TS_NO_VERSION_ROUTE

    versions: dict[str, str] = {}
    invoked = invocations_for(partition, only_check=only_check)
    for tool in {inv.tool for inv in invoked}:
        manager = TS_MANAGER_TOOLS.get(tool) if lang == "typescript" else None
        if manager is not None and manager != partition:
            continue
        probe = probes[tool]
        if probe is None:
            versions[tool] = f"no version route: {absent[tool]}"
            continue
        inv = representative[tool]
        if blocked_by is not None and inv.in_env:
            versions[tool] = (
                "environment-unmaterialized: the partition's materialization "
                f"stopped at {' '.join(blocked_by)}, so there is no environment "
                "this probe could run inside"
            )
            continue
        prefix = launcher(
            inv, partition, granted=granted, honour_own_runner=False, command=probe[0]
        )
        command = (*prefix, *probe)
        outcome = run(command, work_dir, timeout)
        stdout = str(outcome["stdout"]).strip()
        stderr = str(outcome["stderr"]).strip()
        if outcome["returncode"] == 0:
            versions[tool] = stdout or stderr
        else:
            versions[tool] = stdout or stderr or f"exit code {outcome['returncode']}"
    return versions


def report_path_for(
    invocation: Invocation, partition: str, grant: str, work_root: Path
) -> Path:
    """Where this row's tool writes the report the record names `<report-path>`.

    In the run's work root rather than in the copy, so the tool writes nothing
    into the tree it reads, and named by partition, grant and row, so two rows
    or two runs sharing a work root never read each other's report. Absolute
    whatever `work_root` is, because the tool runs with the copy as its working
    directory: a relative `--work-dir` would otherwise resolve inside the copy,
    putting the write in the tree and the read where nothing was written.
    """
    slug = f"{invocation.check}-{invocation.tool}".replace("/", "-")
    return (work_root / f"{partition}-{grant}-{slug}-report.json").resolve()


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
    stdout and stderr are kept, and where a route writes a report file its
    content under `report`, so that a later pass can re-classify without
    re-running, and so that a completion this round had to make is visible
    beside what it produced.

    `only_check` narrows the run to one check id and reaches the version probe
    as well as the rows, so the observation covers exactly the cell that ran.
    The observation records it under `only_check`, because a file holding one
    check's rows is indistinguishable from a matrix whose other checks all
    produced nothing unless it says which it is. The caller owns the filename;
    `main` gives a filtered run one carrying the check's slug.

    A TypeScript partition runs under `_ts_fixture_env`, and a partition whose
    manager corepack provides has it enabled into a shim directory beside the
    copy first, whatever the grant, recorded under `setup`. A row whose tool is
    another manager's subcommand, or whose route's `applies_when` fails on the
    fixture, is recorded as not run with `not_run` saying which and `why` saying
    what, rather than run against a tree it does not describe.
    """
    if grant not in GRANTS:
        raise ValueError(f"unknown grant {grant!r}; expected one of {GRANTS}")
    # Absolute from here on: the commands below run with the copy as their
    # working directory, so a path built from a relative `--work-dir` - the
    # corepack shim directory, a row's report file - would resolve inside it.
    work_root = work_root.resolve()
    lang = lang_of(partition)
    granted = grant != "none"
    copy = reconstruct(partition, source, work_root)
    env: dict[str, str] | None = None
    setup = []
    if lang == "typescript":
        shim_dir = None
        if partition in TS_COREPACK_MANAGED:
            shim_dir = work_root / TS_SHIM_DIRNAME
            shim_dir.mkdir(parents=True, exist_ok=True)
        env = _ts_fixture_env(shim_dir)
        if shim_dir is not None:
            command = ts_shim_command(partition, shim_dir)
            setup.append(
                {"command": list(command), **_runner(env)(command, copy, timeout)}
            )
    run = _runner(env)
    materialize = MATERIALIZE if lang == "python" else TS_MATERIALIZE
    materialization = []
    # The command that stopped the materialization, or `None` where it finished.
    # A route that fails leaves the copy unresolved, and every row needing the
    # tree then has to say so rather than run against it: run anyway and each
    # such row classifies on its own, `tool-failed` here and spuriously `ok`
    # there, with nothing in the file pointing back at the one cause - which is
    # the harness inventing a finding rather than reporting one.
    blocked_by: list[str] | None = None
    if granted:
        for command in materialize[partition]:
            outcome = run(command, copy, timeout)
            materialization.append({"command": list(command), **outcome})
            if outcome["returncode"] != 0:
                blocked_by = list(command)
                break

    rows = []
    for invocation in invocations_for(partition, only_check=only_check):
        tier = grant_tier(invocation.check, invocation.tool, lang)
        permitted = granted or not tier
        argv = argv_for(invocation, partition)
        supplied = invocation.supplied(partition)
        row: dict[str, object] = {
            "check": invocation.check,
            "tool": invocation.tool,
            "record_argv": list(invocation.prescribed(partition)),
            "completion": list(
                invocation.completion
                + dict(invocation.completion_by_partition).get(partition, ())
            ),
            "note": invocation.note,
            "needs": tier,
            "in_env": invocation.in_env,
            "alone_insufficient": invocation.alone_insufficient,
        }
        if invocation.fills:
            # Beside `completion` for the reason it is: what the round put into
            # the record's command stays distinguishable from what it said.
            row["fills"] = dict(invocation.fills)
        workdir = workdir_for(invocation, partition)
        if workdir:
            row["workdir"] = workdir
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
        skipped = not_run_on(invocation, partition)
        if skipped is not None:
            row |= {
                "ran": False,
                "status": "",
                "reason": "",
                "not_run": skipped[0],
                "why": skipped[1],
            }
            rows.append(row)
            continue
        if not permitted:
            status, reason = classify(0, "", "", tool_present=True, permitted=False)
            row |= {"ran": False, "status": status, "reason": reason}
            rows.append(row)
            continue
        # A row needing the tree is one carrying a tier or running inside the
        # environment; the two sets are not the same in general, because a route
        # can carry a tier and still launch through a one-shot runner. No Python
        # row is that shape today; the `or` keeps such a row gated if one is.
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
        # outside the copy - `uv run --no-sync --with` (or, off `uv`, the same route
        # pointed `--python` at the copy's own venv) - and never installed into
        # the copy this run owns, never mind the fixture or the shared tree:
        # `audit-core` bars all three, and a package the audit added is never
        # evidence about the target wherever it landed.
        prefix = launcher(invocation, partition, granted=granted)
        command = expand_plugin_root((*prefix, *argv))
        report = None
        if any(REPORT_PATH_TOKEN in token for token in command):
            report = report_path_for(invocation, partition, grant, work_root)
            report.unlink(missing_ok=True)
            command = tuple(
                token.replace(REPORT_PATH_TOKEN, str(report)) for token in command
            )
        outcome = run(command, copy / workdir, timeout)
        row |= {"ran": True, "command": list(command), **outcome}
        if report is not None:
            # The evidence is the file, not the streams: the reporter prints
            # only where it wrote it. `None` where the tool wrote nothing.
            row["report"] = report.read_text() if report.is_file() else None
        # A route the record writes as two commands is one route, so both halves
        # reach the verdict. Classifying on the first alone would grade a route
        # whose measuring half ran and whose reporting half died as `ok` with no
        # coverage table behind it - the shape `then` exists to prevent.
        ran: list[tuple[Sequence[str], dict[str, object]]] = [(command, outcome)]
        if invocation.then:
            follow_up = expand_plugin_root((*prefix, *invocation.then))
            then_outcome = run(follow_up, copy / workdir, timeout)
            row["then"] = {"command": list(follow_up), **then_outcome}
            ran.append((follow_up, then_outcome))
        row |= _verdict(
            ran,
            invocation.findings_stream,
            nonzero_exit_meaning(invocation.tool, lang),
        )
        if report is not None and row["report"] is None and row["status"] == "ok":
            # The streams cannot vouch for a report-writing route: vitest prints
            # `JSON report written to` whether or not the file ends up holding
            # anything, so a run that left no file is a tool that returned
            # nothing parseable, whatever its exit code and stdout said.
            row |= {
                "status": "no-evidence",
                "reason": "tool-failed",
                "why": f"the route writes its report to {report} and none was there",
            }
        rows.append(row)

    versions = probe_versions(
        partition,
        grant,
        copy,
        timeout,
        blocked_by=blocked_by,
        only_check=only_check,
        env=env,
    )

    observed: dict[str, object] = {
        "partition": partition,
        "grant": grant,
        "source": str(source),
        "only_check": only_check or "",
        "materialization": materialization,
        "results": rows,
        "versions": versions,
    }
    if lang == "typescript":
        observed["setup"] = setup
    return observed


def main(argv: list[str] | None = None) -> int:
    """Run one partition under one grant state and write the observations.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `0` once the run is written. A tool that failed is an observation rather
        than an error here: the round exists to record what came back.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run each check record's prescribed tooling in the partition's "
            "language against one seeded fixture partition."
        )
    )
    parser.add_argument("partition", choices=list(ALL_PARTITIONS))
    parser.add_argument("--grant", choices=list(GRANTS), default="target-execution")
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=None,
        help=(
            "where the generated partitions are; by default the builder's "
            "output directory for the partition's language"
        ),
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help=(
            "scratch root for the copy and for any report a row writes; a "
            "temporary directory by default"
        ),
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
    if args.fixture_root is None:
        args.fixture_root = FIXTURE_ROOTS[lang_of(args.partition)]

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
